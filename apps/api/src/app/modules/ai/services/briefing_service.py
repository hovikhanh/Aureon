"""BriefingService (M3.3, T-819/T-823, R-DEC-131/132/134) — CEO Daily Briefing snapshot.

A briefing is a **snapshot** of `ReportingService.executive()` (EP-RPT-01, the 7-block content)
persisted into `ENT-Briefing` so it can be tracked (G1 open), e-mailed and reviewed. Extra blocks
— RECOMMENDATIONS (recommendation insights), CALENDAR (today's events) and STALE (metrics past
their freshness SLA, R-DEC-86) — are added on top. One row per `(recipient, day)`; `today()` is
generate-if-missing and idempotent via the `uq_briefing_recipient_date` constraint.

Numbers are grounded (FR-AIQ-01) because every value originates from the metric store / tool
results via the reporting service. Cross-module reads go through public services only (DEC-125).
The caller commits.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.clock import business_today
from app.core.deps import Principal
from app.core.envelope import Page
from app.core.errors import NotFoundError, PermissionDeniedError
from app.core.pagination import PageParams
from app.modules.ai.models import Briefing
from app.modules.ai.repositories import BriefingRepository
from app.modules.ai.schemas import BriefingCalendarItemOut, BriefingOut
from app.modules.ai.services.insight_service import InsightService
from app.modules.dashboard.services.reporting_service import ReportingService
from app.modules.execution.services.calendar_service import CalendarService
from app.modules.platform.services.notification_service import NotificationService

HOME_LINK = "/home"


class BriefingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = BriefingRepository(db)

    # ---------- EP-AI-24 ----------
    async def today(self, user: Principal) -> BriefingOut:
        """The caller's briefing for the business day; generate (idempotent) if missing."""
        self._require_executive(user)
        today = business_today()
        existing = await self.repo.for_recipient_date(user.user_id, today)
        if existing is not None:
            return self._to_out(existing)
        return self._to_out(await self._generate(user, today))

    # ---------- EP-AI-25 ----------
    async def history(
        self, user: Principal, page: PageParams, *,
        date_from: date | None, date_to: date | None,
    ) -> Page[BriefingOut]:  # fmt: skip
        self._require_executive(user)
        rows, total = await self.repo.history(
            user.user_id, date_from=date_from, date_to=date_to,
            limit=page.limit, offset=page.offset,
        )  # fmt: skip
        return Page(
            items=[self._to_out(b) for b in rows],
            total=total, limit=page.limit, offset=page.offset,
        )  # fmt: skip

    # ---------- EP-AI-26 ----------
    async def mark_opened(self, user: Principal, briefing_id: uuid.UUID) -> BriefingOut:
        row = await self.repo.by_id_for(briefing_id, user.user_id)
        if row is None:
            raise NotFoundError("briefing not found")
        if row.opened_at is None:  # first open → G1 tracking (North Star §20.1); idempotent after
            row.opened_at = datetime.now(UTC)
            row.status = "opened"
            await self.db.flush()
            await record_audit(
                self.db, action="ai.briefing_open", target_schema="ai",
                target_table="briefings", target_id=row.id,
            )  # fmt: skip
        return self._to_out(row)

    # ---------- job (R-DEC-134) ----------
    async def generate_for(self, user: Principal, *, email: bool = True) -> Briefing | None:
        """Pre-generate for the beat job; returns None if already present (idempotent)."""
        if not self._is_executive(user):
            return None
        today = business_today()
        if await self.repo.for_recipient_date(user.user_id, today) is not None:
            return None
        row = await self._generate(user, today)
        if email:
            await self._email(user, row)
        return row

    async def generate_all(self, *, email: bool = True) -> int:
        """Beat entry (R-DEC-134): one briefing per active CEO/DIR for today; idempotent per
        (recipient, day). Returns the number of briefings newly generated this run."""
        from app.modules.auth.services.user_admin_service import UserAdminService

        made = 0
        for user in await UserAdminService(self.db).executive_principals():
            if await self.generate_for(user, email=email) is not None:
                made += 1
        return made

    # ---------- internals ----------
    async def _generate(self, user: Principal, when: date) -> Briefing:
        dash = await ReportingService(self.db).executive(user)
        recs = await InsightService(self.db).list_for(user, kind="recommendation")
        events = await CalendarService(self.db).list_events(
            user, date_from=when, date_to=when, event_source=None, task_id=None
        )
        cal = [
            BriefingCalendarItemOut(
                id=e.id, title=e.title, starts_at=e.starts_at, ends_at=e.ends_at
            )
            for e in events
        ]
        stale = [t.metric_code for t in dash.tiles if t.is_stale]
        payload: dict[str, Any] = {
            "dashboard": dash.model_dump(mode="json"),
            "recommendations": [r.model_dump(mode="json") for r in recs],
            "calendar_today": [c.model_dump(mode="json") for c in cal],
            "stale_metric_codes": stale,
        }
        return await self.repo.create(
            recipient_id=user.user_id,
            briefing_date=when,
            generated_at=datetime.now(UTC),
            summary_line=dash.summary_line,
            payload=payload,
            stale_metric_codes=stale,
            status="generated",
        )

    async def _email(self, user: Principal, row: Briefing) -> None:
        """Summary + link only — never level-3/4 content (02 §5.3, R-DEC-134)."""
        await NotificationService(self.db).create(
            recipient_id=user.user_id, kind="system",
            title="Daily Briefing", body=row.summary_line, link=HOME_LINK,
            ref_schema="ai", ref_table="briefings", ref_id=row.id,
        )  # fmt: skip
        row.delivered_email_at = datetime.now(UTC)
        await self.db.flush()

    def _to_out(self, row: Briefing) -> BriefingOut:
        p = row.payload or {}
        return BriefingOut(
            id=row.id,
            briefing_date=row.briefing_date,
            generated_at=row.generated_at,
            summary_line=row.summary_line,
            dashboard=p.get("dashboard", {}),
            recommendations=p.get("recommendations", []),
            calendar_today=p.get("calendar_today", []),
            stale_metric_codes=list(row.stale_metric_codes or []),
            opened_at=row.opened_at,
            status=row.status,
        )

    @staticmethod
    def _is_executive(user: Principal) -> bool:
        return user.has("dashboard:read") and user.role in ("CEO", "DIR")

    def _require_executive(self, user: Principal) -> None:
        if not self._is_executive(user):
            raise PermissionDeniedError("daily briefing is for CEO/Director")


__all__ = ["BriefingService"]

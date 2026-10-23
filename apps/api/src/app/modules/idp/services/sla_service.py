"""IDP review SLA escalation (04 §8.3, FR-DC-21; T-412). An hourly beat task
(`app.jobs.check_review_sla`) scans documents still awaiting a human and escalates those past
their SLA:

* current assignment `due_at` passed (≥ `REVIEW_SLA_HOURS`) → escalate to **manager**;
* past a second SLA span (≥ 2×) → escalate to the **department head**.

Each escalation appends a `ReviewAssignment(kind=ESCALATE)` (append-only history; the one
`is_current` row moves up the chain), emits `EVT-idp.review_escalated`, and creates an in-app
`ENT-Notification` for the resolved recipient. Idempotent: a document is not re-escalated to a
level it already sits at (the current assignment already targets that role).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.config import get_config
from app.modules.idp.models import ReviewAssignment, SourceDocument

EVT_ESCALATED = "idp.review_escalated"

# role codes used for escalation targets (02 §1.4, R-DEC-12)
MANAGER_ROLE = "MGR"
DEPT_HEAD_ROLE = "CEO"  # department-head stand-in for the demo org (04 §8.3 "escalate_to")


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class SlaService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def check_review_sla(self, now: datetime | None = None) -> list[uuid.UUID]:
        """Scan + escalate overdue reviews. Returns the escalated document ids."""
        now = now or _now()
        sla_hours = get_config().review_sla_hours
        rows = (
            await self.db.execute(
                select(SourceDocument, ReviewAssignment)
                .join(
                    ReviewAssignment,
                    ReviewAssignment.source_document_id == SourceDocument.id,
                )
                .where(
                    SourceDocument.status.in_(("NEEDS_REVIEW", "IN_REVIEW")),
                    SourceDocument.deleted_at.is_(None),
                    ReviewAssignment.is_current.is_(True),
                )
            )
        ).all()
        escalated: list[uuid.UUID] = []
        for doc, current in rows:
            due = _aware(current.due_at)
            overdue_hours = (now - due).total_seconds() / 3600
            if overdue_hours < 0:
                continue
            # choose the level: ≥ 2×SLA → department head, else manager
            if overdue_hours >= sla_hours:
                target_role = DEPT_HEAD_ROLE
                level = "DEPT_HEAD"
            else:
                target_role = MANAGER_ROLE
                level = "MANAGER"
            # idempotency: already escalated to this role → skip
            if current.kind == "ESCALATE" and current.to_role_code == target_role:
                continue
            await self._escalate(doc, current, target_role, level, now)
            escalated.append(doc.id)
        return escalated

    async def _escalate(
        self,
        doc: SourceDocument,
        current: ReviewAssignment,
        target_role: str,
        level: str,
        now: datetime,
    ) -> None:
        recipient = await self._resolve_recipient(target_role, doc.department_id)
        current.is_current = False
        assignment = ReviewAssignment(
            source_document_id=doc.id,
            kind="ESCALATE",
            from_user_id=current.to_user_id,
            to_user_id=recipient,
            to_role_code=target_role,
            reason=f"SLA breached ({level})",
            due_at=current.due_at,  # keep original SLA clock (04 §8.3)
            is_current=True,
        )
        self.db.add(assignment)
        await self.db.flush()
        await self._emit(doc, target_role, level)
        if recipient is not None:
            await self._notify(recipient, doc.id, level)
        await record_audit(
            self.db,
            action="idp.review.escalate",
            target_schema="idp",
            target_table="review_assignments",
            target_id=assignment.id,
            after={"to_role_code": target_role, "level": level},
        )

    async def _resolve_recipient(
        self, role_code: str, department_id: uuid.UUID | None
    ) -> uuid.UUID | None:
        from app.modules.auth.services.auth_service import AuthService

        return await AuthService(self.db).find_user_by_role(role_code, department_id=department_id)

    async def _emit(self, doc: SourceDocument, target_role: str, level: str) -> None:
        from app.core.events.outbox import publish_in_tx

        payload: dict[str, Any] = {
            "document_id": str(doc.id),
            "escalated_to_role": target_role,
            "level": level,
        }
        await publish_in_tx(
            self.db,
            event_type=EVT_ESCALATED,
            producer="idp",
            aggregate_schema="idp",
            aggregate_table="source_documents",
            aggregate_id=doc.id,
            payload=payload,
        )

    async def _notify(self, recipient_id: uuid.UUID, document_id: uuid.UUID, level: str) -> None:
        from app.modules.platform.services.notification_service import NotificationService

        await NotificationService(self.db).create(
            recipient_id=recipient_id,
            kind="review_escalated",
            title="Tài liệu quá hạn duyệt (SLA)",
            body=f"Một tài liệu chờ duyệt đã quá hạn và được chuyển lên ({level}).",
            ref_schema="idp",
            ref_table="source_documents",
            ref_id=document_id,
        )

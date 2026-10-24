"""Public notification service (ENT-Notification, 05 §5/§2.4; FR-NTF; M1.2 T-616).

Other modules create in-app notifications through `create` (never importing `platform.models` —
DEC-125); it runs in the caller's transaction so the notification commits with the triggering
mutation. `email_status = PENDING` only when the recipient's preference for `kind` enables
e-mail (R-DEC-32/33); the sender (T-616b) picks PENDING rows up.

Inbox endpoints EP-NTF-01..05 use the caller's own id only (R-DEC-31).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.envelope import Page
from app.core.errors import NotFoundError
from app.core.tenant import require_tenant
from app.modules.platform.models import Notification
from app.modules.platform.repositories import (
    NotificationPreferenceRepository,
    NotificationRepository,
)
from app.modules.platform.schemas import (
    NotificationOut,
    NotificationPreferenceOut,
    PreferenceItem,
)

log = logging.getLogger(__name__)

ALL_KINDS: tuple[str, ...] = (
    "alert", "review_assigned", "review_escalated", "task_assigned", "approval_requested",
    "approval_decided", "report_ready", "ai_action", "document_ready", "reminder", "system",
)  # fmt: skip
# R-DEC-32: no stored row → e-mail on only for these kinds; in-app is always on.
EMAIL_DEFAULT_ON: frozenset[str] = frozenset(
    {"task_assigned", "approval_requested", "review_assigned", "review_escalated"}
)


def notification_out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=n.id, kind=n.kind, title=n.title, body=n.body, link=n.link, ref_schema=n.ref_schema,
        ref_table=n.ref_table, ref_id=n.ref_id, read_at=n.read_at, created_at=n.created_at,
    )  # fmt: skip


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = NotificationRepository(db)
        self.prefs = NotificationPreferenceRepository(db)

    async def email_enabled(self, user_id: uuid.UUID, kind: str) -> bool:
        stored = (await self.prefs.of_user(user_id)).get(kind)
        return stored.email_enabled if stored is not None else kind in EMAIL_DEFAULT_ON

    async def create(
        self,
        *,
        recipient_id: uuid.UUID,
        kind: str,
        title: str,
        body: str,
        link: str | None = None,
        ref_schema: str | None = None,
        ref_table: str | None = None,
        ref_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        email = await self.email_enabled(recipient_id, kind)
        notif = Notification(
            recipient_id=recipient_id, kind=kind, title=title, body=body, link=link,
            ref_schema=ref_schema, ref_table=ref_table, ref_id=ref_id,
            tenant_id=require_tenant(), email_status="PENDING" if email else "NOT_REQUIRED",
        )  # fmt: skip
        self.db.add(notif)
        await self.db.flush()
        return notif.id

    async def notify_users(
        self, recipients: Iterable[uuid.UUID | None], *, skip: Iterable[uuid.UUID | None] = (),
        kind: str, title: str, body: str, link: str, ref_schema: str, ref_table: str,
        ref_id: uuid.UUID,
    ) -> list[uuid.UUID]:  # fmt: skip
        """One notification per distinct recipient user id, minus `skip` (R-DEC-46)."""
        out: list[uuid.UUID] = []
        skipped = {s for s in skip if s is not None}
        for uid in dict.fromkeys(r for r in recipients if r is not None):
            if uid in skipped:
                continue
            out.append(await self.create(
                recipient_id=uid, kind=kind, title=title, body=body, link=link,
                ref_schema=ref_schema, ref_table=ref_table, ref_id=ref_id,
            ))  # fmt: skip
        return out

    async def already_sent(
        self, recipient_id: uuid.UUID, *, kind: str, since: datetime, link: str | None = None,
        ref_table: str | None = None, ref_id: uuid.UUID | None = None, title: str | None = None,
    ) -> bool:  # fmt: skip
        """Public dedupe lookup for idempotent producers (goal alerts / weekly reminder, T-629):
        a `kind` notification with this `link` / `ref_table + ref_id` / `title` already exists
        for the recipient since `since`."""
        return await self.repo.exists(recipient_id, kind=kind, since=since, link=link,
                                      ref_table=ref_table, ref_id=ref_id, title=title)  # fmt: skip

    # ---------- EP-NTF-01..03 inbox ----------
    async def inbox(
        self, user_id: uuid.UUID, *, unread_only: bool, kind: str | None, limit: int, offset: int
    ) -> Page[NotificationOut]:
        rows, total, unread = await self.repo.page(
            user_id, unread_only=unread_only, kind=kind, limit=limit, offset=offset
        )
        return Page(items=[notification_out(n) for n in rows], total=total, limit=limit,
                    offset=offset, unread_count=unread)  # fmt: skip

    async def mark_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> NotificationOut:
        n = await self.repo.mine(user_id, notification_id)
        if n is None:
            raise NotFoundError("notification not found")
        if n.read_at is None:  # idempotent: keep the first read time
            n.read_at = datetime.now(UTC)
            await self.db.flush()
        return notification_out(n)

    async def read_all(self, user_id: uuid.UUID, up_to: datetime | None) -> int:
        now = datetime.now(UTC)
        return await self.repo.read_all(user_id, up_to or now, now)

    # ---------- EP-NTF-04/05 preferences ----------
    async def preferences(self, user_id: uuid.UUID) -> list[NotificationPreferenceOut]:
        stored = await self.prefs.of_user(user_id)
        return [
            NotificationPreferenceOut(kind=k, email_enabled=stored[k].email_enabled,
                                      is_default=False)
            if k in stored
            else NotificationPreferenceOut(kind=k, email_enabled=k in EMAIL_DEFAULT_ON,
                                           is_default=True)
            for k in ALL_KINDS
        ]  # fmt: skip

    async def update_preferences(
        self, user_id: uuid.UUID, items: list[PreferenceItem]
    ) -> list[NotificationPreferenceOut]:
        before = {p.kind: p.email_enabled for p in await self.preferences(user_id)}
        stored = await self.prefs.of_user(user_id)
        for item in {i.kind: i for i in items}.values():  # last item per kind wins
            row = stored.get(item.kind)
            if row is None:
                await self.prefs.create(user_id=user_id, kind=item.kind,
                                        email_enabled=item.email_enabled,
                                        created_by=user_id)  # fmt: skip
            elif row.email_enabled != item.email_enabled:
                await self.prefs.update(row, email_enabled=item.email_enabled,
                                        updated_by=user_id)  # fmt: skip
        out = await self.preferences(user_id)
        await record_audit(
            self.db, action="platform.notification_preference_update",
            target_schema="platform", target_table="notification_preferences",
            target_id=user_id, before=before, after={p.kind: p.email_enabled for p in out},
        )  # fmt: skip
        return out

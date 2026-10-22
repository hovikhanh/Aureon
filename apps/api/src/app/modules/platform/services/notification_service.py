"""Public notification service (ENT-Notification, 05 §5; FR-NTF). Other modules create in-app
notifications through this service (never importing `platform.models` — DEC-125). A write runs
in the caller's transaction so the notification and the triggering mutation commit together.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.platform.models import Notification


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

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
        notif = Notification(
            recipient_id=recipient_id,
            kind=kind,
            title=title,
            body=body,
            link=link,
            ref_schema=ref_schema,
            ref_table=ref_table,
            ref_id=ref_id,
        )
        self.db.add(notif)
        await self.db.flush()
        return notif.id

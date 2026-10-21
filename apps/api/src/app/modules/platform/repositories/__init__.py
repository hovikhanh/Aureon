"""Repositories of `platform` — used only inside this module (DEC-125)."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.platform.models import OutboxEvent, ProcessedEvent

DeadLetterRow = tuple[ProcessedEvent, OutboxEvent]


class DeadLetterRepository:
    """DLQ = `processed_events.status = 'DLQ'` (10 §8.2 E4), joined to the outbox row."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _base(self) -> Any:
        return (
            select(ProcessedEvent, OutboxEvent)
            .join(OutboxEvent, OutboxEvent.id == ProcessedEvent.event_id)
            .where(ProcessedEvent.status == "DLQ")
        )

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        consumer: str | None = None,
        event_type: str | None = None,
    ) -> tuple[Sequence[DeadLetterRow], int]:
        stmt = self._base()
        if consumer:
            stmt = stmt.where(ProcessedEvent.consumer == consumer)
        if event_type:
            stmt = stmt.where(OutboxEvent.event_type == event_type)
        total = int(
            (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        )
        stmt = stmt.order_by(ProcessedEvent.processed_at.desc(), ProcessedEvent.id)
        rows = (await self.db.execute(stmt.limit(limit).offset(offset))).all()
        return [(p, o) for p, o in rows], total

    async def get(self, id_: uuid.UUID) -> DeadLetterRow | None:
        row = (await self.db.execute(self._base().where(ProcessedEvent.id == id_))).first()
        return None if row is None else (row[0], row[1])

    async def dlq_count(self) -> int:
        stmt = select(func.count()).where(ProcessedEvent.status == "DLQ")
        return int((await self.db.execute(stmt)).scalar_one())

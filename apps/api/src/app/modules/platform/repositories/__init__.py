"""Repositories of `platform` — used only inside this module (DEC-125)."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import Actor, record_audit
from app.modules.platform.models import AuditLog, OutboxEvent, ProcessedEvent

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


class AuditRepository:
    """Append-only: `create` + `list` only — no update/delete by design (T-012 / brief T-007)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        action: str,
        target_schema: str | None = None,
        target_table: str | None = None,
        target_id: uuid.UUID | None = None,
        before: Any = None,
        after: Any = None,
        why: str | None = None,
        metadata: dict[str, Any] | None = None,
        actor: Actor | None = None,
    ) -> AuditLog:
        audit_id = await record_audit(
            self.db,
            action=action,
            target_schema=target_schema,
            target_table=target_table,
            target_id=target_id,
            before=before,
            after=after,
            why=why,
            metadata=metadata,
            actor=actor,
        )
        return (await self.db.execute(select(AuditLog).where(AuditLog.id == audit_id))).scalar_one()

    async def list(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        action: str | None = None,
        target_table: str | None = None,
        target_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> tuple[Sequence[AuditLog], int]:
        stmt = select(AuditLog)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if target_table:
            stmt = stmt.where(AuditLog.target_table == target_table)
        if target_id:
            stmt = stmt.where(AuditLog.target_id == target_id)
        if actor_user_id:
            stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
        total = int(
            (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        )
        stmt = stmt.order_by(AuditLog.occurred_at.desc(), AuditLog.id).limit(limit).offset(offset)
        return (await self.db.execute(stmt)).scalars().all(), total

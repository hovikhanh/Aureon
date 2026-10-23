"""`ai` repositories."""

import uuid
from collections.abc import Collection, Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_repository import BaseRepository
from app.modules.ai.models import AIAction, Insight, ModelCallLog


class AIActionRepository(BaseRepository[AIAction]):
    """ENT-AIAction — tenant-scoped (R-DEC-21)."""

    model = AIAction

    async def by_id(self, action_id: uuid.UUID, *, lock: bool = False) -> AIAction | None:
        stmt = self._scoped(select(AIAction)).where(AIAction.id == action_id)
        if lock:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, *, status: str | None = None, autonomy_level: str | None = None
    ) -> Sequence[AIAction]:
        stmt = self._scoped(select(AIAction)).where(AIAction.on_behalf_of == user_id)
        if status is not None:
            stmt = stmt.where(AIAction.status == status)
        if autonomy_level is not None:
            stmt = stmt.where(AIAction.autonomy_level == autonomy_level)
        stmt = stmt.order_by(AIAction.created_at.desc())
        return (await self.db.execute(stmt)).scalars().all()

    async def executed_before(
        self, cutoff: datetime, levels: Collection[str]
    ) -> Sequence[AIAction]:
        stmt = self._scoped(select(AIAction)).where(
            AIAction.status == "executed", AIAction.autonomy_level.in_(levels),
            AIAction.executed_at.is_not(None), AIAction.executed_at <= cutoff,
        )  # fmt: skip
        return (await self.db.execute(stmt)).scalars().all()


class InsightRepository(BaseRepository[Insight]):
    """ENT-Insight — tenant-scoped (R-DEC-21)."""

    model = Insight

    async def active_for_role(
        self, role: str, *, pillar: str | None, kind: str | None, severity: str | None
    ) -> Sequence[Insight]:
        stmt = self._scoped(select(Insight)).where(
            Insight.status == "active", Insight.audience_roles.op("@>")([role])
        )
        if pillar is not None:
            stmt = stmt.where(Insight.pillar == pillar)
        if kind is not None:
            stmt = stmt.where(Insight.kind == kind)
        if severity is not None:
            stmt = stmt.where(Insight.severity == severity)
        return (await self.db.execute(stmt.order_by(Insight.created_at.desc()))).scalars().all()

    async def for_role(self, insight_id: uuid.UUID, role: str) -> Insight | None:
        stmt = self._scoped(select(Insight)).where(
            Insight.id == insight_id, Insight.audience_roles.op("@>")([role])
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()


class ModelCallLogRepository:
    """ENT-ModelCallLog — append-only (insert + aggregate reads only)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, row: ModelCallLog) -> uuid.UUID:
        self.db.add(row)
        await self.db.flush()
        return row.id

    async def cost_since(self, since: datetime) -> int:
        stmt = select(func.coalesce(func.sum(ModelCallLog.estimated_cost_micro_usd), 0)).where(
            ModelCallLog.created_at >= since
        )
        return int((await self.db.execute(stmt)).scalar_one())


def month_start(now: datetime | None = None) -> datetime:
    n = now or datetime.now(UTC)
    return n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

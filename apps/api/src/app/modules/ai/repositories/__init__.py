"""`ai` repositories."""

import uuid
from collections.abc import Collection, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_repository import BaseRepository
from app.core.tenant import current_tenant, require_tenant
from app.modules.ai.models import (
    AgentProfile,
    AIAction,
    AutonomyPolicy,
    Insight,
    ModelCallLog,
    ToolCallLog,
)


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
        tenant = current_tenant()
        if tenant is not None:  # R-DEC-74; beat jobs without a tenant context see all rows
            stmt = stmt.where(ModelCallLog.tenant_id == tenant)
        return int((await self.db.execute(stmt)).scalar_one())


def month_start(now: datetime | None = None) -> datetime:
    n = now or datetime.now(UTC)
    return n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class AgentProfileRepository(BaseRepository[AgentProfile]):
    """ENT-AIAgent (`ai.agent_profiles`) — tenant-scoped config (R-DEC-71)."""

    model = AgentProfile

    async def by_code(self, code: str) -> AgentProfile | None:
        stmt = self._scoped(select(AgentProfile)).where(AgentProfile.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def all(self) -> Sequence[AgentProfile]:
        stmt = self._scoped(select(AgentProfile)).order_by(AgentProfile.code)
        return (await self.db.execute(stmt)).scalars().all()

    async def max_level(self, code: str) -> str | None:
        stmt = self._scoped(select(AgentProfile.max_autonomy_level)).where(
            AgentProfile.code == code
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()


class AutonomyPolicyRepository(BaseRepository[AutonomyPolicy]):
    """ENT-AutonomyPolicy — tenant-scoped, soft-deleted (R-DEC-73)."""

    model = AutonomyPolicy

    async def active_for(self, action_name: str) -> Sequence[AutonomyPolicy]:
        stmt = self._scoped(select(AutonomyPolicy)).where(
            AutonomyPolicy.action_name == action_name,
            AutonomyPolicy.is_active.is_(True),
            AutonomyPolicy.deleted_at.is_(None),
        )
        return (await self.db.execute(stmt)).scalars().all()

    async def live(self, policy_id: uuid.UUID) -> AutonomyPolicy | None:
        stmt = self._scoped(select(AutonomyPolicy)).where(
            AutonomyPolicy.id == policy_id, AutonomyPolicy.deleted_at.is_(None)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def key_taken(
        self, action: str, agent: str | None, role: str | None, amount: int | None,
        *, exclude: uuid.UUID | None = None,
    ) -> bool:  # fmt: skip
        stmt = self._scoped(select(AutonomyPolicy.id)).where(
            AutonomyPolicy.action_name == action,
            AutonomyPolicy.agent_profile_code.is_not_distinct_from(agent),
            AutonomyPolicy.role_code.is_not_distinct_from(role),
            AutonomyPolicy.max_amount.is_not_distinct_from(amount),
            AutonomyPolicy.deleted_at.is_(None),
        )
        if exclude is not None:
            stmt = stmt.where(AutonomyPolicy.id != exclude)
        return (await self.db.execute(stmt)).first() is not None

    async def page(
        self, *, filters: dict[str, Any], include_deleted: bool, sort_by: str, order: str,
        limit: int, offset: int,
    ) -> tuple[Sequence[AutonomyPolicy], int]:  # fmt: skip
        stmt = self._scoped(select(AutonomyPolicy))
        if not include_deleted:
            stmt = stmt.where(AutonomyPolicy.deleted_at.is_(None))
        for name, val in filters.items():
            if val is not None:
                stmt = stmt.where(getattr(AutonomyPolicy, name) == val)
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar()
        col = getattr(AutonomyPolicy, sort_by)
        stmt = stmt.order_by(col.asc() if order == "asc" else col.desc(), AutonomyPolicy.id)
        rows = (await self.db.execute(stmt.limit(limit).offset(offset))).scalars().all()
        return rows, int(total or 0)


class CallLogQueryRepository:
    """EP-AI-22/23 reads over the append-only logs, always `WHERE tenant_id = current` (R-DEC-74).

    Logs have their own `tenant_id` column (no `TenantMixin`, like the outbox) — the filter is
    explicit here instead of the session guard.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def page(
        self, model: type[ToolCallLog] | type[ModelCallLog], *, filters: dict[str, Any],
        start: datetime, end: datetime, sort_by: str, order: str, limit: int, offset: int,
    ) -> tuple[Sequence[Any], int]:  # fmt: skip
        stmt = select(model).where(
            model.tenant_id == require_tenant(),
            model.created_at >= start,
            model.created_at <= end,
        )
        for name, val in filters.items():
            if val is not None:
                stmt = stmt.where(getattr(model, name) == val)
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar()
        col = getattr(model, sort_by)
        stmt = stmt.order_by(col.asc() if order == "asc" else col.desc(), model.id)
        rows = (await self.db.execute(stmt.limit(limit).offset(offset))).scalars().all()
        return rows, int(total or 0)

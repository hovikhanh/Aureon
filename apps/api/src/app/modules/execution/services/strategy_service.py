"""EP-STR-02..11 Strategy + StrategicObjective (10 §7.2.3; 05 §2.6; R-DEC-50, T-626).

- Strategy: unique live `code` (409), `period_end > period_start` (422 VALIDATION_ERROR),
  ≤ 1 `active` Strategy with an overlapping period per tenant (checked under `FOR UPDATE`
  → 422 `overlapping_active_strategy`); delete blocked while a live SO exists (`has_live_children`).
- StrategicObjective: unique live `code`; `progress_pct` is system-computed
  (`recompute_progress`); delete blocked while a live KPI / Objective / Initiative links to it
  (`has_live_links`). Scope: `goal_scope` (R-DEC-57).
"""

import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ValidationError
from app.core.pagination import PageParams
from app.modules.execution.models import (
    Initiative,
    Kpi,
    Objective,
    StrategicObjective,
    Strategy,
)
from app.modules.execution.repositories import (
    InitiativeRepository,
    KpiRepository,
    ObjectiveRepository,
    StrategicObjectiveRepository,
    StrategyRepository,
)
from app.modules.execution.schemas.strategy import (
    StrategicObjectiveCreate,
    StrategicObjectiveOut,
    StrategicObjectiveUpdate,
    StrategyCreate,
    StrategyOut,
    StrategyUpdate,
)
from app.modules.execution.services import goal_scope
from app.modules.execution.services.base import ExecBase, not_found
from app.modules.execution.services.meeting_service import _c19

RULE = "FR-STR-01"
Q = Decimal("0.0001")


def strategy_out(s: Strategy) -> StrategyOut:
    return StrategyOut(
        **_c19(s), code=s.code, name=s.name, vision=s.vision, mission=s.mission,
        period_start=s.period_start, period_end=s.period_end, owner_id=s.owner_id,
        status=s.status,
    )  # fmt: skip


def so_out(o: StrategicObjective, **counts: int) -> StrategicObjectiveOut:
    return StrategicObjectiveOut(
        **_c19(o), strategy_id=o.strategy_id, code=o.code, title=o.title,
        description=o.description, pillar=o.pillar, owner_id=o.owner_id,
        department_id=o.department_id, weight_pct=float(o.weight_pct), sort_order=o.sort_order,
        status=o.status, progress_pct=float(o.progress_pct), **counts,
    )  # fmt: skip


def so_progress(initiatives: list[tuple[Any, Any]], objectives: list[Any]) -> Decimal:
    """05 §2.6: weighted mean of initiatives `(progress, weight)` (all weights 0 → plain mean);
    no initiative → mean of the directly linked objectives' progress; none → 0."""
    p: Decimal
    if initiatives:
        total_w = sum((Decimal(w) for _, w in initiatives), Decimal(0))
        if total_w > 0:
            p = sum((Decimal(v) * Decimal(w) for v, w in initiatives), Decimal(0)) / total_w
        else:
            p = sum((Decimal(v) for v, _ in initiatives), Decimal(0)) / len(initiatives)
    elif objectives:
        p = sum((Decimal(v) for v in objectives), Decimal(0)) / len(objectives)
    else:
        p = Decimal(0)
    return p.quantize(Q, rounding=ROUND_HALF_UP)


def _rule(msg: str, reason: str, **details: Any) -> BusinessRuleError:
    return BusinessRuleError(msg, details={"rule": RULE, "reason": reason, **details})


class StrategyService(ExecBase):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.strategies = StrategyRepository(db)
        self.sos = StrategicObjectiveRepository(db)

    # ---------- strategies ----------
    async def list_strategies(
        self, page: PageParams, *, status: str | None
    ) -> tuple[list[StrategyOut], int]:
        items, total = await self.strategies.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters={"status": status} if status is not None else {},
        )  # fmt: skip
        return [strategy_out(s) for s in items], total

    async def get_strategy(self, id_: uuid.UUID) -> Strategy:
        s = await self.strategies.get(id_)
        if s is None:
            raise not_found("strategy")
        return s

    async def _no_overlap(
        self, status: str, start: date, end: date, exclude: uuid.UUID | None
    ) -> None:
        if end <= start:
            raise ValidationError("period_end must be after period_start",
                                  details={"field": "period_end"})  # fmt: skip
        if status == "active" and await self.strategies.active_overlapping(start, end, exclude):
            raise _rule("another active strategy overlaps this period",
                        "overlapping_active_strategy", field="status")  # fmt: skip

    async def create_strategy(self, user: Principal, body: StrategyCreate) -> StrategyOut:
        goal_scope.require_strategy_writer(user)
        data = body.model_dump()
        await self.require_unique(Strategy, "code", data["code"], None)
        await self._no_overlap(data["status"], data["period_start"], data["period_end"], None)
        s = await self.strategies.create(**data, source="MANUAL", created_by=user.user_id)
        await self.db.refresh(s)
        out = strategy_out(s)
        await self.audit("strategy_create", "strategies", s.id, after=out)
        return out

    async def update_strategy(
        self, user: Principal, id_: uuid.UUID, body: StrategyUpdate, expected: int
    ) -> StrategyOut:
        goal_scope.require_strategy_writer(user)
        s = await self.get_strategy(id_)
        before = strategy_out(s)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        for k in ("name", "period_start", "period_end", "owner_id", "status"):
            if k in data and data[k] is None:
                del data[k]
        await self._no_overlap(data.get("status", s.status),
                               data.get("period_start", s.period_start),
                               data.get("period_end", s.period_end), s.id)  # fmt: skip
        await self.strategies.update(s, expected_version=expected, updated_by=user.user_id,
                                     **data)  # fmt: skip
        await self.db.refresh(s)
        out = strategy_out(s)
        await self.audit("strategy_update", "strategies", s.id, before, out)
        return out

    async def delete_strategy(self, user: Principal, id_: uuid.UUID) -> None:
        goal_scope.require_strategy_writer(user)
        s = await self.get_strategy(id_)
        if await self.sos.where(StrategicObjective.strategy_id == s.id):
            raise _rule("strategy still has strategic objectives", "has_live_children")
        before = strategy_out(s)
        s.updated_by = user.user_id
        await self.strategies.soft_delete(s)
        await self.audit("strategy_delete", "strategies", s.id, before=before)

    # ---------- strategic objectives ----------
    async def list_sos(
        self, user: Principal, page: PageParams, *, strategy_id: uuid.UUID | None,
        pillar: str | None, department_id: uuid.UUID | None,
    ) -> tuple[list[StrategicObjectiveOut], int]:  # fmt: skip
        SO = StrategicObjective
        pred = goal_scope.so_predicate(user, dept=SO.department_id, owner=SO.owner_id,
                                       pillar=SO.pillar)  # fmt: skip
        raw = {"strategy_id": strategy_id, "pillar": pillar, "department_id": department_id}
        items, total = await self.sos.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters={k: v for k, v in raw.items() if v is not None},
            where=[pred] if pred is not None else [],
        )  # fmt: skip
        return [so_out(o) for o in items], total

    async def get_so(self, user: Principal, id_: uuid.UUID) -> StrategicObjective:
        o = await self.sos.get(id_)
        if o is None:
            raise not_found("strategic objective")
        goal_scope.check_so_read(user, dept=o.department_id, owner=o.owner_id, pillar=o.pillar)
        return o

    async def _links(self, so_id: uuid.UUID) -> tuple[list[Kpi], list[Objective], list[Initiative]]:
        kpis = await KpiRepository(self.db).where(Kpi.strategic_objective_id == so_id)
        objs = await ObjectiveRepository(self.db).where(Objective.strategic_objective_id == so_id)
        inis = await InitiativeRepository(self.db).where(Initiative.strategic_objective_id == so_id)
        return list(kpis), list(objs), list(inis)

    async def so_detail(self, user: Principal, id_: uuid.UUID) -> StrategicObjectiveOut:
        o = await self.get_so(user, id_)
        kpis, objs, inis = await self._links(o.id)
        return so_out(o, kpi_count=len(kpis), objective_count=len(objs),
                      initiative_count=len(inis))  # fmt: skip

    async def create_so(
        self, user: Principal, body: StrategicObjectiveCreate
    ) -> StrategicObjectiveOut:
        data = body.model_dump()
        goal_scope.check_so_write(user, data["pillar"])
        if data["sort_order"] is None:
            data["sort_order"] = 0
        await self.require_refs(data, RULE, strategy_id=Strategy)
        await self.require_unique(StrategicObjective, "code", data["code"], None)
        o = await self.sos.create(**data, status="draft", progress_pct=Decimal(0),
                                  source="MANUAL", created_by=user.user_id)  # fmt: skip
        await self.db.refresh(o)
        out = so_out(o)
        await self.audit("strategic_objective_create", "strategic_objectives", o.id, after=out)
        return out

    async def update_so(
        self, user: Principal, id_: uuid.UUID, body: StrategicObjectiveUpdate, expected: int
    ) -> StrategicObjectiveOut:
        o = await self.get_so(user, id_)
        goal_scope.check_so_write(user, o.pillar)
        before = so_out(o)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        for k in ("code", "title", "owner_id", "weight_pct", "sort_order", "status"):
            if k in data and data[k] is None:
                del data[k]
        if "pillar" in data:
            goal_scope.check_so_write(user, data["pillar"])
        if "code" in data:
            await self.require_unique(StrategicObjective, "code", data["code"], o.id)
        await self.sos.update(o, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(o)
        out = so_out(o)
        await self.audit("strategic_objective_update", "strategic_objectives", o.id, before, out)
        return out

    async def delete_so(self, user: Principal, id_: uuid.UUID) -> None:
        o = await self.get_so(user, id_)
        goal_scope.check_so_write(user, o.pillar)
        if any(await self._links(o.id)):
            raise _rule("strategic objective still has linked KPIs, objectives or initiatives",
                        "has_live_links")  # fmt: skip
        before = so_out(o)
        o.updated_by = user.user_id
        await self.sos.soft_delete(o)
        await self.audit("strategic_objective_delete", "strategic_objectives", o.id, before=before)

    async def recompute_progress(self, so_id: uuid.UUID | None) -> None:
        """05 §2.6 rule, same transaction as the initiative / objective change (EP-STR-15)."""
        if so_id is None:
            return
        o = await self.sos.get(so_id)
        if o is None:
            return
        _, objs, inis = await self._links(o.id)
        o.progress_pct = so_progress([(i.progress_pct, i.weight_pct) for i in inis],
                                     [x.progress_pct for x in objs])  # fmt: skip
        await self.db.flush()

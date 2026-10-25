"""EP-STR-01 goal alignment tree, EP-PRF-06 check-ins due (10 §7.2.3, 05 §2.6) — T-628.

Tree: one query per entity kind (strategies, SOs, KPIs + latest evaluations, objectives + KRs,
initiatives + projects) — no per-node query, no metric computed at request time: only stored
columns (`progress_pct`, `kpi_evaluations`, KR `at_risk`, `last_checked_in_at`); `on_track` =
the SEI rule (`metrics.sei_on_track`). KPI / Objective depth ≤ 5 (deeper nodes dropped).
Visibility (`goal_scope`): a node out of scope is sent only when it leads to a visible node, as
`{id, code?, title?, restricted: true}`; otherwise it is left out (never `null`).
Roots with no StrategicObjective (`strategic_objective_id` NULL, no parent) → `unaligned`.
"""

import uuid
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import BusinessModel
from app.core.config import get_config
from app.core.deps import Principal
from app.modules.execution.models import (
    Initiative,
    KeyResult,
    Kpi,
    KpiEvaluation,
    Objective,
    StrategicObjective,
    Strategy,
)
from app.modules.execution.repositories import (
    InitiativeRepository,
    KeyResultRepository,
    KpiEvaluationRepository,
    KpiRepository,
    ObjectiveRepository,
    StrategicObjectiveRepository,
    StrategyRepository,
)
from app.modules.execution.schemas.okr import CheckInDueOut
from app.modules.execution.schemas.strategy import (
    GoalTreeOut,
    IniNode,
    IniProjectNode,
    KpiNode,
    KrNode,
    ObjNode,
    SONode,
    StrategyNode,
    UnalignedOut,
)
from app.modules.execution.services import goal_scope
from app.modules.execution.services.at_risk import current_objectives
from app.modules.execution.services.base import num, today
from app.modules.execution.services.kpi_rules import (
    kr_progress_pct,
    last_ended_period,
    local_day,
    period_bounds,
    period_key_for,
    periods_overlap,
)
from app.modules.execution.services.kpi_target_service import evaluation_brief
from app.modules.execution.services.meeting_service import ProjectService
from app.modules.execution.services.metrics import sei_on_track

MAX_DEPTH = 5


class _Forest[R: BusinessModel]:
    """Parent → children index over rows with `id`; prunes subtrees with no visible node."""

    def __init__(self, rows: Sequence[R], parent: Callable[[R], uuid.UUID | None],
                 visible: Callable[[R], bool],
                 anchor: Callable[[R], bool] | None = None) -> None:  # fmt: skip
        self.ids = {r.id for r in rows}
        self.kids: dict[uuid.UUID | None, list[R]] = defaultdict(list)
        for r in rows:
            p = parent(r)
            self.kids[p if p in self.ids else None].append(r)  # orphan of the period → root
        self.visible = visible
        self.anchor = anchor or (lambda _r: False)  # e.g. objective with a KR of the caller

    def roots(self) -> list[R]:
        return self.kids[None]

    def keep(self, r: R, depth: int = 1) -> bool:
        """Visible itself, or an ancestor (≤ MAX_DEPTH) of a visible node."""
        if depth > MAX_DEPTH:
            return False
        return (self.visible(r) or self.anchor(r)
                or any(self.keep(c, depth + 1) for c in self.kids.get(r.id, [])))  # fmt: skip

    def children(self, r: R, depth: int) -> list[R]:
        if depth >= MAX_DEPTH:
            return []
        return [c for c in self.kids.get(r.id, []) if self.keep(c, depth + 1)]


def kr_node(k: KeyResult) -> KrNode:
    return KrNode(
        id=k.id, title=k.title, unit=k.unit, baseline=float(k.baseline), target=float(k.target),
        current_value=num(k.current_value),
        progress_pct=float(kr_progress_pct(k.baseline, k.target, k.current_value)),
        confidence=k.confidence, at_risk=k.at_risk, last_checked_in_at=k.last_checked_in_at,
        owner_id=k.owner_id,
    )  # fmt: skip


class GoalTreeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.strategies = StrategyRepository(db)
        self.sos = StrategicObjectiveRepository(db)
        self.kpis = KpiRepository(db)
        self.evaluations = KpiEvaluationRepository(db)
        self.objectives = ObjectiveRepository(db)
        self.krs = KeyResultRepository(db)
        self.initiatives = InitiativeRepository(db)

    async def tree(
        self, user: Principal, *, strategy_id: uuid.UUID | None, period_key: str | None,
        department_id: uuid.UUID | None,
    ) -> GoalTreeOut:  # fmt: skip
        day = today()
        period = period_key or period_key_for("QUARTER", day)
        start, end = period_bounds(period)
        gs = await goal_scope.resolve(self.db, user)
        gs.check_department_filter(department_id)

        def visible(dept: uuid.UUID | None, owner: uuid.UUID, pillar: str | None) -> bool:
            if department_id is not None and dept != department_id:
                return False
            return gs.readable(dept=dept, owners=(owner,), pillar=pillar)

        if strategy_id is not None:
            strategies = await self.strategies.where(Strategy.id == strategy_id)
        else:
            strategies = await self.strategies.where(
                Strategy.period_start < end, Strategy.period_end > start,
                order=Strategy.period_start)  # fmt: skip
        sos = await self.sos.where(
            StrategicObjective.strategy_id.in_([s.id for s in strategies]),
            order=(StrategicObjective.sort_order, StrategicObjective.code),
        ) if strategies else []  # fmt: skip
        kpis = await self.kpis.where(order=Kpi.code)
        latest = await self.evaluations.latest_for([k.id for k in kpis])
        objs = [o for o in await self.objectives.where(
            Objective.period_key.startswith(period[:4]), order=Objective.title)
            if periods_overlap(o.period_key, period)]  # fmt: skip
        krs_by: dict[uuid.UUID, list[KeyResult]] = defaultdict(list)
        if objs:
            for k in await self.krs.where(KeyResult.objective_id.in_([o.id for o in objs]),
                                          order=KeyResult.title):  # fmt: skip
                krs_by[k.objective_id].append(k)
        inis = await self.initiatives.where(
            Initiative.strategic_objective_id.in_([s.id for s in sos]), order=Initiative.code,
        ) if sos else []  # fmt: skip
        vis_inis = [i for i in inis if visible(i.department_id, i.owner_id, i.pillar)]
        projects = await ProjectService(self.db).of_initiatives(user, [i.id for i in vis_inis])
        proj_by: dict[uuid.UUID, list[IniProjectNode]] = defaultdict(list)
        for p in projects:
            if p.initiative_id is not None:
                proj_by[p.initiative_id].append(
                    IniProjectNode(id=p.id, code=p.code, name=p.name, status=p.status)
                )

        kf = _Forest(kpis, lambda k: k.parent_kpi_id,
                     lambda k: visible(k.department_id, k.owner_id, k.pillar))  # fmt: skip

        def kr_visible(o: Objective, k: KeyResult) -> bool:
            """KR owner sees it under an out-of-scope objective (EMP own KR, R-DEC-57)."""
            return visible(o.department_id, k.owner_id, o.pillar)

        of = _Forest(objs, lambda o: o.parent_id,
                     lambda o: visible(o.department_id, o.owner_id, o.pillar),
                     lambda o: any(kr_visible(o, k) for k in krs_by.get(o.id, [])))  # fmt: skip

        def kpi_node(k: Kpi, depth: int) -> KpiNode:
            kids = [kpi_node(c, depth + 1) for c in kf.children(k, depth)]
            if not kf.visible(k):
                return KpiNode(id=k.id, code=k.code, name=k.name, restricted=True, children=kids)
            ev: KpiEvaluation | None = latest.get(k.id)
            return KpiNode(
                id=k.id, code=k.code, name=k.name, unit=k.unit, direction=k.direction,
                owner_id=k.owner_id, department_id=k.department_id,
                latest_evaluation=evaluation_brief(ev), children=kids,
            )  # fmt: skip

        def obj_node(o: Objective, depth: int) -> ObjNode:
            kids = [obj_node(c, depth + 1) for c in of.children(o, depth)]
            krs = krs_by.get(o.id, [])
            if not of.visible(o):
                return ObjNode(
                    id=o.id,
                    title=o.title,
                    restricted=True,
                    children=kids,
                    key_results=[kr_node(k) for k in krs if kr_visible(o, k)],
                )
            return ObjNode(
                id=o.id, title=o.title, period_key=o.period_key, level=o.level, status=o.status,
                progress_pct=float(o.progress_pct), owner_id=o.owner_id,
                department_id=o.department_id, at_risk_kr_count=sum(k.at_risk for k in krs),
                key_results=[kr_node(k) for k in krs], children=kids,
            )  # fmt: skip

        def ini_node(i: Initiative) -> IniNode:
            return IniNode(
                id=i.id, code=i.code, title=i.title, status=i.status,
                progress_pct=float(i.progress_pct), start_date=i.start_date,
                planned_end_date=i.planned_end_date,
                on_track=None if i.status == "cancelled" else sei_on_track(i, day),
                projects=proj_by.get(i.id, []),
            )  # fmt: skip

        return self._assemble(gs, strategies, sos, kf, of, vis_inis, kpi_node, obj_node,
                              ini_node, filtered=department_id is not None,
                              with_unaligned=strategy_id is None)  # fmt: skip

    @staticmethod
    def _assemble(
        gs: goal_scope.GoalScope, strategies: Sequence[Strategy],
        sos: Sequence[StrategicObjective],
        kf: "_Forest[Kpi]", of: "_Forest[Objective]", inis: Sequence[Initiative],
        kpi_node: Callable[[Kpi, int], KpiNode], obj_node: Callable[[Objective, int], ObjNode],
        ini_node: Callable[[Initiative], IniNode], *, filtered: bool, with_unaligned: bool,
    ) -> GoalTreeOut:  # fmt: skip
        so_ids = {s.id for s in sos}
        root_kpis: dict[uuid.UUID | None, list[Kpi]] = defaultdict(list)
        for k in kf.roots():
            if kf.keep(k) and (k.strategic_objective_id in so_ids or k.strategic_objective_id
                               is None):  # fmt: skip
                root_kpis[k.strategic_objective_id].append(k)
        root_objs: dict[uuid.UUID | None, list[Objective]] = defaultdict(list)
        for o in of.roots():
            if of.keep(o) and (o.strategic_objective_id in so_ids or o.strategic_objective_id
                               is None):  # fmt: skip
                root_objs[o.strategic_objective_id].append(o)
        ini_by: dict[uuid.UUID, list[Initiative]] = defaultdict(list)
        for i in inis:
            if i.strategic_objective_id is not None:
                ini_by[i.strategic_objective_id].append(i)
        by_strategy: dict[uuid.UUID, list[SONode]] = defaultdict(list)
        for s in sos:
            kids: dict[str, Any] = {
                "kpis": [kpi_node(k, 1) for k in root_kpis.get(s.id, [])],
                "objectives": [obj_node(o, 1) for o in root_objs.get(s.id, [])],
                "initiatives": [ini_node(i) for i in ini_by.get(s.id, [])],
            }
            has_kids = any(kids.values())
            readable = goal_scope.so_readable(gs, dept=s.department_id, owner=s.owner_id,
                                              pillar=s.pillar)  # fmt: skip
            if (filtered or not readable) and not has_kids:
                continue
            if not readable:
                by_strategy[s.strategy_id].append(
                    SONode(id=s.id, code=s.code, title=s.title, restricted=True, **kids)
                )
                continue
            by_strategy[s.strategy_id].append(SONode(
                id=s.id, code=s.code, title=s.title, pillar=s.pillar, owner_id=s.owner_id,
                department_id=s.department_id, progress_pct=float(s.progress_pct),
                status=s.status, **kids))  # fmt: skip
        nodes = [StrategyNode(
            id=s.id, code=s.code, name=s.name, status=s.status, period_start=s.period_start,
            period_end=s.period_end, owner_id=s.owner_id,
            strategic_objectives=by_strategy.get(s.id, []),
        ) for s in strategies if not filtered or by_strategy.get(s.id)]  # fmt: skip
        unaligned = UnalignedOut(
            kpis=[kpi_node(k, 1) for k in root_kpis.get(None, [])],
            objectives=[obj_node(o, 1) for o in root_objs.get(None, [])],
        ) if with_unaligned else UnalignedOut()  # fmt: skip
        return GoalTreeOut(strategies=nodes, unaligned=unaligned)

    # ---------- EP-PRF-06 ----------
    async def check_ins_due(self, user: Principal) -> list[CheckInDueOut]:
        """F4 card of the caller: KRs of `active` objectives whose period contains today +
        `active` KPIs, owned by the caller (`owner_id = Principal.user_id`). `due`: KR not
        checked in within `GOALS_KR_CHECKIN_MAX_AGE_DAYS`; KPI whose last ended period has no
        evaluation yet. `prefill` stays `null` at M1.4."""
        day = today()
        cfg = get_config()
        me = user.user_id
        out: list[CheckInDueOut] = []
        objs = {o.id: o for o in await current_objectives(self.db, day)}
        if objs:
            mine = await self.krs.where(
                KeyResult.objective_id.in_(list(objs)), KeyResult.owner_id == me,
                order=KeyResult.title)  # fmt: skip
            for kr in mine:
                last = kr.last_checked_in_at
                fresh = last is not None and local_day(last) >= day - timedelta(
                    days=cfg.goals_kr_checkin_max_age_days)  # fmt: skip
                out.append(CheckInDueOut(
                    target_type="key_result", target_id=kr.id, title=kr.title, unit=kr.unit,
                    current_value=num(kr.current_value), target=float(kr.target),
                    confidence=kr.confidence, last_checked_in_at=last, due=not fresh))  # fmt: skip
        kpis = await self.kpis.where(Kpi.status == "active", Kpi.owner_id == me, order=Kpi.code)
        evs = await self.evaluations.of_periods(
            [(k.id, last_ended_period(k.period_type, day)) for k in kpis]
        )
        latest = await self.evaluations.latest_for([k.id for k in kpis])
        for k in kpis:
            ev = latest.get(k.id)
            out.append(CheckInDueOut(
                target_type="kpi", target_id=k.id, title=k.name, unit=k.unit,
                current_value=None if ev is None else float(ev.actual_value),
                target=float(k.target_value), confidence=None, last_checked_in_at=None,
                due=(k.id, last_ended_period(k.period_type, day)) not in evs))  # fmt: skip
        return out

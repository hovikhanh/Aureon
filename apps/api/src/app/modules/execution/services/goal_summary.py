"""Home summaries of OKR / KPI / check-in / workload (EP-RPT-02, EP-RPT-03; F6).

Public read of `execution` for the reporting dashboards: counts only, computed from the same rows
and rules as the goal screens. "Current" = the `active` objectives whose period contains the day
(`current_objectives`, shared with the at-risk job and the weekly check-in reminder).
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.org_scope import department_subtree
from app.modules.execution.models import CheckIn, KeyResult, Kpi, Objective, Task
from app.modules.execution.repositories import (
    OPEN_TASK_STATUSES,
    CheckInRepository,
    KeyResultRepository,
    KpiRepository,
    TaskRepository,
)
from app.modules.execution.services import scope
from app.modules.execution.services.at_risk import current_objectives, iso_week_start
from app.modules.execution.services.kpi_rules import LOCAL_TZ, period_bounds, period_key_for
from app.modules.execution.services.workload import load_pct, load_tasks, weekly_hours

WEEK_DAYS = 7


@dataclass(frozen=True)
class PendingCheckinRef:
    target_type: str
    target_id: str
    label: str
    period_key: str


@dataclass(frozen=True)
class DueCounts:
    overdue: int
    today: int
    this_week: int


def _since(day: date) -> datetime:
    return datetime.combine(day, time(), tzinfo=LOCAL_TZ)


class GoalSummaryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.krs = KeyResultRepository(db)
        self.kpis = KpiRepository(db)
        self.check_ins = CheckInRepository(db)

    async def _departments(self, department_id: uuid.UUID | None) -> set[uuid.UUID] | None:
        """Department + sub-departments (10 EP-RPT-02); `None` = the whole company."""
        return None if department_id is None else await department_subtree(self.db, [department_id])

    # ---------- EP-RPT-02 ----------
    async def department_okrs(self, department_id: uuid.UUID | None, day: date) -> tuple[int, int]:
        """(objectives with an at-risk KR, current objectives) of the department."""
        depts = await self._departments(department_id)
        objs = [
            o for o in await current_objectives(self.db, day)
            if depts is None or o.department_id in depts
        ]  # fmt: skip
        counts = await self.krs.at_risk_counts([o.id for o in objs])
        return sum(1 for n in counts.values() if n > 0), len(objs)

    async def department_due(self, department_id: uuid.UUID | None, day: date) -> DueCounts:
        """Open tasks of the department: past due, due today, due within the coming week."""
        depts = await self._departments(department_id)
        clauses = [Task.status.in_(OPEN_TASK_STATUSES), Task.due_date.is_not(None),
                   Task.due_date <= day + timedelta(days=WEEK_DAYS)]  # fmt: skip
        if depts is not None:
            clauses.append(Task.department_id.in_(depts))
        rows = await TaskRepository(self.db).where(*clauses, order=Task.id)
        due = [t.due_date for t in rows if t.due_date is not None]
        return DueCounts(
            overdue=sum(1 for d in due if d < day),
            today=sum(1 for d in due if d == day),
            this_week=sum(1 for d in due if d >= day),
        )

    # ---------- EP-RPT-03 ----------
    async def _my_krs(self, user: Principal, objs: Sequence[Objective]) -> Sequence[KeyResult]:
        if not objs:
            return []
        return await self.krs.where(
            KeyResult.objective_id.in_([o.id for o in objs]),
            KeyResult.owner_id.in_(scope.self_ids(user)),
            order=KeyResult.id,
        )

    async def _my_kpis(self, user: Principal) -> Sequence[Kpi]:
        return await self.kpis.where(
            Kpi.status == "active", Kpi.owner_id.in_(scope.self_ids(user)), order=Kpi.id
        )

    async def my_goals(self, user: Principal, day: date) -> tuple[int, int]:
        """(active KPIs, KRs of current objectives) owned by the caller."""
        objs = await current_objectives(self.db, day)
        return len(await self._my_kpis(user)), len(await self._my_krs(user, objs))

    async def _checked_in_since(
        self, ids: Sequence[uuid.UUID], column: str, since: date
    ) -> set[uuid.UUID]:
        if not ids:
            return set()
        target = getattr(CheckIn, column)
        rows = await self.check_ins.where(target.in_(ids), CheckIn.checked_in_at >= _since(since))
        return {getattr(c, column) for c in rows}

    async def pending_checkins(self, user: Principal, day: date) -> list[PendingCheckinRef]:
        """KRs without a check-in this ISO week (the F4 weekly rhythm) and KPIs without one in
        their running period, owned by the caller."""
        objs = {o.id: o for o in await current_objectives(self.db, day)}
        krs = await self._my_krs(user, list(objs.values()))
        week = iso_week_start(day)
        kr_done = await self._checked_in_since([k.id for k in krs], "key_result_id", week)
        out = [
            PendingCheckinRef("key_result", str(k.id), k.title, objs[k.objective_id].period_key)
            for k in krs if k.id not in kr_done
        ]  # fmt: skip
        for k in await self._my_kpis(user):
            key = period_key_for(k.period_type, day)
            done = await self._checked_in_since([k.id], "kpi_id", period_bounds(key)[0])
            if k.id not in done:
                out.append(PendingCheckinRef("kpi", str(k.id), k.name, key))
        return out

    async def workload_week_pct(self, user: Principal, day: date) -> float:
        """METRIC-HR-03 load of the caller for the week ending `day`; no open task → 0."""
        hours = weekly_hours(await load_tasks(self.db, None, day), day)
        mine = sum((hours[i][1] for i in scope.self_ids(user) if i in hours), Decimal(0))
        return float(load_pct(mine))

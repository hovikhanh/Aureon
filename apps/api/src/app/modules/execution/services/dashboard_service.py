"""EP-49 `/execution/dashboard` — execution half of PIL-O (10 §5, OQ-06), T-222.

`summary` is computed live from tasks / projects for the caller's scope (MANAGER and EMPLOYEE
pinned to their department, DEC-220) using the same pure functions as the metric provider
(OPS-01/02/03, HR-03). `metrics[]` + `open_alerts` come from the metric store (company scope,
`platform.pillar_snapshot`, isolated) and are only returned to company-wide readers.
"""

import uuid
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import month_key, month_range, shift_month
from app.core.deps import Principal
from app.core.periods import Period
from app.modules.execution.models import Task
from app.modules.execution.repositories import ProjectRepository, TaskRepository
from app.modules.execution.schemas.dashboard import (
    ExecPeriodOut,
    ExecutionDashboardOut,
    ExecutionSummary,
    HeatCell,
    OnTimePoint,
)
from app.modules.execution.services import metrics as m
from app.modules.execution.services import scope
from app.modules.execution.services.workload import load_tasks, rows_from, weekly_grid
from app.modules.platform.services.pillar_snapshot import (
    PillarSnapshot,
    pillar_snapshot,
    pillar_status_of,
)

TREND_MONTHS = 6
HEAT_WEEKS = 4
STATUS_CODES = ("METRIC-OPS-01", "METRIC-OPS-02", "METRIC-OPS-03", "METRIC-HR-03")


def _in_dept(rows: Sequence[Task], dept: uuid.UUID | None) -> list[Task]:
    return [t for t in rows if dept is None or t.department_id == dept]


class ExecutionDashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.tasks = TaskRepository(db)

    @staticmethod
    def department(user: Principal, requested: uuid.UUID | None) -> uuid.UUID | None:
        if scope.level(user, "query") == "all":
            return requested
        if user.department_id is None or requested not in (None, user.department_id):
            raise scope.deny("department", department_id=requested)
        return user.department_id

    async def _due(self, start: date, end: date, dept: uuid.UUID | None) -> list[Task]:
        due = await self.tasks.due_between(start, end + timedelta(days=1))
        return [t for t in _in_dept(due, dept) if t.status != "cancelled"]

    async def dashboard(
        self, user: Principal, period: Period, today: date, department_id: uuid.UUID | None
    ) -> ExecutionDashboardOut:
        dept = self.department(user, department_id)
        as_of = min(period.end, today)
        key = period.key
        due = await self._due(period.start, as_of, dept)
        projects = [p for p in await ProjectRepository(self.db).running(as_of)
                    if dept is None or p.department_id == dept]  # fmt: skip
        ptasks = await self.tasks.for_parents(Task.project_id, [p.id for p in projects])
        loads = await load_tasks(self.db, dept, as_of)
        ops01, ops03 = m.ops01(due, key), m.ops03(due, key)
        ops02 = m.ops02(projects, ptasks, as_of, key)
        summary = ExecutionSummary(
            tasks_on_time_pct=ops01.value, projects_late=len(ops02.records),
            decision_execution_pct=ops03.value,
            overloaded_count=sum(r.overloaded for r in rows_from(loads, as_of)),
        )  # fmt: skip
        snap = await pillar_snapshot(self.db, "O") if dept is None else PillarSnapshot()
        mine = [x for x in snap.metrics if x["metric_code"] in STATUS_CODES]
        status = pillar_status_of([str(x["status"]) for x in mine]) if mine else "no_data"
        return ExecutionDashboardOut(
            status=cast(Literal["ok", "warning", "critical", "no_data"], status),
            period=ExecPeriodOut(
                key=key, type=period.type, start_date=period.start, end_date=period.end
            ),
            summary=summary,
            metrics=mine,
            open_alerts=snap.open_alerts,
            workload_heatmap=await self._heatmap(dept, as_of),
            ontime_trend=await self._trend(dept, as_of),
        )

    async def _heatmap(self, dept: uuid.UUID | None, as_of: date) -> list[HeatCell]:
        """Sparse view of `weekly_grid` (shared with EP-TASK-18): week, then person."""
        rows = await weekly_grid(self.db, dept, as_of, HEAT_WEEKS)
        cells = [(c.week, str(r.employee_id), c) for r in rows for c in r.cells if c.open_tasks]
        return [HeatCell(employee_ref=emp, week=week, load_pct=c.load_pct)
                for week, emp, c in sorted(cells, key=lambda x: (x[0], x[1]))]  # fmt: skip

    async def _trend(self, dept: uuid.UUID | None, as_of: date) -> list[OnTimePoint]:
        out = []
        for i in range(TREND_MONTHS - 1, -1, -1):
            key = shift_month(month_key(as_of), -i)
            start, end = month_range(key)
            due = await self._due(start, min(end - timedelta(days=1), as_of), dept)
            out.append(OnTimePoint(period_key=key, tasks_on_time_pct=m.ops01(due, key).value))
        return out

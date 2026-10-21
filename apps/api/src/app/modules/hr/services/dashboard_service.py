"""EP-80 HR dashboard (FR-HR-06, 10 §5) and EP-87 workload (METRIC-HR-03).

Scope (02 §6.2, 02 §5.3 `hr:query`): CEO / HR_MANAGER / CFO / RISK_MANAGER see company
aggregates; MANAGER (`hr:query d`) sees their own department. `summary.payroll_total` is the
aggregate payroll fund (sum of each on-payroll employee's latest `base_salary` at period end)
and is present only for CEO, HR_MANAGER, CFO — for every other role the key is **omitted**,
never `null` (DEC-197). No individual salary or PII is ever returned.

`revenue_per_employee` (METRIC-HR-01) needs finance revenue: `hr` must not import finance
models (DEC-125) and finance exposes no public revenue service yet, so it is `null` until the
metric store (T-220) feeds it. `metrics[]` and `open_alerts` are likewise owned by the metric
store / alert engine (T-220) → `[]` / `null` here; the pillar `status` is computed from the
live turnover (METRIC-HR-02) and delayed-plan (METRIC-HR-04) values.
"""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import ScopeDeniedError
from app.modules.hr.models import Employee, HiringPlan
from app.modules.hr.repositories import (
    EmployeeRepository,
    HiringPlanRepository,
    SalaryRepository,
)
from app.modules.hr.schemas import (
    HeadcountPoint,
    HrDashboardOut,
    PeriodOut,
    TurnoverPoint,
    WorkloadOut,
)
from app.modules.hr.services.metrics import (
    Period,
    Tenure,
    average_tenure_months,
    delay_status,
    hires,
    leavers,
    on_payroll,
    period_turnover_pct,
    trend_months,
    turnover_status,
    worst,
)
from app.modules.hr.services.scope import DEPARTMENT_ROLES, sees_payroll

CURRENCY = "VND"


class HrDashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.employees = EmployeeRepository(db)
        self.salaries = SalaryRepository(db)
        self.plans = HiringPlanRepository(db)

    @staticmethod
    def _department(user: Principal, requested: uuid.UUID | None) -> uuid.UUID | None:
        if user.role in DEPARTMENT_ROLES:
            if user.department_id is None or requested not in (None, user.department_id):
                raise ScopeDeniedError(
                    "department outside your scope", details={"department_id": str(requested)}
                )
            return user.department_id
        return requested

    async def dashboard(self, user: Principal, period: Period, today: date) -> HrDashboardOut:
        dept = self._department(user, None)
        emp_where: list[ColumnElement[bool]] = []
        plan_where: list[ColumnElement[bool]] = []
        if dept is not None:
            emp_where.append(Employee.department_id == dept)
            plan_where.append(HiringPlan.department_id == dept)
        raw = await self.employees.roster(emp_where)
        rows = [Tenure(h, t) for h, t, _ in raw]
        end = period.end
        current = on_payroll(rows, end)
        live_status = [s for _, t, s in raw if t is None or t > end]
        turnover = period_turnover_pct(rows, period.start, end, period.months)
        late = await self.plans.late_days(today, plan_where)

        summary: dict[str, Any] = {
            "headcount": len(current),
            "active": live_status.count("active") + live_status.count("probation"),
            "on_leave": live_status.count("on_leave"),
            "terminated": leavers(rows, period.start, end),
            "new_hires": hires(rows, period.start, end),
            "turnover_rate_pct": turnover,
            "avg_tenure_months": average_tenure_months([r.hire_date for r in current], end),
        }
        if sees_payroll(user):
            summary["payroll_total"] = await self.salaries.payroll_on(end, emp_where)
        summary["open_positions"] = await self.plans.open_positions(plan_where)
        summary["revenue_per_employee"] = None
        summary["currency"] = CURRENCY

        months = trend_months(end)
        headcount_trend = [
            HeadcountPoint(period_key=k, headcount=len(on_payroll(rows, e))) for k, _, e in months
        ]
        turnover_trend = [
            TurnoverPoint(period_key=k, turnover_rate_pct=period_turnover_pct(rows, s, e, 1) or 0.0)
            for k, s, e in months
        ]
        status = worst(turnover_status(turnover), delay_status(late) if rows or late else None)
        period_out = PeriodOut(
            key=period.key, type=period.type, start_date=period.start, end_date=end
        )
        return HrDashboardOut(
            status=status, period=period_out, summary=summary, metrics=[],
            headcount_trend=headcount_trend, turnover_trend=turnover_trend, open_alerts=None,
        )  # fmt: skip

    async def workload(
        self, user: Principal, *, department_id: uuid.UUID | None
    ) -> list[WorkloadOut]:
        """EP-87 `[{ employee_ref, open_tasks, load_pct, overloaded }]` (METRIC-HR-03).

        Workload needs `execution.tasks` (estimate_hours / assignee), read only through the
        `execution` public service, which exposes no task API yet (execution tasks module not
        built, T-13x). Until then the endpoint enforces scope and returns an empty list — the
        documented "no data" state, not a fabricated value (BRD-P05).
        """
        self._department(user, department_id)
        return []

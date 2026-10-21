"""HR metric provider — METRIC-HR-01, HR-02, HR-04 (HR-03 comes from execution) — DEC-205.

HR-02: BR-HR-01 annualized turnover over the rolling 12 months ending at the last closed month.
HR-01: 12-month revenue (finance public `revenue_total`) ÷ average headcount of those 12 month
ends; `threshold_input` = % below `HR_REVENUE_PER_HEAD_PLAN` (warning > 15, critical > 25).
HR-04: count of open plans past target; status by the worst delay (1–45 d warning, > 45 critical).
"""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import month_key, shift_month
from app.core.config import get_config
from app.core.data_quality import DqSource, register_dq
from app.core.metrics import MetricReading, metric_provider
from app.modules.finance.services.revenue_query import revenue_total
from app.modules.hr.models import Employee, HiringPlan
from app.modules.hr.repositories import EmployeeRepository, HiringPlanRepository
from app.modules.hr.services.metrics import (
    Tenure,
    delay_status,
    month_end,
    on_payroll,
    period_turnover_pct,
)


def _months(last: str, n: int) -> list[str]:
    return [shift_month(last, -i) for i in range(n - 1, -1, -1)]


def _end(key: str) -> date:
    return month_end(int(key[:4]), int(key[5:7]))


async def compute_hr(db: AsyncSession, as_of: date) -> list[MetricReading]:
    last = shift_month(month_key(as_of), -1)
    months = _months(last, 12)
    rows = [Tenure(h, t) for h, t, _ in await EmployeeRepository(db).roster()]
    start = _end(shift_month(months[0], -1)) + timedelta(days=1)
    turnover = period_turnover_pct(rows, start, _end(last), 12) if rows else None

    heads = [len(on_payroll(rows, _end(m))) for m in months]
    avg_head = sum(heads) / len(heads) if rows else 0
    revenue = await revenue_total(db, months)
    per_head = revenue / avg_head if avg_head and revenue else None
    plan = get_config().hr_revenue_per_head_plan
    below = None if per_head is None else round((plan - per_head) / plan * 100, 1)

    late = await HiringPlanRepository(db).late_days(as_of)
    return [
        MetricReading("METRIC-HR-01", None if per_head is None else round(per_head), last,
                      period_type="ROLLING_12M",
                      threshold_input=below if below is not None else None),
        MetricReading("METRIC-HR-02", turnover, last, period_type="ROLLING_12M"),
        MetricReading("METRIC-HR-04", float(len(late)), month_key(as_of),
                      status=delay_status(late)),
    ]  # fmt: skip


@metric_provider("hr")
async def compute(db: AsyncSession, as_of: date) -> list[MetricReading]:
    return await compute_hr(db, as_of)


# METRIC-DQ-01 sources (03 §2.6, DEC-209): required business fields + validation failures.
register_dq(
    "hr",
    DqSource(Employee, ("email", "position_id", "contract_type"),
             (lambda m: (m.status == "terminated") & m.termination_date.is_(None),
              lambda m: m.termination_date < m.hire_date)),
    DqSource(HiringPlan, ("requirements",)),
)  # fmt: skip

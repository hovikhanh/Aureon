"""Finance metric provider — METRIC-FIN-02..07 (FIN-01 needs the sales target: the sales
provider computes it from finance's public revenue, avoiding a module cycle) — T-220, DEC-205.

Period = last **closed** month before `as_of` (03 §1.3 "kỳ hiện tại = T9" at 20/10; FIN-02/04/06
use its quarter), except
METRIC-FIN-07 which projects the running month (FR-FIN-08). Change-vs-3-period metrics send
`threshold_input` = the change (points for FIN-02, % for FIN-04); FIN-06 sends the worst
department overrun % (utilization − 100) of the quarter containing the period.
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import month_key, month_range, shift_month
from app.core.metrics import MetricReading, RecordRef, metric_provider
from app.modules.finance import rules
from app.modules.finance.repositories import AnalyticsRepository, InvoiceRepository
from app.modules.finance.rules import quarter_periods
from app.modules.finance.services.analytics_service import FinanceAnalyticsService
from app.modules.finance.services.budget_service import BudgetService, quarter_of


def _avg(values: list[float | None]) -> float | None:
    xs = [v for v in values if v is not None]
    return sum(xs) / len(xs) if xs else None


def _change_pct(cur: float | None, base: float | None) -> float | None:
    if cur is None or base is None or base == 0:
        return None
    return round((cur - base) / abs(base) * 100, 1)


class FinanceMetrics:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AnalyticsRepository(db)
        self.svc = FinanceAnalyticsService(db)

    async def margin(self, months: list[str]) -> float | None:
        rev = sum((await self.repo.monthly_revenue(months)).values())
        cogs = sum((await self.repo.monthly_expense(months, category="cogs")).values())
        return rules.gross_margin_pct(rev, cogs)

    async def dso(self, months: list[str]) -> float | None:
        start, _ = month_range(months[0])
        _, nxt = month_range(months[-1])
        end = date.fromordinal(nxt.toordinal() - 1)
        ar, _ = await InvoiceRepository(self.db).receivables(end)
        rev = sum((await self.repo.monthly_revenue(months)).values())
        return rules.dso_days(ar, rev, (end - start).days + 1)

    async def compute(self, as_of: date) -> list[MetricReading]:
        cur = month_key(as_of)
        m = shift_month(cur, -1)
        out: list[MetricReading] = []

        year, q = quarter_of(m)
        qkey = f"{year}-{q}"
        qm = quarter_periods(year, q)
        prev_q = [[shift_month(k, -3 * i) for k in qm] for i in (1, 2, 3)]
        margin = await self.margin(qm)
        base = _avg([await self.margin(p) for p in prev_q])
        drop = None if margin is None or base is None else round(base - margin, 1)
        out.append(MetricReading("METRIC-FIN-02", margin, qkey, period_type="QUARTER",
                                 threshold_input=drop if drop is not None else 0.0))  # fmt: skip

        _, balance, runway = await self.svc.burn_and_runway(cur)
        if runway is None and balance is not None:  # BR-FIN-03: profitable → ok, no runway
            out.append(MetricReading("METRIC-FIN-03", None, m, status="ok",
                                     status_reason="NOT_APPLICABLE_PROFITABLE"))  # fmt: skip
        else:
            out.append(MetricReading("METRIC-FIN-03", runway, m))

        dso = await self.dso(qm)
        dso_base = _avg([await self.dso(p) for p in prev_q])
        chg = _change_pct(dso, dso_base)
        out.append(MetricReading("METRIC-FIN-04", dso, qkey, period_type="QUARTER",
                                 threshold_input=chg if chg is not None else 0.0))  # fmt: skip

        ar, overdue = await InvoiceRepository(self.db).receivables(as_of)
        out.append(MetricReading("METRIC-FIN-05", rules.pct(overdue, ar), cur))

        statuses = await BudgetService(self.db).statuses(period=f"{year}-{q}", department_id=None)
        worst = max((s.budget_utilization_pct for s in statuses), default=None)
        out.append(MetricReading(
            "METRIC-FIN-06", None if worst is None else round(worst - 100, 1), f"{year}-{q}",
            period_type="QUARTER",
            records=tuple(RecordRef("finance", "budgets", str(s.budget_id)) for s in statuses),
        ))  # fmt: skip
        for s in statuses:
            out.append(MetricReading(
                "METRIC-FIN-06", round(s.budget_utilization_pct - 100, 1), f"{year}-{q}",
                period_type="QUARTER", scope_type="department", scope_id=str(s.department_id),
            ))  # fmt: skip

        out.append(MetricReading("METRIC-FIN-07", await self.svc.burn_variance(as_of), cur))
        return out


@metric_provider("finance")
async def compute(db: AsyncSession, as_of: date) -> list[MetricReading]:
    return await FinanceMetrics(db).compute(as_of)

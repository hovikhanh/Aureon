"""BR-FIN burn / runway, EP-69 what-if, EP-60 dashboard, FR-FIN-08 job (T-105).

`summary` and the trends of the dashboard are computed on read for the requested period (DEC-200).
`metrics[]` carries the 7 METRIC-FIN codes with the metric store's meaning: same formulas (the
`finance` provider, `revenue_vs_target_pct`) on the last closed month of that period, same
thresholds (`platform.metric_rules`, NFR-19), so a code never reads two ways (K1, K7, K8).
YoY growth is `summary.revenue_growth_pct`, not a METRIC.
"""

import calendar
from datetime import UTC, date, datetime
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today, month_key, month_range, shift_month
from app.core.errors import BadRequestError
from app.core.events.outbox import publish_in_tx
from app.core.metrics import MetricReading
from app.core.revenue_target import team_revenue_target
from app.modules.finance import rules
from app.modules.finance.models import Expense, Revenue
from app.modules.finance.repositories import (
    AnalyticsRepository,
    BudgetRepository,
    InvoiceRepository,
)
from app.modules.finance.rules import budget_period_key, quarter_periods
from app.modules.finance.schemas import (
    DashboardPeriod,
    FinanceDashboardOut,
    FinanceMetricOut,
    FinanceSummary,
    RevenueTrendPoint,
    RunwayTrendPoint,
    RunwayWhatIfOut,
    SourceRefOut,
)
from app.modules.finance.services.revenue_query import revenue_vs_target_pct
from app.modules.platform.services.metric_store import metric_rules
from app.modules.platform.services.pillar_snapshot import pillar_snapshot

EVT_BURN_OVER = "finance.burn_over_forecast"
METRIC_UNITS = {
    "METRIC-FIN-01": "PCT", "METRIC-FIN-02": "PCT", "METRIC-FIN-03": "MONTHS",
    "METRIC-FIN-04": "DAYS", "METRIC-FIN-05": "PCT", "METRIC-FIN-06": "PCT",
    "METRIC-FIN-07": "PCT",
}  # fmt: skip
Status = Literal["ok", "warning", "critical", "no_data"]
_RANK = {"no_data": 0, "ok": 1, "warning": 2, "critical": 3}


def last_months(period_key: str, n: int) -> list[str]:
    """n month keys ending at `period_key` (inclusive), ascending."""
    return [shift_month(period_key, -i) for i in range(n - 1, -1, -1)]


def resolve_period(period: str | None, today: date) -> DashboardPeriod:
    """10 §1.5 — current_month (default) / YYYY-MM / current_quarter / YYYY-Qn / ytd."""
    try:
        return _resolve_period(period, today)
    except ValueError as exc:  # e.g. `2026-13`, `2026-Q9` → 400, never 500 (T-510)
        raise BadRequestError(
            "period must be current_month, current_quarter, ytd, YYYY-MM or YYYY-Qn",
            details={"param": "period"},
        ) from exc


def _resolve_period(period: str | None, today: date) -> DashboardPeriod:
    p = period or "current_month"
    if p == "current_month" or (len(p) == 7 and p[4] == "-" and p[5] != "Q"):
        key = month_key(today) if p == "current_month" else p
        start, end = month_range(key)
        return DashboardPeriod(
            key=key, type="current_month" if p == "current_month" else "month",
            start_date=start, end_date=date.fromordinal(end.toordinal() - 1),
        )  # fmt: skip
    if p == "current_quarter" or "-Q" in p:
        year = today.year if p == "current_quarter" else int(p[:4])
        q = (today.month - 1) // 3 + 1 if p == "current_quarter" else int(p[-1])
        first, last = quarter_periods(year, f"Q{q}")[0], quarter_periods(year, f"Q{q}")[-1]
        return DashboardPeriod(
            key=budget_period_key(year, f"Q{q}"),
            type="current_quarter" if p == "current_quarter" else "quarter",
            start_date=month_range(first)[0],
            end_date=date.fromordinal(month_range(last)[1].toordinal() - 1),
        )  # fmt: skip
    if p == "ytd":
        return DashboardPeriod(
            key=str(today.year), type="ytd", start_date=date(today.year, 1, 1), end_date=today
        )
    raise BadRequestError(
        "period must be current_month, current_quarter, ytd, YYYY-MM or YYYY-Qn",
        details={"param": "period"},
    )


def months_in(period: DashboardPeriod) -> list[str]:
    keys, k = [], month_key(period.start_date)
    while k <= month_key(period.end_date):
        keys.append(k)
        k = shift_month(k, 1)
    return keys


class FinanceAnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AnalyticsRepository(db)

    # ---------- BR-FIN-01..03 ----------
    async def burn_and_runway(self, as_of_month: str) -> tuple[int, int | None, float | None]:
        """(net burn over the 3 closed months before `as_of_month`, closing balance, runway)."""
        months = last_months(shift_month(as_of_month, -1), 3)
        burn = await self.monthly_burn(months)
        cash = await self.repo.cash_on_or_before(shift_month(as_of_month, -1))
        balance = cash.closing_balance if cash else None
        return burn, balance, rules.runway_months(balance, burn)

    async def monthly_burn(self, months: list[str]) -> int:
        return rules.net_burn(*await self.burn_basis(months))

    async def burn_basis(self, months: list[str]) -> tuple[list[int], list[int]]:
        """(out, in) per month of BR-FIN-01 on cash "chi − thu" (DEC-202): a month whose opening
        and closing CashPosition both exist uses `opening − closing`; otherwise
        `expense − revenue`. The one burn definition of METRIC-FIN-03 and the what-if (K3)."""
        exp = await self.repo.monthly_expense(months)
        rev = await self.repo.monthly_revenue(months)
        cash = await self.repo.cash_by_period([shift_month(months[0], -1), *months])
        outflow, inflow = [], []
        for m in months:
            prev = cash.get(shift_month(m, -1))
            if prev is not None and m in cash:
                outflow.append(prev)
                inflow.append(cash[m])
            else:
                outflow.append(exp.get(m, 0))
                inflow.append(rev.get(m, 0))
        return outflow, inflow

    # ---------- EP-69 ----------
    async def what_if_runway(
        self, *, as_of: date | None, revenue_change_pct: float, expense_change_pct: float,
        extra_monthly_cost: int,
    ) -> RunwayWhatIfOut:  # fmt: skip
        day = as_of or business_today()
        current = month_key(day)
        months = last_months(shift_month(current, -1), 3)
        exp = await self.repo.monthly_expense(months)
        rev = await self.repo.monthly_revenue(months)
        cash = await self.repo.cash_on_or_before(shift_month(current, -1))
        base = {
            "as_of": day, "revenue_change_pct": revenue_change_pct,
            "expense_change_pct": expense_change_pct, "extra_monthly_cost": extra_monthly_cost,
        }  # fmt: skip
        if cash is None:
            return RunwayWhatIfOut(
                **base, runway_months_no_new_revenue=None, runway_months=None,
                closing_balance=None, avg_expense_3m=None, avg_revenue_3m=None, net_burn=None,
                status_reason="NO_CASH_POSITION", sources=[],
            )  # fmt: skip
        expenses = [exp.get(m, 0) for m in months]
        incomes = [rev.get(m, 0) for m in months]
        avg_exp = round(sum(expenses) / 3)
        avg_rev = round(sum(incomes) / 3)
        adj_exp = [round(e * (1 + expense_change_pct / 100)) + extra_monthly_cost for e in expenses]
        adj_inc = [round(i * (1 + revenue_change_pct / 100)) for i in incomes]
        # the scenario shifts the store's burn by what changes, so 0 % / 0 reads METRIC-FIN-03
        out, inc = await self.burn_basis(months)
        burn = rules.net_burn(
            [o + new - old for o, new, old in zip(out, adj_exp, expenses, strict=True)],
            [i + new - old for i, new, old in zip(inc, adj_inc, incomes, strict=True)],
        )
        sources = [
            SourceRefOut(
                type="record", id=str(cash.id), label=f"Số dư tiền mặt {cash.period_key}",
                period_key=cash.period_key, value=cash.closing_balance,
                lineage_url=f"/finance/cash-positions/{cash.id}",
            ),
            *[
                SourceRefOut(
                    type="tool_result", id=f"finance.expense_total:{m}",
                    label=f"Tổng chi {m}", period_key=m, value=exp.get(m, 0),
                    lineage_url=f"/finance/expenses?period={m}",
                )
                for m in months
            ],
        ]  # fmt: skip
        return RunwayWhatIfOut(
            **base, closing_balance=cash.closing_balance, avg_expense_3m=avg_exp,
            avg_revenue_3m=avg_rev, net_burn=burn,
            runway_months_no_new_revenue=rules.runway_no_new_revenue(cash.closing_balance, adj_exp),
            runway_months=rules.runway_months(cash.closing_balance, burn), sources=sources,
        )  # fmt: skip

    # ---------- EP-60 ----------
    async def dashboard(self, period: str | None) -> FinanceDashboardOut:
        today = business_today()
        per = resolve_period(period, today)
        months = months_in(per)
        last = months[-1]
        rev = await self.repo.monthly_revenue(months)
        exp = await self.repo.monthly_expense(months)
        cogs = await self.repo.monthly_expense(months, category="cogs")
        total_rev, total_exp = sum(rev.values()), sum(exp.values())
        prev_months = [shift_month(m, -12) for m in months]
        prev_rev = sum((await self.repo.monthly_revenue(prev_months)).values())

        # BR-FIN-01 uses closed months only: never include the month in progress
        basis = min(shift_month(last, 1), month_key(today))
        burn, _, runway = await self.burn_and_runway(basis)
        ar_total, overdue = await InvoiceRepository(self.db).receivables(per.end_date)
        days = (per.end_date - per.start_date).days + 1
        margin = rules.gross_margin_pct(total_rev, sum(cogs.values()))
        dso = rules.dso_days(ar_total, total_rev, days)
        util = await self._budget_utilization(per)

        trend_months = last_months(last, 12)
        t_rev = await self.repo.monthly_revenue(trend_months)
        t_exp = await self.repo.monthly_expense(trend_months)
        runway_trend = []
        for m in trend_months:
            _, _, r = await self.burn_and_runway(shift_month(m, 1))
            runway_trend.append(RunwayTrendPoint(period_key=m, runway_months=r))

        now = datetime.now(UTC)
        thresholds = await metric_rules(self.db)

        def metric(r: MetricReading) -> FinanceMetricOut:
            status = cast(Status, thresholds.status(r))
            return FinanceMetricOut(
                metric_code=r.code, value=r.value, unit=METRIC_UNITS[r.code], status=status,
                computed_at=now, freshness="no_data" if status == "no_data" else "fresh",
                lineage_url=f"/dashboard/metrics/{r.code}", period_key=r.period_key,
            )  # fmt: skip

        # Emit the dashboard output unit vocabulary (PCT), same as every other domain dashboard
        # and the platform metric store (`UNIT_OUT` in metric_query.py). The catalog's internal
        # unit is "PERCENT"; the FE `unit.*` i18n namespace only knows the normalized codes, so a
        # raw "PERCENT" here surfaced as `MISSING_MESSAGE: unit.PERCENT`.
        metrics = [metric(r) for r in await self._store_readings(basis, today)]
        snap = await pillar_snapshot(self.db, "F")  # open alerts of pillar F (store)
        no_data = sum(m.status == "no_data" for m in metrics)
        worst = max((m.status for m in metrics), key=lambda s: _RANK[s])
        status: Status = "no_data" if no_data * 2 >= len(metrics) else worst
        return FinanceDashboardOut(
            status=status, period=per,
            summary=FinanceSummary(
                total_revenue=total_rev, total_expense=total_exp,
                net_profit=total_rev - total_exp, gross_margin_pct=margin,
                gross_burn=total_exp, net_burn=burn, runway_months=runway,
                revenue_growth_pct=rules.growth_pct(total_rev, prev_rev),
                budget_utilization_pct=util, overdue_ar=overdue, dso_days=dso,
            ),
            metrics=metrics,
            revenue_trend=[
                RevenueTrendPoint(period_key=m, revenue=t_rev.get(m, 0), expense=t_exp.get(m, 0))
                for m in trend_months
            ],
            runway_trend=runway_trend, open_alerts=snap.open_alerts or 0,
        )  # fmt: skip

    async def _store_readings(self, basis: str, today: date) -> list[MetricReading]:
        """The store's readings of METRIC-FIN-01..07 with `basis` as the running month.

        FIN-01 comes from the sales provider in the store (target), see `revenue_vs_target_pct`;
        FIN-07 projects the month in progress, so it always reads `today`.
        """
        # local import: `metrics` builds on this service
        from app.modules.finance.services.metrics import FinanceMetrics

        closed = shift_month(basis, -1)
        revenue = sum((await self.repo.monthly_revenue([closed])).values())
        target = await team_revenue_target(self.db, closed)
        as_of = today if basis == month_key(today) else month_range(basis)[0]
        rows = await FinanceMetrics(self.db).compute(as_of)
        by_code = {r.code: r for r in rows if r.scope_type == "company"}
        by_code["METRIC-FIN-01"] = MetricReading(
            "METRIC-FIN-01", revenue_vs_target_pct(revenue, target), closed
        )
        by_code["METRIC-FIN-07"] = MetricReading(
            "METRIC-FIN-07", await self.burn_variance(today), month_key(today)
        )
        return [by_code[code] for code in sorted(METRIC_UNITS)]

    async def _budget_utilization(self, per: DashboardPeriod) -> float | None:
        """Company-wide utilization of the quarter budgets containing the period end."""
        q = f"Q{(per.end_date.month - 1) // 3 + 1}"
        budgets = BudgetRepository(self.db)
        items, _ = await budgets.list_page(
            limit=100, offset=0, sort_by="created_at", order="asc",
            filters={"fiscal_year": per.end_date.year, "quarter": q},
        )  # fmt: skip
        if not items:
            return None
        periods = quarter_periods(per.end_date.year, q)
        spent = sum([await budgets.spent(b.department_id, periods) for b in items])
        return rules.utilization_pct(spent, sum(b.allocated_amount for b in items))

    # ---------- METRIC-FIN-07 / FR-FIN-08 ----------
    async def burn_variance(self, today: date) -> float | None:
        key = month_key(today)
        line = await self.repo.forecast_line("base", key)
        if line is None:
            return None
        start, _ = month_range(key)
        end = date.fromordinal(today.toordinal() + 1)
        projected = rules.projected_month_burn(
            await self.repo.sum_between(Expense, start, end),
            await self.repo.sum_between(Revenue, start, end),
            calendar.monthrange(today.year, today.month)[1],
            today.day,
        )
        forecast = line.projected_expenses - line.projected_revenue
        return rules.burn_variance_pct(projected, forecast)

    async def check_burn_over_forecast(self, today: date | None = None) -> bool:
        """Daily job: variance > THR_FIN_07_WARN → `burn_over_forecast`, ≤ 1/day (FR-FIN-08)."""
        day = today or business_today()
        variance = await self.burn_variance(day)
        key = month_key(day)
        reading = MetricReading("METRIC-FIN-07", variance, key)
        severity = (await metric_rules(self.db)).status(reading)
        if severity not in ("warning", "critical"):
            return False
        if await self.repo.burn_event_published(day):
            return False
        line = await self.repo.forecast_line("base", key)
        if line is None:  # forecast removed between the two reads
            return False
        start, _ = month_range(key)
        end = date.fromordinal(day.toordinal() + 1)
        actual = rules.projected_month_burn(
            await self.repo.sum_between(Expense, start, end),
            await self.repo.sum_between(Revenue, start, end),
            calendar.monthrange(day.year, day.month)[1], day.day,
        )  # fmt: skip
        await publish_in_tx(
            self.db, event_type=EVT_BURN_OVER, producer="finance", aggregate_schema="finance",
            aggregate_table="forecasts", aggregate_id=line.forecast_id,
            payload={
                "period_key": key, "as_of": day.isoformat(), "actual_burn": actual,
                "forecast_burn": line.projected_expenses - line.projected_revenue,
                "variance_pct": variance,
                "severity": severity,
                "currency": "VND",
            },
        )  # fmt: skip
        return True

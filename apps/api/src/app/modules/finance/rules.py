"""Pure finance business rules BR-FIN-01..06 (03 §6) — no DB, unit-tested with 08 numbers.

Money in BIGINT smallest unit; ratios via `Decimal` then rounded (CLAUDE.md §6.5).
"""

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

BudgetStatus = Literal["ok", "warning", "critical"]

# ALERT-FIN-06 (03 §3): warning > 100 %, critical > 110 %.
BUDGET_WARN_PCT = Decimal(100)
BUDGET_CRIT_PCT = Decimal(110)


def _round(value: Decimal, places: int) -> float:
    q = Decimal(1).scaleb(-places)
    return float(value.quantize(q, rounding=ROUND_HALF_UP))


def quarter_periods(fiscal_year: int, quarter: str | None) -> list[str]:
    """`YYYY-MM` keys covered by a budget (`quarter` None = whole year)."""
    if quarter is None:
        months = range(1, 13)
    else:
        q = int(quarter[1])
        months = range(3 * q - 2, 3 * q + 1)
    return [f"{fiscal_year:04d}-{m:02d}" for m in months]


def budget_period_key(fiscal_year: int, quarter: str | None) -> str:
    return f"{fiscal_year}-{quarter}" if quarter else f"{fiscal_year}"


def utilization_pct(spent: int, allocated: int) -> float:
    """BR-FIN-05: spent ÷ allocated × 100 (2 decimals)."""
    if allocated <= 0:
        raise ValueError("allocated must be > 0")
    return _round(Decimal(spent) * 100 / Decimal(allocated), 2)


def budget_status(pct: float) -> BudgetStatus:
    p = Decimal(str(pct))
    if p > BUDGET_CRIT_PCT:
        return "critical"
    if p > BUDGET_WARN_PCT:
        return "warning"
    return "ok"


# ---------- BR-FIN-01..04, 06, METRIC-FIN-02/04/07 ----------
def net_burn(expenses: Sequence[int], incomes: Sequence[int]) -> int:
    """BR-FIN-01: mean of positive (expense − income) over the given months; none → 0."""
    positive = [e - i for e, i in zip(expenses, incomes, strict=True) if e - i > 0]
    if not positive:
        return 0
    return int((Decimal(sum(positive)) / len(positive)).quantize(Decimal(1), ROUND_HALF_UP))


def runway_months(closing_balance: int | None, burn: int) -> float | None:
    """BR-FIN-02/03: balance ÷ burn (1 decimal); burn ≤ 0 or no balance → None."""
    if closing_balance is None or burn <= 0:
        return None
    return _round(Decimal(closing_balance) / Decimal(burn), 1)


def runway_no_new_revenue(closing_balance: int | None, expenses: Sequence[int]) -> float | None:
    """BR-FIN-06: balance ÷ AVG(total expense of the last months)."""
    if closing_balance is None or not expenses or sum(expenses) <= 0:
        return None
    return _round(Decimal(closing_balance) * len(expenses) / Decimal(sum(expenses)), 1)


def pct(numerator: int, denominator: int, places: int = 1) -> float | None:
    if denominator == 0:
        return None
    return _round(Decimal(numerator) * 100 / Decimal(denominator), places)


def gross_margin_pct(revenue: int, cogs: int) -> float | None:
    """METRIC-FIN-02: (revenue − COGS) ÷ revenue × 100."""
    return pct(revenue - cogs, revenue)


def growth_pct(current: int, previous: int) -> float | None:
    return pct(current - previous, previous)


def dso_days(receivables: int, revenue: int, days_in_period: int) -> float | None:
    """METRIC-FIN-04: AR ÷ revenue × days."""
    if revenue <= 0:
        return None
    return _round(Decimal(receivables) * days_in_period / Decimal(revenue), 1)


def projected_month_burn(
    expense_mtd: int, income_mtd: int, days_in_month: int, days_elapsed: int
) -> int:
    """METRIC-FIN-07: (expense MTD − income MTD) × days in month ÷ elapsed days."""
    if days_elapsed <= 0:
        return 0
    value = Decimal(expense_mtd - income_mtd) * days_in_month / days_elapsed
    return int(value.quantize(Decimal(1), ROUND_HALF_UP))


def burn_variance_pct(projected: int, forecast: int) -> float | None:
    """METRIC-FIN-07: (projected − forecast) ÷ |forecast| × 100."""
    if forecast == 0:
        return None
    return _round(Decimal(projected - forecast) * 100 / abs(Decimal(forecast)), 1)

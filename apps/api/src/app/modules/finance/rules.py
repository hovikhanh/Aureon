"""Pure finance business rules BR-FIN-01..06 (03 §6) — no DB, unit-tested with 08 numbers.

Money in BIGINT smallest unit; ratios via `Decimal` then rounded (CLAUDE.md §6.5).
"""

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

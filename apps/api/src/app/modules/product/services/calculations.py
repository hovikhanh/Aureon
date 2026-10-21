"""Pure product rules (no I/O) — BR-PRD-01, METRIC-PRD-01..05 / CUS-05 math (03 §2.4, §5.4).

Kept free of DB access so they are unit-tested exactly and reused by EP-90 and the metric
provider. Inputs are plain numbers; `None` means "no data".
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.core.clock import shift_month

# 03 §5.4 BR-PRD-01 defaults (CHURN_ANOMALY_REL_PCT / CHURN_ANOMALY_FLOOR_PCT — DEC-213).
CHURN_ANOMALY_REL_PCT = 50.0
CHURN_ANOMALY_FLOOR_PCT = 2.0
BASELINE_PERIODS = 3


def round1(value: float | Decimal | None) -> float | None:
    if value is None:
        return None
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def previous_periods(period_key: str, n: int = BASELINE_PERIODS) -> list[str]:
    """The `n` months right before `period_key` ("3 kỳ gần nhất", 03 §1.3), ascending."""
    return [shift_month(period_key, -i) for i in range(n, 0, -1)]


def baseline(values: Sequence[float | None]) -> float | None:
    """AVG of the 3 previous periods; `None` unless all 3 exist (no partial baseline)."""
    if len(values) < BASELINE_PERIODS or any(v is None for v in values):
        return None
    return sum(v for v in values if v is not None) / len(values)


def is_churn_anomaly(
    current: float,
    base: float | None,
    rel_pct: float = CHURN_ANOMALY_REL_PCT,
    floor_pct: float = CHURN_ANOMALY_FLOOR_PCT,
) -> bool:
    """BR-PRD-01: `current > base × (1 + rel/100)` **and** `current ≥ floor`."""
    if base is None:
        return False
    return current > base * (1 + rel_pct / 100) and current >= floor_pct


def relative_change_pct(current: float | None, base: float | None) -> float | None:
    """`(current − base) / base × 100`; `None` when either side missing or base = 0."""
    if current is None or base is None or base == 0:
        return None
    return round1((current - base) / base * 100)


@dataclass(frozen=True)
class Snapshot:
    """One product's current metric row for a period (plain numbers)."""

    mau: int
    adoption_pct: float | None
    churn_rate_pct: float
    retention_30d_pct: float | None
    nps: float | None
    arpu: int | None


def weighted(rows: Iterable[Snapshot], attr: str) -> float | None:
    """MAU-weighted average of `attr` over rows having it (03 METRIC-PRD-01/03, CUS-05)."""
    num, den = 0.0, 0
    for r in rows:
        value = getattr(r, attr)
        if value is not None and r.mau > 0:
            num += float(value) * r.mau
            den += r.mau
    return round1(num / den) if den else None


def total_mau(rows: Sequence[Snapshot]) -> int | None:
    return sum(r.mau for r in rows) if rows else None


def worst_churn(rows: Sequence[Snapshot]) -> float | None:
    """METRIC-PRD-02 pillar value = worst (highest) product churn."""
    return round1(max(r.churn_rate_pct for r in rows)) if rows else None


def pct(num: int, den: int) -> float | None:
    return round1(Decimal(num) / Decimal(den) * 100) if den else None


def pillar_status(metric_statuses: Iterable[str]) -> str:
    """Worst metric wins; ≥ 50% `no_data` (or no metric at all) → `no_data` (03 §4)."""
    items = list(metric_statuses)
    if not items or items.count("no_data") * 2 >= len(items):
        return "no_data"
    for level in ("critical", "warning"):
        if level in items:
            return level
    return "ok"

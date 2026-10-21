"""Pure product rules (no I/O) — BR-PRD-01, METRIC-PRD-01..05 / CUS-05 math (03 §2.4, §5.4).

Kept free of DB access so they are unit-tested exactly and reused by EP-90 and the metric
provider. Inputs are plain numbers; `None` means "no data".
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.core.clock import month_key, month_range, shift_month

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


PillarStatus = Literal["ok", "warning", "critical", "no_data"]


def pillar_status(metric_statuses: Iterable[str]) -> PillarStatus:
    """Worst metric wins; ≥ 50% `no_data` (or no metric at all) → `no_data` (03 §4)."""
    items = list(metric_statuses)
    if not items or items.count("no_data") * 2 >= len(items):
        return "no_data"
    if "critical" in items:
        return "critical"
    return "warning" if "warning" in items else "ok"


# ---------- periods (10 §1.5) ----------
_MONTH = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
_QUARTER = re.compile(r"^(\d{4})-Q([1-4])$")


@dataclass(frozen=True)
class Period:
    key: str
    type: str
    start: date
    end: date  # inclusive

    @property
    def last_month(self) -> str:
        return month_key(self.end)


def _month_end(y: int, m: int) -> date:
    return month_range(f"{y:04d}-{m:02d}")[1] - timedelta(days=1)


def quarter_key(d: date) -> str:
    return f"{d.year:04d}-Q{(d.month - 1) // 3 + 1}"


def resolve_period(value: str | None, today: date) -> Period:
    """`current_month` (default) / `current_quarter` / `ytd` / `YYYY-MM` / `YYYY-Qn`.

    Anything else (incl. `custom`, EP-60 only) → `ValueError` (route maps to `400`).
    """
    v = value or "current_month"
    y, m = today.year, today.month
    if v == "current_month":
        v = f"{y:04d}-{m:02d}"
    elif v == "current_quarter":
        v = quarter_key(today)
    elif v == "ytd":
        return Period(f"{y:04d}", "ytd", date(y, 1, 1), _month_end(y, m))
    if mm := _MONTH.match(v):
        yy, mo = int(mm.group(1)), int(mm.group(2))
        return Period(v, "month", date(yy, mo, 1), _month_end(yy, mo))
    if qm := _QUARTER.match(v):
        yy, q = int(qm.group(1)), int(qm.group(2))
        return Period(v, "quarter", date(yy, 3 * q - 2, 1), _month_end(yy, 3 * q))
    raise ValueError("period must be current_month|current_quarter|ytd|YYYY-MM|YYYY-Qn")


def trend_keys(last: str, count: int = 12) -> list[str]:
    return [shift_month(last, -i) for i in range(count - 1, -1, -1)]


def roadmap_late(status: str, planned: date | None, completed: date | None, today: date) -> bool:
    """METRIC-PRD-04 "trễ": `target_date < today` and not done, or done after `target_date`."""
    if planned is None:
        return False
    if status == "done":
        return completed is not None and completed > planned
    return planned < today


def roadmap_on_time_pct(
    items: Sequence[tuple[str, date | None, date | None]], today: date
) -> float | None:
    """% of the quarter's items not late; `dropped` items are excluded (DEC-214)."""
    live = [i for i in items if i[0] != "dropped"]
    late = sum(1 for s, p, c in live if roadmap_late(s, p, c, today))
    return pct(len(live) - late, len(live))

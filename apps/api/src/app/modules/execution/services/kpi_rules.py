"""Pure OKR / KPI maths (05 ENT-KPIMeasurement, ENT-KPITarget, DEC-147) — TC-EXE-004.

- `achievement_pct` by direction: HIGHER = actual/target; LOWER = target/actual;
  WITHIN_RANGE = 100 inside `[minimum, target]`, else distance-scaled like HIGHER (below) /
  LOWER (above); BINARY = 100 when actual ≥ target else 0. Floor 0, cap `score_cap_pct` (150).
  Division by zero: numerator 0 → 100 (on target), otherwise the cap.
- Band = highest band whose lower bound (`band_thresholds`, % achievement) ≤ achievement.
- M1.4 (05 §2.6): `gap_value` (≥ 0 while the target is not met), on-time KPI period (grace days
  after the period end, local calendar day), effective target version `[valid_from, valid_to)`.
"""

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

DEFAULT_BANDS: dict[str, float] = {
    "CRITICAL": 0, "BELOW": 70, "NEAR": 90, "MEETS": 100, "EXCEEDS": 110,
}  # fmt: skip
DEFAULT_CAP = Decimal(150)
Q4 = Decimal("0.0001")
LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")  # business calendar (05 §2.6)
LOW_BANDS = frozenset({"BELOW", "CRITICAL"})  # `execution.kpi_below_threshold`
BAND_RANK = {"CRITICAL": 0, "BELOW": 1, "NEAR": 2, "MEETS": 3, "EXCEEDS": 4}


def entered_low_band(new: str, previous: str | None) -> bool:
    """Band moved into BELOW / CRITICAL from a better band, or first evaluation (10 §9.2)."""
    if new not in LOW_BANDS:
        return False
    return previous is None or BAND_RANK[new] < BAND_RANK[previous]


def _ratio(num: Decimal, den: Decimal, cap: Decimal) -> Decimal:
    if den == 0:
        return Decimal(100) if num == 0 else cap
    return num / den * 100


def achievement_pct(
    direction: str, actual: Decimal, target: Decimal, *, minimum: Decimal | None = None,
    cap: Decimal = DEFAULT_CAP,
) -> Decimal:  # fmt: skip
    if direction == "LOWER_IS_BETTER":
        raw = _ratio(target, actual, cap)
    elif direction == "BINARY":
        raw = Decimal(100) if actual >= target else Decimal(0)
    elif direction == "WITHIN_RANGE":
        low = minimum if minimum is not None else target
        if actual < low:
            raw = _ratio(actual, low, cap)
        elif actual > target:
            raw = _ratio(target, actual, cap)
        else:
            raw = Decimal(100)
    else:  # HIGHER_IS_BETTER
        raw = _ratio(actual, target, cap)
    return min(max(raw, Decimal(0)), cap).quantize(Q4, rounding=ROUND_HALF_UP)


def band(achievement: Decimal, thresholds: dict[str, Any] | None = None) -> str:
    bounds = sorted((Decimal(str(v)), k) for k, v in (thresholds or DEFAULT_BANDS).items())
    chosen = bounds[0][1]
    for low, name in bounds:
        if achievement >= low:
            chosen = name
    return chosen


def kr_progress_pct(baseline: Decimal, target: Decimal, current: Decimal | None) -> Decimal:
    """KR progress 0..100 from baseline → target (works for decreasing targets)."""
    if current is None:
        return Decimal(0)
    if target == baseline:
        return Decimal(100) if current == target else Decimal(0)
    raw = (current - baseline) / (target - baseline) * 100
    return min(max(raw, Decimal(0)), Decimal(100)).quantize(Q4, rounding=ROUND_HALF_UP)


def weighted_avg(pairs: list[tuple[Decimal, Decimal]]) -> Decimal:
    """Σ(w·v)/Σw over `(value, weight)`; Σw = 0 → plain mean; empty → 0."""
    if not pairs:
        return Decimal(0)
    total_w = sum((w for _, w in pairs), Decimal(0))
    if total_w == 0:
        avg = sum((v for v, _ in pairs), Decimal(0)) / len(pairs)
    else:
        avg = sum((v * w for v, w in pairs), Decimal(0)) / total_w
    return avg.quantize(Q4, rounding=ROUND_HALF_UP)


def period_key_for(period_type: str, day: date) -> str:
    if period_type == "QUARTER":
        return f"{day.year:04d}-Q{(day.month - 1) // 3 + 1}"
    if period_type == "YEAR":
        return f"{day.year:04d}"
    return f"{day.year:04d}-{day.month:02d}"  # MONTH, ROLLING_12M (month end key)


def period_bounds(period_key: str) -> tuple[date, date]:
    """`[start, end)` of `YYYY-MM` / `YYYY-Qn` / `YYYY`; `ValueError` otherwise."""
    year = int(period_key[:4])
    rest = period_key[4:]
    if rest == "":
        return date(year, 1, 1), date(year + 1, 1, 1)
    if rest.startswith("-Q") and len(rest) == 3 and rest[2] in "1234":
        q = int(rest[2])
        start = date(year, 3 * q - 2, 1)
        return start, date(year + 1, 1, 1) if q == 4 else date(year, 3 * q + 1, 1)
    if len(rest) == 3 and rest[0] == "-" and rest[1:].isdigit() and 1 <= int(rest[1:]) <= 12:
        m = int(rest[1:])
        return date(year, m, 1), date(year + 1, 1, 1) if m == 12 else date(year, m + 1, 1)
    raise ValueError(f"invalid period_key {period_key!r}")


def gap_value(
    direction: str, actual: Decimal, target: Decimal, minimum: Decimal | None = None
) -> Decimal:
    """Distance to the target by `direction`: positive = short of it, ≤ 0 = met (05 §2.6)."""
    if direction == "LOWER_IS_BETTER":
        return actual - target
    if direction == "WITHIN_RANGE":
        low = minimum if minimum is not None else target
        if actual < low:
            return low - actual
        return actual - target if actual > target else Decimal(0)
    return target - actual  # HIGHER_IS_BETTER, BINARY


def local_day(at: datetime) -> date:
    return at.astimezone(LOCAL_TZ).date()


def on_time(measured_at: datetime, period_key: str, grace_days: int) -> bool:
    """On-time KPI period: measured before `end(P) + grace` (local day, 05 §2.6)."""
    _, end = period_bounds(period_key)
    return local_day(measured_at) < end + timedelta(days=grace_days)


def in_force(valid_from: date, valid_to: date | None, day: date) -> bool:
    return valid_from <= day and (valid_to is None or day < valid_to)


def last_ended_period(period_type: str, day: date) -> str:
    """Most recently ended period of `period_type` at `day` (due KPI-period, 05 §2.6)."""
    start, _ = period_bounds(period_key_for(period_type, day))
    return period_key_for(period_type, start - timedelta(days=1))


def periods_overlap(a: str, b: str) -> bool:
    """`[start, end)` of two period keys overlap (a year objective spans its quarters)."""
    a0, a1 = period_bounds(a)
    b0, b1 = period_bounds(b)
    return a0 < b1 and b0 < a1

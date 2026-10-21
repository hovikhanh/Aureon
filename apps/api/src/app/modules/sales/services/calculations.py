"""Pure Sales calculations — BR-SAL-01..04, METRIC-CUS-01/02/06, periods (03 §2.3, §5.2).

No I/O: the service feeds plain numbers / dates in, so every rule is unit-tested in isolation.
Ratios use `Decimal` (CLAUDE.md §6.5: never float for money) and are rounded only at the end.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

OPEN_STAGES: tuple[str, ...] = ("lead", "qualified", "proposal", "negotiation")
CLOSED_STAGES: tuple[str, ...] = ("closed_won", "closed_lost")
STAGE_ORDER: tuple[str, ...] = OPEN_STAGES + CLOSED_STAGES


def _round(value: Decimal, places: int) -> float:
    q = Decimal(1).scaleb(-places)
    return float(value.quantize(q, rounding=ROUND_HALF_UP))


# ---------- BR-SAL-01 / stage order (03 §5.2) ----------
def closing_probability(to_stage: str) -> Decimal | None:
    """BR-SAL-01: `closed_won` → 100, `closed_lost` → 0; open stages keep the user's value."""
    return {"closed_won": Decimal(100), "closed_lost": Decimal(0)}.get(to_stage)


def transition_error(from_stage: str, to_stage: str) -> str | None:
    """`None` if allowed, else the reason (03 §5.2, DEC-192).

    Closed deals are final (`closed`). Open deals move forward only — to any later open stage
    or straight to `closed_won` / `closed_lost`; same stage or backwards → `not_forward`.
    """
    if from_stage in CLOSED_STAGES:
        return "closed"
    if to_stage in CLOSED_STAGES:
        return None
    if STAGE_ORDER.index(to_stage) <= STAGE_ORDER.index(from_stage):
        return "not_forward"
    return None


# ---------- BR-SAL-02 ----------
def weighted_value(deal_value: int, probability_pct: Decimal | float | int) -> int:
    """BR-SAL-02 — same formula as the generated column `(deal_value * p / 100)::bigint`."""
    raw = Decimal(deal_value) * Decimal(str(probability_pct)) / Decimal(100)
    return int(raw.quantize(Decimal(1), rounding=ROUND_HALF_UP))


# ---------- BR-SAL-03 / METRIC-CUS-02 ----------
def win_rate_pct(won: int, lost: int) -> float | None:
    """`won / (won + lost) × 100`, 1 decimal; no closed deal → `None` (no_data)."""
    closed = won + lost
    if closed <= 0:
        return None
    return _round(Decimal(won) * 100 / Decimal(closed), 1)


# ---------- BR-SAL-04 / METRIC-CUS-01 ----------
def coverage_ratio(open_value: int, target_amount: int | None) -> float | None:
    """Open pipeline value (closing in the quarter) ÷ quarter team target, 1 decimal."""
    if not target_amount or target_amount <= 0:
        return None
    return _round(Decimal(open_value) / Decimal(target_amount), 1)


def attainment_pct(closed_value: int, quota: int | None) -> float | None:
    """`closed / quota × 100` (FR-SAL-05), 1 decimal; no quota → `None`."""
    if not quota or quota <= 0:
        return None
    return _round(Decimal(closed_value) * 100 / Decimal(quota), 1)


# ---------- METRIC-CUS-06 / averages ----------
def avg_days(durations: Iterable[timedelta]) -> float | None:
    """Average length in days (1 decimal) — `AVG(closed_at − created_at)` for won deals."""
    items = list(durations)
    if not items:
        return None
    total = sum((d.total_seconds() for d in items), 0.0)
    return _round(Decimal(str(total)) / Decimal(86400 * len(items)), 1)


def avg_amount(values: Iterable[int]) -> int | None:
    items = list(values)
    if not items:
        return None
    return int((Decimal(sum(items)) / Decimal(len(items))).quantize(Decimal(1), ROUND_HALF_UP))


def stage_durations(
    history: Iterable[tuple[str, datetime]], now: datetime
) -> list[tuple[str, timedelta]]:
    """`[(stage, time spent)]` for one deal's ordered `(stage, entered_at)` rows.

    A stage ends when the next row starts; the current open stage runs until `now`; a closed
    stage is terminal and has no duration.
    """
    rows = list(history)
    out: list[tuple[str, timedelta]] = []
    for i, (stage, entered) in enumerate(rows):
        if i + 1 < len(rows):
            out.append((stage, rows[i + 1][1] - entered))
        elif stage not in CLOSED_STAGES:
            out.append((stage, now - entered))
    return out


# ---------- pillar status (03 §4) ----------
def pillar_status(metric_statuses: Iterable[str]) -> str:
    """Worst metric wins; ≥ 50% `no_data` (or no metric at all) → `no_data` (03 §4)."""
    items = list(metric_statuses)
    if not items or items.count("no_data") * 2 >= len(items):
        return "no_data"
    for level in ("critical", "warning"):
        if level in items:
            return level
    return "ok"


# ---------- periods (10 §1.5) ----------
_MONTH = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
_QUARTER = re.compile(r"^(\d{4})-Q([1-4])$")
_YEAR = re.compile(r"^(\d{4})$")


@dataclass(frozen=True)
class Period:
    key: str
    type: str  # month | quarter | year | ytd (10 §5 `period.type` uses the request keyword)
    start: date
    end: date  # inclusive


def _month_end(y: int, m: int) -> date:
    nxt = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    return nxt - timedelta(days=1)


def month_period(y: int, m: int) -> Period:
    return Period(f"{y:04d}-{m:02d}", "month", date(y, m, 1), _month_end(y, m))


def quarter_period(y: int, q: int) -> Period:
    return Period(f"{y:04d}-Q{q}", "quarter", date(y, 3 * q - 2, 1), _month_end(y, 3 * q))


def quarter_of(d: date) -> Period:
    return quarter_period(d.year, (d.month - 1) // 3 + 1)


def resolve_period(value: str | None, today: date, default: str = "current_month") -> Period:
    """`current_month` / `current_quarter` / `ytd` / `YYYY-MM` / `YYYY-Qn` / `YYYY`.

    Raises `ValueError` for anything else (`custom` is EP-60 only — 10 §5).
    """
    v = value or default
    if v == "current_month":
        return month_period(today.year, today.month)
    if v == "current_quarter":
        return quarter_of(today)
    if v == "ytd":
        return Period(f"{today.year:04d}", "ytd", date(today.year, 1, 1), today)
    if m := _MONTH.match(v):
        return month_period(int(m.group(1)), int(m.group(2)))
    if m := _QUARTER.match(v):
        return quarter_period(int(m.group(1)), int(m.group(2)))
    if m := _YEAR.match(v):
        y = int(m.group(1))
        return Period(v, "year", date(y, 1, 1), date(y, 12, 31))
    raise ValueError("period must be current_month|current_quarter|ytd|YYYY-MM|YYYY-Qn|YYYY")


def target_period_key_ok(period_type: str, period_key: str) -> bool:
    """EP-77: `month` → `YYYY-MM`, `quarter` → `YYYY-Qn`, `year` → `YYYY`."""
    pattern = {"month": _MONTH, "quarter": _QUARTER, "year": _YEAR}[period_type]
    return pattern.match(period_key) is not None


def last_months(end: date, n: int) -> list[Period]:
    """`n` month periods ending with the month of `end`, ascending (for `*_trend`)."""
    y, m = end.year, end.month
    out: list[Period] = []
    for _ in range(n):
        out.append(month_period(y, m))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return out[::-1]

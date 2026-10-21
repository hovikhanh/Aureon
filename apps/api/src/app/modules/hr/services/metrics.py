"""Pure HR metric functions (no I/O) — BR-HR-01, METRIC-HR-02, EP-80 period resolution.

Kept free of DB access so they are unit-tested exactly and reused by the metric store (T-220).
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

PeriodType = Literal["current_month", "current_quarter", "ytd", "month", "quarter"]
Status = Literal["ok", "warning", "critical"]
MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
QUARTER_RE = re.compile(r"^(\d{4})-Q([1-4])$")

# 03 §2 METRIC-HR-02 / METRIC-HR-04 default bands (DEC-143); metric store (T-220) owns config.
TURNOVER_WARNING_PCT = 15.0
TURNOVER_CRITICAL_PCT = 20.0
DELAY_CRITICAL_DAYS = 45


def _round1(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def annualized_turnover_pct(
    terminations: int, headcount_start: int, headcount_end: int, months: int
) -> float | None:
    """BR-HR-01: `(leavers ÷ avg headcount) × (12 ÷ months) × 100`, avg = (start + end) / 2.

    `None` when the average headcount is 0 (undefined rate) or `months` < 1. 1 decimal.
    """
    if months < 1 or terminations < 0:
        return None
    avg = Decimal(headcount_start + headcount_end) / 2
    if avg <= 0:
        return None
    return _round1(Decimal(terminations) / avg * Decimal(12) / Decimal(months) * 100)


def tenure_months(hire: date, as_of: date) -> int:
    """Whole months from `hire` to `as_of` (0 if not yet hired)."""
    months = (as_of.year - hire.year) * 12 + as_of.month - hire.month
    if as_of.day < hire.day:
        months -= 1
    return max(months, 0)


def average_tenure_months(hires: list[date], as_of: date) -> float | None:
    if not hires:
        return None
    total = sum(tenure_months(h, as_of) for h in hires)
    return _round1(Decimal(total) / len(hires))


def month_end(year: int, month: int) -> date:
    nxt = date(year + month // 12, month % 12 + 1, 1)
    return nxt - timedelta(days=1)


def add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


@dataclass(frozen=True)
class Period:
    key: str
    type: PeriodType
    start: date
    end: date

    @property
    def months(self) -> int:
        return (self.end.year - self.start.year) * 12 + self.end.month - self.start.month + 1


def resolve_period(spec: str | None, today: date) -> Period:
    """10 §1.5 `period`: `current_month` (default) / `current_quarter` / `ytd` / `YYYY-MM` /
    `YYYY-Qn`. `custom` is EP-60 only → `ValueError` (route maps to `400`)."""
    spec = spec or "current_month"
    y, m = today.year, today.month
    if spec == "current_month":
        return Period(f"{y:04d}-{m:02d}", "current_month", date(y, m, 1), month_end(y, m))
    if spec == "current_quarter":
        q = (m - 1) // 3 + 1
        return Period(f"{y:04d}-Q{q}", "current_quarter", date(y, 3 * q - 2, 1),
                      month_end(y, 3 * q))  # fmt: skip
    if spec == "ytd":
        return Period(f"{y:04d}-YTD", "ytd", date(y, 1, 1), month_end(y, m))
    if mm := MONTH_RE.match(spec):
        yy, mo = int(mm.group(1)), int(mm.group(2))
        return Period(spec, "month", date(yy, mo, 1), month_end(yy, mo))
    if qm := QUARTER_RE.match(spec):
        yy, q = int(qm.group(1)), int(qm.group(2))
        return Period(spec, "quarter", date(yy, 3 * q - 2, 1), month_end(yy, 3 * q))
    raise ValueError("period must be current_month|current_quarter|ytd|YYYY-MM|YYYY-Qn")


def trend_months(end: date, count: int = 12) -> list[tuple[str, date, date]]:
    """`count` calendar months ending with `end`'s month, ascending: (key, start, end)."""
    out = []
    for back in range(count - 1, -1, -1):
        y, m = add_months(end.year, end.month, -back)
        out.append((f"{y:04d}-{m:02d}", date(y, m, 1), month_end(y, m)))
    return out


def turnover_status(pct: float | None) -> Status | None:
    if pct is None:
        return None
    if pct >= TURNOVER_CRITICAL_PCT:
        return "critical"
    return "warning" if pct >= TURNOVER_WARNING_PCT else "ok"


def delay_status(days_late: list[int]) -> Status:
    """METRIC-HR-04: any plan late > 45 days → critical; any late → warning."""
    if any(d > DELAY_CRITICAL_DAYS for d in days_late):
        return "critical"
    return "warning" if days_late else "ok"


def worst(*statuses: Status | None) -> Status | Literal["no_data"]:
    present = [s for s in statuses if s is not None]
    if not present:
        return "no_data"
    order = {"ok": 0, "warning": 1, "critical": 2}
    return max(present, key=lambda s: order[s])


@dataclass(frozen=True)
class Tenure:
    """Minimal employee row for headcount maths (no PII)."""

    hire_date: date
    termination_date: date | None


def on_payroll(rows: list[Tenure], day: date) -> list[Tenure]:
    return [
        r for r in rows
        if r.hire_date <= day and (r.termination_date is None or r.termination_date > day)
    ]  # fmt: skip


def leavers(rows: list[Tenure], start: date, end: date) -> int:
    return sum(1 for r in rows if r.termination_date and start <= r.termination_date <= end)


def hires(rows: list[Tenure], start: date, end: date) -> int:
    return sum(1 for r in rows if start <= r.hire_date <= end)


def period_turnover_pct(rows: list[Tenure], start: date, end: date, months: int) -> float | None:
    """BR-HR-01 over [start, end]: headcount at the day before `start` and at `end`."""
    return annualized_turnover_pct(
        leavers(rows, start, end),
        len(on_payroll(rows, start - timedelta(days=1))),
        len(on_payroll(rows, end)),
        months,
    )

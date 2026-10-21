"""Dashboard period resolution — 10 §1.5 `period` (shared by domain dashboards, T-222).

`current_month` (default) / `current_quarter` / `ytd` / `YYYY-MM` / `YYYY-Qn`; `custom` is EP-60
only (finance keeps its own resolver). Moved from `hr.services.metrics` so execution (EP-49)
can use it without an hr ↔ execution import cycle.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

PeriodType = Literal["current_month", "current_quarter", "ytd", "month", "quarter"]
MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
QUARTER_RE = re.compile(r"^(\d{4})-Q([1-4])$")


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

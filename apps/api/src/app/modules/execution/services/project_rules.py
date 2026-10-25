"""Pure project/milestone rules shared by EP-TASK-09..17 and METRIC-OPS-02 (R-DEC-49, 05 §2.5).

One formula, two callers: `ProjectOut.progress_pct/planned_pct/late` (computed at read) and the
METRIC-OPS-02 provider (`metrics.ops02`) — so the list badge and the KPI never disagree.
- progress = share of `done` among the project's non-cancelled tasks (DEC-226; no tasks → 0).
- planned = linear `start_date → planned_end_date` at `as_of`, clamped 0..100.
- late = planned − progress > `LATE_GAP_PCT` (10 points, 03 §4 threshold unchanged).
"""

from collections.abc import Iterable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

LATE_GAP_PCT = Decimal(10)  # METRIC-OPS-02
CLOSED_PROJECT = frozenset({"done", "cancelled"})


def linear_progress(start: date, end: date, as_of: date) -> Decimal:
    """Planned % complete at `as_of`, linear over `[start, end]`, clamped to 0..100."""
    if as_of >= end:
        return Decimal(100)
    if as_of <= start:
        return Decimal(0)
    return Decimal((as_of - start).days * 100) / Decimal((end - start).days)


def progress(statuses: Iterable[str]) -> Decimal:
    """Share of `done` among non-cancelled task statuses, 0..100 (4 decimals)."""
    counted = [s for s in statuses if s != "cancelled"]
    if not counted:
        return Decimal(0)
    pct = Decimal(sum(1 for s in counted if s == "done") * 100) / len(counted)
    return pct.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def planned(start: date | None, end: date | None, as_of: date) -> Decimal | None:
    if start is None or end is None:
        return None
    return linear_progress(start, end, as_of)


def is_late(planned_pct: Decimal | None, progress_pct: Decimal) -> bool:
    return planned_pct is not None and planned_pct - progress_pct > LATE_GAP_PCT


def project_late(
    status: str, start: date | None, end: date | None, statuses: Iterable[str], as_of: date
) -> bool:
    """`late` badge of a project; closed (done/cancelled) projects are never late."""
    if status in CLOSED_PROJECT:
        return False
    return is_late(planned(start, end, as_of), progress(statuses))


def milestone_late(status: str, due: date, as_of: date) -> bool:
    """R-DEC-49: `planned` milestone past its `due_date`."""
    return status == "planned" and due < as_of


def rounded(value: Decimal | None) -> float | None:
    return None if value is None else float(value.quantize(Decimal("0.1"), ROUND_HALF_UP))

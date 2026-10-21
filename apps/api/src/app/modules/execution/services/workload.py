"""Public workload service (03 §2.2 METRIC-HR-03, HR EP-87) — DEC-226.

`workload = Σ estimate_hours (missing → DEFAULT_TASK_HOURS) of the assignee's open tasks ÷
WEEKLY_CAPACITY_HOURS × 100`. A task is open in a week when it is assigned, not cancelled,
created before the week ends and not done before the week starts. `overloaded` = load above
`OVERLOAD_PCT` in the week ending `as_of` **and** the week before (2 consecutive weeks).
"""

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.models import Task
from app.modules.execution.repositories import TaskRepository

DEFAULT_TASK_HOURS = Decimal(4)  # 03 OQ-03
WEEKLY_CAPACITY_HOURS = Decimal(40)
OVERLOAD_PCT = Decimal(110)
OVERLOAD_WEEKS = 2


@dataclass(frozen=True)
class WorkloadRow:
    employee_id: uuid.UUID
    open_tasks: int
    estimate_hours: float
    load_pct: float
    overloaded: bool


def _hours(t: Task) -> Decimal:
    return Decimal(t.estimate_hours) if t.estimate_hours is not None else DEFAULT_TASK_HOURS


def _open_in(t: Task, start: datetime, end: datetime) -> bool:
    return t.created_at < end and (t.done_at is None or t.done_at >= start)


def _ts(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=UTC)


def load_pct(hours: Decimal) -> Decimal:
    return (hours / WEEKLY_CAPACITY_HOURS * 100).quantize(Decimal("0.01"), ROUND_HALF_UP)


def weekly_hours(tasks: Sequence[Task], week_end: date) -> dict[uuid.UUID, tuple[int, Decimal]]:
    """`{assignee: (open task count, Σ hours)}` for the 7 days ending `week_end` (inclusive)."""
    start, end = _ts(week_end - timedelta(days=6)), _ts(week_end + timedelta(days=1))
    out: dict[uuid.UUID, tuple[int, Decimal]] = defaultdict(lambda: (0, Decimal(0)))
    for t in tasks:
        if t.assignee_id is not None and _open_in(t, start, end):
            n, h = out[t.assignee_id]
            out[t.assignee_id] = (n + 1, h + _hours(t))
    return dict(out)


def rows_from(tasks: Sequence[Task], as_of: date) -> list[WorkloadRow]:
    weeks = [weekly_hours(tasks, as_of - timedelta(days=7 * i)) for i in range(OVERLOAD_WEEKS)]
    rows = []
    for emp, (n, hours) in weeks[0].items():
        over = all(load_pct(w.get(emp, (0, Decimal(0)))[1]) > OVERLOAD_PCT for w in weeks)
        rows.append(WorkloadRow(employee_id=emp, open_tasks=n, estimate_hours=float(hours),
                                load_pct=float(load_pct(hours)), overloaded=over))  # fmt: skip
    return sorted(rows, key=lambda r: (-r.load_pct, str(r.employee_id)))


async def load_tasks(
    db: AsyncSession, department_id: uuid.UUID | None, as_of: date
) -> Sequence[Task]:
    since = as_of - timedelta(days=7 * OVERLOAD_WEEKS - 1)
    return await TaskRepository(db).assigned_active(since, as_of + timedelta(days=1),
                                                    department_id)  # fmt: skip


async def workload(
    db: AsyncSession, department_id: uuid.UUID | None, as_of: date
) -> list[WorkloadRow]:
    """Per-assignee load for the week ending `as_of` (highest first). Read-only."""
    return rows_from(await load_tasks(db, department_id, as_of), as_of)

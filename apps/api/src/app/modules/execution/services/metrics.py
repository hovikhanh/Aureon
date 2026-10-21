"""Execution metric provider (03 §2.2, §2.5) — METRIC-OPS-01..03, METRIC-HR-03, METRIC-RSK-06.

All company scope, `period_key = YYYY-MM` of `as_of`; `value=None` (+ `status_reason`) when
there is nothing to measure. Status is left to the catalog thresholds. Window: tasks with
`due_date` in `[month start, as_of]` (tasks that have come due — DEC-226); cancelled tasks
are not counted. OPS-02 actual progress = share of `done` among the project's non-cancelled
tasks (05 `projects` has no progress column — DEC-226).
"""

from collections.abc import Iterable, Sequence
from datetime import UTC, date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import month_key, month_range
from app.core.data_quality import DqSource, register_dq
from app.core.metrics import MetricReading, RecordRef, metric_provider
from app.modules.execution.models import Initiative, Project, Task
from app.modules.execution.repositories import (
    InitiativeRepository,
    ProjectRepository,
    TaskRepository,
)
from app.modules.execution.services.initiative_service import share_done
from app.modules.execution.services.workload import load_tasks, rows_from

MAX_RECORDS = 50
LATE_GAP_PCT = Decimal(10)  # METRIC-OPS-02
SEI_ON_TRACK_RATIO = Decimal("0.9")  # METRIC-RSK-06 (DEC-226)


def pct(part: int | Decimal, whole: int | Decimal) -> float | None:
    if not whole:
        return None
    return float((Decimal(part) / Decimal(whole) * 100).quantize(Decimal("0.1"), ROUND_HALF_UP))


def refs(table: str, ids: Iterable[object]) -> tuple[RecordRef, ...]:
    return tuple(RecordRef("execution", table, str(i)) for i in list(ids)[:MAX_RECORDS])


def linear_progress(start: date, end: date, as_of: date) -> Decimal:
    """Planned % complete at `as_of`, linear over `[start, end]`, clamped to 0..100."""
    if as_of >= end:
        return Decimal(100)
    if as_of <= start:
        return Decimal(0)
    return Decimal((as_of - start).days * 100) / Decimal((end - start).days)


def on_time(t: Task) -> bool:
    return (
        t.status == "done"
        and t.done_at is not None
        and t.due_date is not None
        and t.done_at.astimezone(UTC).date() <= t.due_date
    )


def from_meeting(t: Task) -> bool:
    return t.decision_id is not None or t.meeting_id is not None or t.task_source == "meeting"


def reading(code: str, value: float | None, key: str, records: tuple[RecordRef, ...],
            reason: str) -> MetricReading:  # fmt: skip
    return MetricReading(code=code, value=value, period_key=key, records=records,
                         status_reason=None if value is not None else reason)  # fmt: skip


def ops01(due: Sequence[Task], key: str) -> MetricReading:
    hit = [t for t in due if on_time(t)]
    return reading("METRIC-OPS-01", pct(len(hit), len(due)), key,
                   refs("tasks", (t.id for t in due)), "no tasks due in period")  # fmt: skip


def ops03(due: Sequence[Task], key: str) -> MetricReading:
    src = [t for t in due if from_meeting(t)]
    done = [t for t in src if t.status == "done"]
    return reading("METRIC-OPS-03", pct(len(done), len(src)), key,
                   refs("tasks", (t.id for t in src)),
                   "no decision/meeting tasks due in period")  # fmt: skip


def ops02(projects: Sequence[Project], tasks: Sequence[Task], as_of: date,
          key: str) -> MetricReading:  # fmt: skip
    by_project: dict[object, list[str]] = {}
    for t in tasks:
        by_project.setdefault(t.project_id, []).append(t.status)
    late = []
    for p in projects:
        if p.start_date is None or p.planned_end_date is None:
            continue
        planned = linear_progress(p.start_date, p.planned_end_date, as_of)
        actual = share_done(by_project.get(p.id, []), skip="cancelled")
        if planned - actual > LATE_GAP_PCT:
            late.append(p.id)
    return reading("METRIC-OPS-02", pct(len(late), len(projects)), key,
                   refs("projects", late), "no running projects")  # fmt: skip


def hr03(tasks: Sequence[Task], as_of: date, key: str) -> MetricReading:
    rows = rows_from(tasks, as_of)
    over = {r.employee_id for r in rows if r.overloaded}
    ids = [t.id for t in tasks if t.assignee_id in over and t.done_at is None]
    return reading("METRIC-HR-03", pct(len(over), len(rows)), key, refs("tasks", ids),
                   "no assigned open tasks")  # fmt: skip


def rsk06(initiatives: Sequence[Initiative], as_of: date, key: str) -> MetricReading:
    if not initiatives:
        return reading("METRIC-RSK-06", None, key, (), "no active initiatives")
    weights = [Decimal(i.weight_pct) for i in initiatives]
    if sum(weights) == 0:
        weights = [Decimal(1)] * len(initiatives)
    hit = Decimal(0)
    for i, w in zip(initiatives, weights, strict=True):
        expected = linear_progress(i.start_date, i.planned_end_date, as_of)
        if Decimal(i.progress_pct) >= expected * SEI_ON_TRACK_RATIO:
            hit += w
    return reading("METRIC-RSK-06", pct(hit, sum(weights)), key,
                   refs("initiatives", (i.id for i in initiatives)), "")  # fmt: skip


@metric_provider("execution")
async def compute(db: AsyncSession, as_of: date) -> list[MetricReading]:
    key = month_key(as_of)
    start, end = month_range(key)
    task_repo = TaskRepository(db)
    due = [t for t in await task_repo.due_between(start, min(end, as_of + timedelta(days=1)))
           if t.status != "cancelled"]  # fmt: skip
    projects = await ProjectRepository(db).running(as_of)
    project_tasks = await task_repo.for_parents(Task.project_id, [p.id for p in projects])
    return [
        ops01(due, key),
        ops02(projects, project_tasks, as_of, key),
        ops03(due, key),
        hr03(await load_tasks(db, None, as_of), as_of, key),
        rsk06(await InitiativeRepository(db).in_flight(start, end), as_of, key),
    ]


# METRIC-DQ-01 sources (03 §2.6, DEC-209): required business fields + validation failures.
register_dq(
    "execution",
    DqSource(Task, ("assignee_id", "due_date", "department_id"),
             (lambda m: (m.status == "done") & m.done_at.is_(None),
              lambda m: (m.status == "blocked") & m.blocked_reason.is_(None))),
    DqSource(Project, ("start_date", "planned_end_date", "department_id")),
)  # fmt: skip

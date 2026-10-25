"""Execution metric provider (03 §2.2, §2.5, §4) — METRIC-OPS-01..03, METRIC-HR-03,
METRIC-RSK-06 (SEI) and METRIC-STR-01 (G2 "KPI/OKR cập nhật đúng kỳ", R-DEC-54).

All company scope, `period_key = YYYY-MM` of `as_of`; `value=None` (+ `status_reason`) when
there is nothing to measure. Status is left to the catalog thresholds. Window: tasks with
`due_date` in `[month start, as_of]` (tasks that have come due — DEC-226); cancelled tasks
are not counted. OPS-02 actual progress = share of `done` among the project's non-cancelled
tasks (05 `projects` has no progress column — DEC-226).

G2 (05 §2.6): `pct(#on-time KPI-periods + #on-time KRs, #due KPI-periods + #active KRs)`. Due
KPI-period = the most recent period of each `active` KPI whose `end + GOALS_KPI_GRACE_DAYS` has
passed; on time = its KPIEvaluation `measured_on_time`. Active KR = KR of an `active` objective
whose period contains `as_of`; on time = `last_checked_in_at ≥ as_of −
GOALS_KR_CHECKIN_MAX_AGE_DAYS`. `records` = late KPIs + KRs; SEI `records` = late initiatives.
"""

import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capture_share import CaptureSource, register_capture_source
from app.core.clock import month_key, month_range
from app.core.config import get_config
from app.core.data_quality import DqSource, register_dq
from app.core.metrics import MetricReading, RecordRef, metric_provider
from app.modules.execution.models import (
    Initiative,
    KeyResult,
    Kpi,
    KpiMeasurement,
    KpiTarget,
    Objective,
    Project,
    Task,
)
from app.modules.execution.repositories import (
    InitiativeRepository,
    KeyResultRepository,
    KpiEvaluationRepository,
    KpiRepository,
    ProjectRepository,
    TaskRepository,
)
from app.modules.execution.services.at_risk import current_objectives
from app.modules.execution.services.kpi_rules import (
    last_ended_period,
    local_day,
    period_bounds,
)
from app.modules.execution.services.project_rules import (
    LATE_GAP_PCT,
    is_late,
    linear_progress,
    planned,
    progress,
)
from app.modules.execution.services.workload import load_tasks, rows_from

__all__ = ["LATE_GAP_PCT", "linear_progress"]  # re-exported (tests / RSK-06)

MAX_RECORDS = 50
SEI_ON_TRACK_RATIO = Decimal("0.9")  # METRIC-RSK-06 (DEC-226)


def pct(part: int | Decimal, whole: int | Decimal) -> float | None:
    if not whole:
        return None
    return float((Decimal(part) / Decimal(whole) * 100).quantize(Decimal("0.1"), ROUND_HALF_UP))


def refs(table: str, ids: Iterable[object]) -> tuple[RecordRef, ...]:
    return tuple(RecordRef("execution", table, str(i)) for i in list(ids)[:MAX_RECORDS])


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
        plan = planned(p.start_date, p.planned_end_date, as_of)
        if plan is not None and is_late(plan, progress(by_project.get(p.id, []))):
            late.append(p.id)
    return reading("METRIC-OPS-02", pct(len(late), len(projects)), key,
                   refs("projects", late), "no running projects")  # fmt: skip


def hr03(tasks: Sequence[Task], as_of: date, key: str) -> MetricReading:
    rows = rows_from(tasks, as_of)
    over = {r.employee_id for r in rows if r.overloaded}
    ids = [t.id for t in tasks if t.assignee_id in over and t.done_at is None]
    return reading("METRIC-HR-03", pct(len(over), len(rows)), key, refs("tasks", ids),
                   "no assigned open tasks")  # fmt: skip


def sei_on_track(i: Initiative, as_of: date) -> bool:
    """SEI rule (DEC-226): progress ≥ 0.9 × linear plan — also EP-STR-01 `on_track`."""
    expected = linear_progress(i.start_date, i.planned_end_date, as_of)
    return Decimal(i.progress_pct) >= expected * SEI_ON_TRACK_RATIO


def rsk06(initiatives: Sequence[Initiative], as_of: date, key: str) -> MetricReading:
    if not initiatives:
        return reading("METRIC-RSK-06", None, key, (), "no active initiatives")
    weights = [Decimal(i.weight_pct) for i in initiatives]
    if sum(weights) == 0:
        weights = [Decimal(1)] * len(initiatives)
    hit = Decimal(0)
    for i, w in zip(initiatives, weights, strict=True):
        if sei_on_track(i, as_of):
            hit += w
    late = (i.id for i in initiatives if not sei_on_track(i, as_of))
    return reading("METRIC-RSK-06", pct(hit, sum(weights)), key,
                   refs("initiatives", late), "")  # fmt: skip


def due_period(period_type: str, as_of: date, grace_days: int) -> str:
    """Most recent period whose `end + grace` is ≤ `as_of` (a due KPI-period, R-DEC-54)."""
    key = last_ended_period(period_type, as_of)
    if as_of < period_bounds(key)[1] + timedelta(days=grace_days):
        key = last_ended_period(period_type, period_bounds(key)[0])
    return key


def str01(
    kpi_periods: Sequence[tuple[uuid.UUID, str]], on_time_kpis: set[tuple[uuid.UUID, str]],
    krs: Sequence[KeyResult], as_of: date, max_age_days: int, key: str,
) -> MetricReading:  # fmt: skip
    """G2: `kpi_periods` = due `(kpi, period)`; `on_time_kpis` = those measured on time."""
    late_kpis = [k for k, p in kpi_periods if (k, p) not in on_time_kpis]
    oldest = as_of - timedelta(days=max_age_days)
    late_krs = [
        r.id
        for r in krs
        if r.last_checked_in_at is None or local_day(r.last_checked_in_at) < oldest
    ]
    due = len(kpi_periods) + len(krs)
    records = (*refs("kpis", late_kpis), *refs("key_results", late_krs))[:MAX_RECORDS]
    return reading("METRIC-STR-01", pct(due - len(late_kpis) - len(late_krs), due), key,
                   records, "no active KPIs or key results")  # fmt: skip


async def load_str01(db: AsyncSession, as_of: date, key: str) -> MetricReading:
    cfg = get_config()
    kpis = await KpiRepository(db).where(Kpi.status == "active", order=Kpi.code)
    pairs = [(k.id, due_period(k.period_type, as_of, cfg.goals_kpi_grace_days)) for k in kpis]
    evs = await KpiEvaluationRepository(db).for_pairs(pairs)
    objs = [o.id for o in await current_objectives(db, as_of)]
    krs = (await KeyResultRepository(db).where(KeyResult.objective_id.in_(objs),
                                               order=KeyResult.id) if objs else [])  # fmt: skip
    return str01(pairs, {p for p, e in evs.items() if e.measured_on_time}, krs, as_of,
                 cfg.goals_kr_checkin_max_age_days, key)  # fmt: skip


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
        await load_str01(db, as_of, key),
    ]


# METRIC-DQ-01 sources (03 §2.6, DEC-209): required business fields + validation failures.
register_dq(
    "execution",
    DqSource(Task, ("assignee_id", "due_date", "department_id"),
             (lambda m: (m.status == "done") & m.done_at.is_(None),
              lambda m: (m.status == "blocked") & m.blocked_reason.is_(None))),
    DqSource(Project, ("start_date", "planned_end_date", "department_id")),
)  # fmt: skip

# METRIC-DQ-02 (R-DEC-68). `check_ins` carry no provenance column → not counted; measurements
# use `data_source` (document / ai_assisted = captured).
register_capture_source(
    "execution",
    *(CaptureSource(m) for m in (Task, Kpi, KpiTarget, Objective, KeyResult)),
    CaptureSource(KpiMeasurement,
                  lambda m: m.data_source.in_(("document", "ai_assisted"))),
)  # fmt: skip

"""T-133 — execution metric maths (03 §2.2/§2.5, DEC-226) on in-memory rows (TC-EXE-006)."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.core.metrics import METRIC_PROVIDERS
from app.modules.execution.models import Initiative, Project, Task
from app.modules.execution.services import metrics as m

D = date(2037, 5, 20)
KEY = "2037-05"


def t(status: str = "todo", due: date | None = D, done: date | None = None, **kw: object) -> Task:
    done_at = datetime(done.year, done.month, done.day, 9, tzinfo=UTC) if done else None
    return Task(id=uuid.uuid4(), title="t", status=status, due_date=due, done_at=done_at,
                task_source=kw.pop("task_source", "manual"), **kw)  # fmt: skip


def test_registered() -> None:
    fn = METRIC_PROVIDERS.providers["execution"]  # may be a re-imported copy (arch tests)
    assert (fn.__module__, fn.__qualname__) == (m.compute.__module__, m.compute.__qualname__)


def test_ops01_ops03() -> None:
    due = [
        t("done", done=date(2037, 5, 19)), t("done", done=date(2037, 5, 21)), t("todo"),
        t("in_review", task_source="meeting"), t("done", done=D, decision_id=uuid.uuid4()),
    ]  # fmt: skip
    r1 = m.ops01(due, KEY)
    assert (r1.code, r1.value, r1.period_key, r1.scope_type) == ("METRIC-OPS-01", 40.0, KEY,
                                                                 "company")  # fmt: skip
    assert len(r1.records) == 5 and r1.records[0].schema == "execution"
    r3 = m.ops03(due, KEY)
    assert r3.value == 50.0 and len(r3.records) == 2
    empty = m.ops01([], KEY)
    assert empty.value is None and empty.status_reason == "no tasks due in period"
    assert m.ops03([t()], KEY).value is None


def test_ops02_projects() -> None:
    late = Project(
        id=uuid.uuid4(), start_date=date(2037, 1, 1), planned_end_date=date(2037, 12, 31)
    )
    fine = Project(
        id=uuid.uuid4(), start_date=date(2037, 5, 1), planned_end_date=date(2037, 12, 31)
    )
    tasks = [t("done", done=D, project_id=fine.id), t("todo", project_id=late.id),
             t("done", done=D, project_id=late.id), t("cancelled", project_id=late.id)]  # fmt: skip
    r = m.ops02([late, fine], tasks, D, KEY)
    # late: planned ≈ 38.4%, actual 50% → on track; fine: planned ≈ 7.8%, actual 100%
    assert r.value == 0.0 and r.records == ()
    lagging = Project(id=uuid.uuid4(), start_date=date(2037, 1, 1), planned_end_date=D)
    r2 = m.ops02([lagging, fine], [t("todo", project_id=lagging.id)], D, KEY)
    assert r2.value == 50.0 and r2.records[0].id == str(lagging.id)
    assert m.ops02([], [], D, KEY).value is None
    assert m.linear_progress(date(2037, 6, 1), date(2037, 7, 1), D) == 0


def test_hr03_overload() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    old = datetime(2037, 4, 1, tzinfo=UTC)
    tasks = [Task(id=uuid.uuid4(), title="x", status="todo", assignee_id=a, created_at=old,
                  estimate_hours=Decimal(50)),
             Task(id=uuid.uuid4(), title="y", status="todo", assignee_id=b, created_at=old,
                  estimate_hours=None)]  # fmt: skip
    r = m.hr03(tasks, D, KEY)
    assert r.value == 50.0 and [x.id for x in r.records] == [str(tasks[0].id)]
    assert m.hr03([], D, KEY).value is None


def ini(weight: int, progress: int, start: date = date(2037, 1, 1)) -> Initiative:
    return Initiative(id=uuid.uuid4(), weight_pct=Decimal(weight), progress_pct=Decimal(progress),
                      start_date=start, planned_end_date=date(2037, 12, 31))  # fmt: skip


def test_rsk06_sei() -> None:
    # expected ≈ 38.4% → on-track threshold ≈ 34.5%
    r = m.rsk06([ini(30, 40), ini(70, 10)], D, KEY)
    assert r.code == "METRIC-RSK-06" and r.value == 30.0 and len(r.records) == 2
    assert m.rsk06([ini(0, 40), ini(0, 10)], D, KEY).value == 50.0  # equal weights
    none = m.rsk06([], D, KEY)
    assert none.value is None and none.status_reason == "no active initiatives"


def test_records_capped() -> None:
    assert len(m.refs("tasks", range(80))) == m.MAX_RECORDS
    assert m.pct(1, 3) == 33.3 and m.pct(1, 0) is None

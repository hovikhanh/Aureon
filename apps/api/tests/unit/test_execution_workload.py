"""T-133 — workload maths (METRIC-HR-03 input, DEC-226), pure on in-memory Task rows."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.modules.execution.models import Task
from app.modules.execution.services.workload import load_pct, rows_from

AS_OF = date(2037, 3, 14)


def task(emp: uuid.UUID, hours: str | None, created: date, done: date | None = None) -> Task:
    return Task(
        title="t", assignee_id=emp, status="done" if done else "todo",
        estimate_hours=Decimal(hours) if hours else None,
        created_at=datetime(created.year, created.month, created.day, 9, tzinfo=UTC),
        done_at=datetime(done.year, done.month, done.day, 9, tzinfo=UTC) if done else None,
    )  # fmt: skip


def test_load_and_two_week_overload() -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    tasks = [
        task(a, "30", date(2037, 2, 1)), task(a, "15", date(2037, 2, 1)),  # 45 h both weeks
        task(b, "45", date(2037, 3, 10)),  # only this week → not overloaded
        task(c, None, date(2037, 2, 1)),  # default 4 h
        task(c, "50", date(2037, 2, 1), done=date(2037, 3, 1)),  # done before window
        task(c, "8", date(2037, 2, 1), done=date(2037, 3, 9)),  # done inside this week
    ]  # fmt: skip
    rows = {r.employee_id: r for r in rows_from(tasks, AS_OF)}
    assert rows[a].load_pct == 112.5 and rows[a].overloaded and rows[a].open_tasks == 2
    assert rows[b].load_pct == 112.5 and not rows[b].overloaded
    assert rows[c].estimate_hours == 12 and rows[c].open_tasks == 2 and rows[c].load_pct == 30
    assert [r.employee_id for r in rows_from(tasks, AS_OF)][-1] == c
    assert load_pct(Decimal(44)) == Decimal("110.00")
    assert rows_from([], AS_OF) == []

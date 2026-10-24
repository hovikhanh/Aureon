"""TC-M13-05 (T-620) — workload grid + project late/progress + milestones per project.

Seed numbers come from the seed itself (the `seeded` fixture of `test_seed_v3`: truncate →
seed twice, rolled back), reference date 20/10/2026 = ISO week 2026-W43 (08 §5).
"""

import uuid
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.execution.models import Task
from app.modules.execution.services.project_rules import (
    is_late,
    milestone_late,
    progress,
    project_late,
)
from app.modules.execution.services.workload import iso_week, parse_iso_week
from tests.conftest import ApiClient
from tests.integration.execution.helpers import (
    as_user,
    audit_actions,
    make,
    make_task,
    patch,
    uniq,
)
from tests.integration.execution.test_initiatives import make_initiative
from tests.integration.test_seed_v3 import AS_OF, TRUNCATE_ALL, _seed_all

pytestmark = pytest.mark.integration


@pytest.fixture
async def seeded(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> AsyncSession:
    from app.core.config import get_config

    monkeypatch.setattr(get_config(), "demo_reference_date", AS_OF.isoformat())
    await db_session.execute(TRUNCATE_ALL)
    await _seed_all(db_session)
    return db_session


def test_pure_project_rules() -> None:
    assert progress(["done", "todo", "cancelled"]) == 50
    assert is_late(progress(["todo"]) + 61, progress(["done", "todo"])) is True
    assert (
        project_late("done", date(2026, 1, 1), date(2026, 2, 1), ["todo"], date(2026, 10, 1))
        is False
    )
    assert milestone_late("planned", date(2026, 10, 1), date(2026, 10, 2)) is True
    assert milestone_late("done", date(2026, 10, 1), date(2026, 10, 2)) is False
    assert parse_iso_week("2026-W43") == date(2026, 10, 25)
    assert iso_week(date(2026, 10, 20)) == "2026-W43"
    with pytest.raises(ValueError):
        parse_iso_week("2026-43")


async def test_workload_on_seed(api: ApiClient, seeded: AsyncSession) -> None:
    r = await api.call("GET", "/work/workload", "CEO", params={"week": "2026-W43"})
    assert r.status_code == 200
    assert r.headers["vary"] == "Authorization" and "max-age=60" in r.headers["cache-control"]
    body = r.json()["data"]
    assert body["weeks"] == ["2026-W40", "2026-W41", "2026-W42", "2026-W43"]
    assert (body["threshold_pct"], body["overload_weeks"], body["capacity_hours"]) == (110, 2, 40)
    assert body["summary"] == {"people": 25, "overloaded_count": 3, "overloaded_pct": 12.0}
    over = [row for row in body["rows"] if row["overloaded"]]
    assert all(c["load_pct"] > 110 for row in over for c in row["cells"][-2:])
    assert "name" not in body["rows"][0] and len(body["rows"][0]["cells"]) == 4

    assert (await api.call("GET", "/work/workload", "CEO",
                           params={"week": "2026-43"})).status_code == 400  # fmt: skip
    emp = await api.call("GET", "/work/workload", "EMP")
    assert emp.status_code == 403 and emp.json()["error"]["code"] == "FORBIDDEN_ROLE"
    mgr = await api.call("GET", "/work/workload", "MGR", department_id=uuid.uuid4(),
                         params={"department_id": str(uuid.uuid4())})  # fmt: skip
    assert mgr.status_code == 403 and mgr.json()["error"]["code"] == "FORBIDDEN_SCOPE"

    late = await api.call("GET", "/work/projects", "CEO", params={"late": "true"})
    assert [p["code"] for p in late.json()["data"]] == ["PRJ-ERP"]
    erp = late.json()["data"][0]
    assert erp["late"] is True and erp["planned_pct"] - erp["progress_pct"] > 10
    not_late = await api.call("GET", "/work/projects", "CEO", params={"late": "false"})
    assert len(not_late.json()["data"]) == 9

    # EMP sees projects they hold a task in (Ngô Thị Lan, employee@)
    u = (await seeded.execute(select(User).where(User.email == "employee@abc.demo"))).scalar_one()
    mine = await as_user(api, "GET", "/work/projects", "EMP", u.id, department_id=u.department_id,
                         employee_id=u.employee_id)  # fmt: skip
    assert mine.status_code == 200  # her 2 seed tasks have no project → own/assigned only
    tasks = await as_user(api, "GET", "/work/tasks", "EMP", u.id, department_id=u.department_id,
                          employee_id=u.employee_id, params={"mine": "true"})  # fmt: skip
    assert tasks.json()["meta"]["pagination"]["total"] >= 1  # TC-M13-02 on seed


async def test_project_milestones_and_detail(api: ApiClient, db_session: AsyncSession) -> None:
    ini = await make_initiative(api, uuid.uuid4())
    p = await make(api, "/work/projects", {
        "code": uniq("PRJ"), "name": "P", "owner_id": str(uuid.uuid4()),
        "start_date": "2026-01-01", "due_date": "2026-12-31", "initiative_id": ini["id"],
    })  # fmt: skip
    assert p["initiative_id"] == ini["id"] and p["open_tasks"] == 0
    flt = await api.call("GET", "/work/projects", "CEO", params={"initiative_id": ini["id"]})
    assert [x["id"] for x in flt.json()["data"]] == [p["id"]]
    bad = await api.call("POST", "/work/projects", "CEO", json={
        "code": uniq("PRJ"), "name": "P", "owner_id": str(uuid.uuid4()),
        "initiative_id": str(uuid.uuid4()),
    })  # fmt: skip
    assert bad.status_code == 422

    url = f"/work/projects/{p['id']}/milestones"
    m_late = await make(api, url, {"title": "A", "due_date": "2026-01-15"})
    m_ok = await make(api, url, {"title": "B", "due_date": "2099-01-15"})
    assert m_late["project_id"] == p["id"] and m_late["late"] is True and m_ok["late"] is False
    asc = {"sort_by": "due_date", "order": "asc"}
    lst = (await api.call("GET", url, "CEO", params=asc)).json()["data"]
    assert [x["id"] for x in lst] == [m_late["id"], m_ok["id"]]
    t = await make_task(api, project_id=p["id"], milestone_id=m_late["id"], due_date="2026-01-02")
    done = await patch(api, f"{url}/{m_late['id']}", 1, status="done")
    assert (
        done.status_code == 200
        and done.json()["data"]["done_at"]
        and not done.json()["data"]["late"]
    )
    other = await make(api, "/work/projects", {"code": uniq("PRJ"), "name": "Q",
                                               "owner_id": str(uuid.uuid4())})  # fmt: skip
    wrong = await patch(api, f"/work/projects/{other['id']}/milestones/{m_ok['id']}", 1, title="x")
    assert wrong.status_code == 404

    d = (await api.call("GET", f"/work/projects/{p['id']}", "CEO")).json()["data"]
    assert [x["id"] for x in d["milestones"]] == [m_late["id"], m_ok["id"]]
    assert d["task_counts"] == {"by_status": {"todo": 1}}
    assert d["open_tasks"] == 1 and d["overdue_tasks"] == 1

    gone = await api.call("DELETE", f"{url}/{m_late['id']}", "CEO")
    assert gone.status_code == 204
    after = (await api.call("GET", f"/work/tasks/{t['id']}", "CEO")).json()["data"]
    assert after["milestone_id"] is None
    assert "execution.task_update" in await audit_actions(db_session, t["id"])
    assert sorted(await audit_actions(db_session, m_late["id"])) == [
        "execution.milestone_create", "execution.milestone_delete", "execution.milestone_update",
    ]  # fmt: skip


@pytest.mark.parametrize("as_of", [date(2026, 10, 20), date(2026, 10, 14), date(2026, 10, 8)])
async def test_workload_summary_matches_hr03(
    api: ApiClient, seeded: AsyncSession, monkeypatch: pytest.MonkeyPatch, as_of: date
) -> None:
    """R-DEC-44: `summary.overloaded_pct` of the current (unfinished) week = stored METRIC-HR-03
    recomputed at the same mid-week day (the week is measured up to `min(week_end, today)`)."""
    from app.core.config import get_config
    from app.modules.platform.models import Metric, MetricValue
    from app.modules.platform.services.metric_store import MetricStore, seed_catalog
    from app.workers.consumers import load_metric_providers

    monkeypatch.setattr(get_config(), "demo_reference_date", as_of.isoformat())
    # a task created later in the same ISO week: counted by a full-week window, not by HR-03
    late = await make_task(api, assignee_id=str(uuid.uuid4()), estimate_hours=60)
    when = datetime.combine(as_of + timedelta(days=1), time(9), tzinfo=UTC)
    if iso_week(when.date()) == iso_week(as_of):
        await seeded.execute(update(Task).where(Task.id == uuid.UUID(late["id"]))
                             .values(created_at=when))  # fmt: skip
    await seed_catalog(seeded)
    load_metric_providers()
    assert (await MetricStore(seeded).recompute(as_of))["failed_providers"] == 0
    hr03 = (await seeded.execute(
        select(MetricValue.value).join(Metric, MetricValue.metric_id == Metric.id)
        .where(Metric.code == "METRIC-HR-03", MetricValue.is_current.is_(True),
               MetricValue.scope_type == "company")
    )).scalar_one()  # fmt: skip
    for params in ({}, {"week": iso_week(as_of)}):
        r = await api.call("GET", "/work/workload", "CEO", params=params)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["summary"]["overloaded_pct"] == float(hr03 or 0)

"""T-131 / T-133 — EP-44 tasks L C R U D, 7 statuses, scope `◑d`/`◑o`, overdue job (TC-EXE-001)."""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.services.task_service import detect_overdue_tasks
from tests.conftest import ApiClient
from tests.integration.execution.helpers import (
    as_user,
    audit_actions,
    make_task,
    outbox_for,
    patch,
)

pytestmark = pytest.mark.integration


async def test_task_crud_and_status_machine(api: ApiClient, db_session: AsyncSession) -> None:
    t = await make_task(
        api, start_date="2037-01-01", due_date="2037-01-10", estimate_hours="6.5",
        evidence=[{"kind": "link", "ref": "https://x.test"}], priority="high",
    )  # fmt: skip
    assert t["status"] == "todo" and t["task_source"] == "manual" and t["source"] == "MANUAL"
    assert t["estimate_hours"] == 6.5 and t["version"] == 1 and t["overdue"] is False
    assert t["data_classification"] == "INTERNAL" and t["owner_id"] is not None
    tid = t["id"]
    blocked = await api.call("PATCH", f"/execution/tasks/{tid}", "CEO",
                             json={"status": "blocked", "version": 1})  # fmt: skip
    assert blocked.status_code == 422
    assert blocked.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    ok = await patch(api, f"/execution/tasks/{tid}", 1, status="blocked", blocked_reason="chờ NCC")
    assert ok.status_code == 200 and ok.json()["data"]["blocked_reason"] == "chờ NCC"
    bad = await api.call("PATCH", f"/execution/tasks/{tid}", "CEO",
                         json={"status": "done", "version": 2})  # fmt: skip
    assert bad.status_code == 409 and bad.json()["error"]["code"] == "CONFLICT_STATE"
    for i, st in enumerate(("in_progress", "in_review", "done"), start=2):
        r = await api.call("PATCH", f"/execution/tasks/{tid}", "CEO",
                           json={"status": st, "version": i})  # fmt: skip
        assert r.status_code == 200, r.text
    done = r.json()["data"]
    assert done["done_at"] is not None and done["blocked_reason"] is None
    stale = await api.call("PATCH", f"/execution/tasks/{tid}", "CEO", json={"version": 1})
    assert stale.status_code == 409
    reopen = await patch(api, f"/execution/tasks/{tid}", 5, status="in_progress", actual_hours=3)
    assert reopen.status_code == 200 and reopen.json()["data"]["done_at"] is None
    assert (await api.call("GET", f"/execution/tasks/{tid}", "CEO")).status_code == 200
    assert (await api.call("DELETE", f"/execution/tasks/{tid}", "CEO")).status_code == 204
    assert (await api.call("GET", f"/execution/tasks/{tid}", "CEO")).status_code == 404
    actions = await audit_actions(db_session, tid)
    assert actions.count("execution.task_update") == 5
    assert "execution.task_create" in actions and "execution.task_delete" in actions


async def test_task_validation(api: ApiClient) -> None:
    dates = await api.call("POST", "/execution/tasks", "CEO", json={
        "title": "x", "start_date": "2037-02-01", "due_date": "2037-01-01"})  # fmt: skip
    assert dates.status_code == 422
    ref = await api.call("POST", "/execution/tasks", "CEO",
                         json={"title": "x", "project_id": str(uuid.uuid4())})  # fmt: skip
    assert ref.status_code == 422 and ref.json()["error"]["details"]["field"] == "project_id"
    blocked = await api.call("POST", "/execution/tasks", "CEO",
                             json={"title": "x", "status": "blocked"})  # fmt: skip
    assert blocked.status_code == 422
    done = await make_task(api, status="done")
    assert done["done_at"] is not None
    child = await make_task(api, parent_id=done["id"])
    assert child["parent_id"] == done["id"]
    selfp = await api.call("PATCH", f"/execution/tasks/{child['id']}", "CEO",
                           json={"parent_id": child["id"], "version": 1})  # fmt: skip
    assert selfp.status_code == 422
    missing = await api.call("POST", "/execution/tasks", "CEO", json={"title": "x"},
                             headers={"Idempotency-Key": ""})  # fmt: skip
    assert missing.status_code == 400
    assert (await api.call("GET", "/execution/tasks", "ADMIN")).status_code == 403
    nf = await api.call("GET", f"/execution/tasks/{uuid.uuid4()}", "CEO")
    assert nf.status_code == 404


async def test_task_scope_manager_and_employee(api: ApiClient) -> None:
    dept, other = uuid.uuid4(), uuid.uuid4()
    me = uuid.uuid4()
    t_dept = await make_task(api, department_id=str(dept))
    t_other = await make_task(api, department_id=str(other), assignee_id=str(me))
    lst = await api.call("GET", "/execution/tasks", "MANAGER", department_id=dept,
                         params={"department_id": str(dept), "limit": 100})  # fmt: skip
    assert lst.status_code == 200
    assert {x["department_id"] for x in lst.json()["data"]} == {str(dept)}
    assert (await api.call("GET", f"/execution/tasks/{t_other['id']}", "MANAGER",
                           department_id=dept)).status_code == 403  # fmt: skip
    pinned = await api.call("POST", "/execution/tasks", "MANAGER", department_id=dept,
                            json={"title": "m"})  # fmt: skip
    assert pinned.json()["data"]["department_id"] == str(dept)
    foreign = await api.call("POST", "/execution/tasks", "MANAGER", department_id=dept,
                             json={"title": "m", "department_id": str(other)})  # fmt: skip
    assert foreign.status_code == 403 and foreign.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    # EMPLOYEE `◑o`: sees / edits only tasks where owner or assignee
    mine = await as_user(api, "GET", "/execution/tasks", "EMPLOYEE", me)
    assert [x["id"] for x in mine.json()["data"]] == [t_other["id"]]
    assert (await as_user(api, "GET", f"/execution/tasks/{t_dept['id']}", "EMPLOYEE",
                          me)).status_code == 403  # fmt: skip
    upd = await as_user(api, "PATCH", f"/execution/tasks/{t_other['id']}", "EMPLOYEE", me,
                        json={"status": "in_progress", "version": 1})  # fmt: skip
    assert upd.status_code == 200
    reassign = await as_user(api, "PATCH", f"/execution/tasks/{t_other['id']}", "EMPLOYEE", me,
                             json={"assignee_id": str(uuid.uuid4()), "version": 2})  # fmt: skip
    assert reassign.status_code == 403
    own = await as_user(api, "POST", "/execution/tasks", "EMPLOYEE", me, json={"title": "e"})
    assert own.status_code == 201 and own.json()["data"]["assignee_id"] == str(me)
    move = await as_user(api, "PATCH", f"/execution/tasks/{own.json()['data']['id']}",
                         "EMPLOYEE", me,
                         json={"department_id": str(other), "version": 1})  # fmt: skip
    assert move.status_code == 403
    no_dept = await api.call("POST", "/execution/tasks", "MANAGER", json={"title": "z"})
    assert no_dept.status_code == 403


async def test_overdue_filter_and_job(api: ApiClient, db_session: AsyncSession) -> None:
    dept = uuid.uuid4()
    late = await make_task(api, due_date="2037-03-01", department_id=str(dept),
                           assignee_id=str(uuid.uuid4()))  # fmt: skip
    closed = await make_task(api, due_date="2037-03-01", status="done", department_id=str(dept))
    await make_task(api, due_date="2037-05-01", department_id=str(dept))
    ids = await detect_overdue_tasks(db_session, date(2037, 4, 1))
    assert uuid.UUID(late["id"]) in ids and uuid.UUID(closed["id"]) not in ids
    events = await outbox_for(db_session, late["id"])
    assert events == [("execution.task_overdue", {
        "task_id": late["id"], "assignee_id": late["assignee_id"],
        "department_id": str(dept), "due_date": "2037-03-01"})]  # fmt: skip
    again = await detect_overdue_tasks(db_session, date(2037, 4, 2))
    assert uuid.UUID(late["id"]) not in again
    moved = await api.call("PATCH", f"/execution/tasks/{late['id']}", "CEO",
                           json={"due_date": "2037-03-15", "version": 1})  # fmt: skip
    assert moved.status_code == 200
    rearmed = await detect_overdue_tasks(db_session, date(2037, 4, 3))
    assert uuid.UUID(late["id"]) in rearmed
    assert "execution.task_overdue" in await audit_actions(db_session, late["id"])
    p = {"department_id": str(dept), "limit": 100}
    od = await api.call("GET", "/execution/tasks", "CEO", params={**p, "overdue": "false"})
    assert od.status_code == 200 and all(not x["overdue"] for x in od.json()["data"])
    od2 = await api.call("GET", "/execution/tasks", "CEO", params={**p, "overdue": "true"})
    assert all(x["overdue"] for x in od2.json()["data"])
    assert len(od.json()["data"]) + len(od2.json()["data"]) == 3

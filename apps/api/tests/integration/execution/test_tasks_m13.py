"""TC-M13-01..03 (T-619) — employee_id identity, sub-task one level, dependencies, source_ref."""

import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.core.security import verify_access_token
from app.modules.execution.services.task_rules import find_cycle, source_kind_matches
from tests.conftest import ApiClient
from tests.integration.execution.helpers import as_user, audit_actions, make_task, patch

pytestmark = pytest.mark.integration

TENANT_B = uuid.UUID("00000000-0000-0000-0000-0000000000b2")


# ---------- TC-M13-01: migration 0014 (DB already at head) ----------
def test_migration_0014_columns_and_backfill() -> None:
    eng = create_engine(get_config().database_url.get_secret_value())
    try:
        with eng.connect() as c:
            cols = set(c.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'execution' AND table_name = 'tasks'"
            )).scalars())  # fmt: skip
            assert {"parent_task_id", "source_ref"} <= cols and "parent_id" not in cols
            proj = set(c.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'execution' AND table_name = 'projects'"
            )).scalars())  # fmt: skip
            assert "initiative_id" in proj
            cks = set(c.execute(text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'execution.task_dependencies'::regclass"
            )).scalars())  # fmt: skip
            assert "ck_task_dependencies_not_self" in cks
            # backfill: no task still points at a user that has an employee (R-DEC-41)
            left = c.execute(text(
                "SELECT count(*) FROM execution.tasks t JOIN auth.users u ON u.id = t.assignee_id "
                "WHERE u.employee_id IS NOT NULL"
            )).scalar_one()  # fmt: skip
            assert left == 0
            # meeting tasks got a source_ref from decision/meeting
            bad = c.execute(text(
                "SELECT count(*) FROM execution.tasks WHERE (decision_id IS NOT NULL "
                "OR meeting_id IS NOT NULL) AND source_ref IS NULL"
            )).scalar_one()  # fmt: skip
            assert bad == 0
    finally:
        eng.dispose()


# ---------- TC-M13-02: identity R-DEC-41 ----------
def test_token_carries_employee_id() -> None:
    emp = uuid.uuid4()
    h = ApiClient.headers("EMP", employee_id=emp)
    claims = verify_access_token(h["Authorization"].removeprefix("Bearer "))
    assert claims.employee_id == emp
    assert (
        verify_access_token(
            ApiClient.headers("EMP")["Authorization"].removeprefix("Bearer ")
        ).employee_id
        is None
    )


async def test_employee_scope_by_employee_id(api: ApiClient) -> None:
    user, emp, dept, other_dept = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    mine = await make_task(api, assignee_id=str(emp), department_id=str(dept))
    other = await make_task(api, assignee_id=str(uuid.uuid4()), department_id=str(dept))
    r = await as_user(api, "GET", "/work/tasks", "EMP", user, employee_id=emp,
                      params={"mine": "true"})  # fmt: skip
    assert [x["id"] for x in r.json()["data"]] == [mine["id"]]
    assert (await as_user(api, "GET", f"/work/tasks/{other['id']}", "EMP", user,
                          employee_id=emp)).status_code == 404  # fmt: skip
    ok = await as_user(api, "PATCH", f"/work/tasks/{mine['id']}", "EMP", user, employee_id=emp,
                       json={"status": "in_progress", "version": 1})  # fmt: skip
    assert ok.status_code == 200
    give = await as_user(api, "POST", "/work/tasks", "EMP", user, employee_id=emp,
                         json={"title": "x", "assignee_id": str(uuid.uuid4())})  # fmt: skip
    assert give.status_code == 403 and give.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    self_ = await as_user(api, "POST", "/work/tasks", "EMP", user, employee_id=emp,
                          json={"title": "x"})  # fmt: skip
    assert self_.status_code == 201 and self_.json()["data"]["assignee_id"] == str(emp)
    # MGR of another department cannot write
    foreign = await patch(api, f"/work/tasks/{mine['id']}", 2, role="MGR", title="z")
    assert foreign.status_code == 403
    mgr = await api.call("PATCH", f"/work/tasks/{mine['id']}", "MGR", department_id=other_dept,
                         json={"title": "z", "version": 2})  # fmt: skip
    assert mgr.status_code == 403 and mgr.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    # other tenant → 404
    assert (await api.call("GET", f"/work/tasks/{mine['id']}", "CEO",
                           tenant_id=TENANT_B)).status_code == 404  # fmt: skip


# ---------- TC-M13-03: sub-task, source_ref, dependencies ----------
def test_pure_rules() -> None:
    assert source_kind_matches("decision", "meeting") and source_kind_matches("ai_action", "ai")
    assert not source_kind_matches("document", "manual")
    assert find_cycle(2, 1, {2: [3], 3: [1]}) == [1, 2, 3, 1]
    assert find_cycle(2, 1, {2: [3]}) is None


async def test_subtask_one_level_and_source_ref(api: ApiClient) -> None:
    parent = await make_task(api)
    child = await make_task(api, parent_task_id=parent["id"])
    assert child["parent_task_id"] == parent["id"]
    got = (await api.call("GET", f"/work/tasks/{parent['id']}", "CEO")).json()["data"]
    assert got["subtask_count"] == 1
    grand = await api.call("POST", "/work/tasks", "CEO",
                           json={"title": "g", "parent_task_id": child["id"]})  # fmt: skip
    assert grand.status_code == 422
    other = await make_task(api)
    nest = await patch(api, f"/work/tasks/{parent['id']}", 1, parent_task_id=other["id"])
    assert nest.status_code == 422  # parent with sub-tasks cannot become a sub-task
    gone = await api.call("DELETE", f"/work/tasks/{parent['id']}", "CEO")
    assert gone.status_code == 422
    filt = await api.call("GET", "/work/tasks", "CEO", params={"parent_task_id": parent["id"]})
    assert [x["id"] for x in filt.json()["data"]] == [child["id"]]

    ref = {"kind": "document", "id": str(uuid.uuid4()), "page": 2}
    doc = await make_task(api, task_source="document", source_ref=ref)
    assert doc["source_ref"] == ref
    bad = await api.call("POST", "/work/tasks", "CEO",
                         json={"title": "b", "source_ref": ref})  # manual ≠ document  # fmt: skip
    assert bad.status_code == 422
    lst = await api.call("GET", "/work/tasks", "CEO",
                         params={"source_kind": "document", "limit": 100})  # fmt: skip
    assert doc["id"] in {x["id"] for x in lst.json()["data"]}
    assert all(x["source_ref"]["kind"] == "document" for x in lst.json()["data"])


async def test_dependencies(api: ApiClient, db_session: AsyncSession) -> None:
    ta, tb, tc = await make_task(api), await make_task(api), await make_task(api)
    url = "/work/tasks/{}/dependencies"
    ab = await api.call("POST", url.format(ta["id"]), "CEO", json={"depends_on_task_id": tb["id"]})
    assert ab.status_code == 201 and ab.json()["data"]["dependency_type"] == "finish_to_start"
    bc = await api.call("POST", url.format(tb["id"]), "CEO", json={"depends_on_task_id": tc["id"]})
    assert bc.status_code == 201
    dup = await api.call("POST", url.format(ta["id"]), "CEO", json={"depends_on_task_id": tb["id"]})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    selfd = await api.call("POST", url.format(ta["id"]), "CEO",
                           json={"depends_on_task_id": ta["id"]})  # fmt: skip
    assert selfd.status_code == 422
    loop = await api.call(
        "POST", url.format(tc["id"]), "CEO", json={"depends_on_task_id": ta["id"]}
    )
    assert loop.status_code == 422
    assert loop.json()["error"]["details"]["cycle"] == [tc["id"], ta["id"], tb["id"], tc["id"]]
    missing = await api.call("POST", url.format(ta["id"]), "CEO",
                             json={"depends_on_task_id": str(uuid.uuid4())})  # fmt: skip
    assert missing.status_code == 404

    lst = (await api.call("GET", url.format(tb["id"]), "CEO")).json()["data"]
    assert [x["task_id"] for x in lst["depends_on"]] == [tc["id"]]
    assert [x["task_id"] for x in lst["blocks"]] == [ta["id"]]
    assert (await api.call("GET", f"/work/tasks/{ta['id']}", "CEO")).json()["data"][
        "depends_on_open"
    ] == 1
    # restricted view for a reader outside scope of the other side
    emp, dept = uuid.uuid4(), uuid.uuid4()
    mine = await make_task(api, assignee_id=str(emp), department_id=str(dept))
    hidden = await make_task(api, department_id=str(uuid.uuid4()))
    await api.call("POST", url.format(mine["id"]), "CEO", json={"depends_on_task_id": hidden["id"]})
    view = await as_user(api, "GET", url.format(mine["id"]), "EMP", uuid.uuid4(), employee_id=emp)
    brief = view.json()["data"]["depends_on"][0]
    assert brief["task_id"] == hidden["id"] and brief["restricted"] is True
    assert brief["title"] is None

    # done gated by open blockers (R-DEC-43); in_progress allowed
    assert (await patch(api, f"/work/tasks/{ta['id']}", 1, status="in_progress")).status_code == 200
    blocked = await patch(api, f"/work/tasks/{ta['id']}", 2, status="done")
    assert blocked.status_code == 422
    assert blocked.json()["error"]["details"]["rule"] == "FR-TASK-02"
    assert (await patch(api, f"/work/tasks/{tb['id']}", 1, status="cancelled")).status_code == 200
    assert (await patch(api, f"/work/tasks/{ta['id']}", 2, status="done")).status_code == 200
    wrong = await patch(api, f"/work/tasks/{ta['id']}", 3, status="blocked", blocked_reason="x")
    assert wrong.status_code == 409  # DEC-147 transitions kept

    dep_id = bc.json()["data"]["id"]
    assert (await api.call("DELETE", f"/work/tasks/{ta['id']}/dependencies/{dep_id}",
                           "CEO")).status_code == 404  # fmt: skip
    assert (await api.call("DELETE", f"/work/tasks/{tb['id']}/dependencies/{dep_id}",
                           "CEO")).status_code == 204  # fmt: skip
    assert await audit_actions(db_session, dep_id) == [
        "execution.task_dependency_create", "execution.task_dependency_delete",
    ]  # fmt: skip
    # deleting a task soft-deletes its dependencies
    await api.call("DELETE", f"/work/tasks/{tc['id']}", "CEO")
    assert (await api.call("GET", url.format(tb["id"]), "CEO")).json()["data"]["depends_on"] == []

"""T-133 — EP-45 initiatives + milestones, system-computed progress (TC-EXE-005)."""

import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import ApiClient
from tests.integration.execution.helpers import (
    as_user,
    audit_actions,
    make,
    make_task,
    patch,
    uniq,
)

pytestmark = pytest.mark.integration


async def make_initiative(api: ApiClient, owner: Any, **kw: Any) -> dict[str, Any]:
    o = await make(api, "/execution/objectives", {
        "title": "o", "owner_id": str(owner), "period_key": "2037"})  # fmt: skip
    return await make(api, "/execution/initiatives", {
        "code": uniq("INI"), "title": "Mở chi nhánh Đà Nẵng", "objective_id": o["id"],
        "owner_id": str(owner), "start_date": "2037-01-01", "planned_end_date": "2037-12-31",
        "weight_pct": 30, "pillar": "S", **kw})  # fmt: skip


async def get(api: ApiClient, url: str) -> dict[str, Any]:
    return dict((await api.call("GET", url, "CEO")).json()["data"])


async def test_initiative_milestones_progress(api: ApiClient, db_session: AsyncSession) -> None:
    owner, dept = uuid.uuid4(), uuid.uuid4()
    ini = await make_initiative(api, owner, department_id=str(dept), status="active")
    iid = ini["id"]
    url = f"/execution/initiatives/{iid}"
    assert ini["progress_pct"] == 0 and ini["currency"] == "VND"
    # no milestones → task completion
    t1 = await make_task(api, initiative_id=iid, status="done")
    await make_task(api, initiative_id=iid)
    await make_task(api, initiative_id=iid, status="cancelled")
    assert (await get(api, url))["progress_pct"] == 50
    # milestones take over
    m1 = await make(api, f"{url}/milestones", {"title": "Thuê mặt bằng", "due_date": "2037-03-01"})
    m2 = await make(api, f"{url}/milestones", {"title": "Tuyển", "due_date": "2037-06-01",
                                               "status": "done"})  # fmt: skip
    assert m2["done_at"] is not None and m1["status"] == "planned"
    assert (await get(api, url))["progress_pct"] == 50
    up = await patch(api, f"{url}/milestones/{m1['id']}", 1, status="done", title=None)
    assert up.status_code == 200 and up.json()["data"]["done_at"] is not None
    assert (await get(api, url))["progress_pct"] == 100
    back = await patch(api, f"{url}/milestones/{m1['id']}", 2, status="missed")
    assert back.json()["data"]["done_at"] is None
    one = await api.call("GET", f"{url}/milestones/{m1['id']}", "CEO")
    assert one.status_code == 200
    lst = await api.call("GET", f"{url}/milestones", "CEO")
    assert lst.json()["meta"]["pagination"]["total"] == 2
    # task linked to milestone blocks deleting it
    tm = await make_task(api, milestone_id=m1["id"])
    assert (await api.call("DELETE", f"{url}/milestones/{m1['id']}", "CEO")).status_code == 409
    await api.call("DELETE", f"/work/tasks/{tm['id']}", "CEO")
    assert (await api.call("DELETE", f"{url}/milestones/{m1['id']}", "CEO")).status_code == 204
    assert (await get(api, url))["progress_pct"] == 100
    assert (await api.call("GET", f"{url}/milestones/{m1['id']}", "CEO")).status_code == 404
    other = await make_initiative(api, owner)
    cross = await api.call("GET", f"/execution/initiatives/{other['id']}/milestones/{m2['id']}",
                           "CEO")  # fmt: skip
    assert cross.status_code == 404
    # initiative still referenced
    assert (await api.call("DELETE", url, "CEO")).status_code == 409
    # moving a task off the initiative recomputes both
    mv = await patch(api, f"/work/tasks/{t1['id']}", 1, initiative_id=other["id"])
    assert mv.status_code == 200
    assert (await get(api, f"/execution/initiatives/{other['id']}"))["progress_pct"] == 100
    acts = await audit_actions(db_session, m1["id"])
    assert "execution.milestone_delete" in acts and "execution.milestone_create" in acts


async def test_initiative_crud_scope_filters(api: ApiClient, db_session: AsyncSession) -> None:
    owner, dept = uuid.uuid4(), uuid.uuid4()
    ini = await make_initiative(api, owner, department_id=str(dept), budget_amount=10**9)
    iid = ini["id"]
    dup = await api.call("POST", "/execution/initiatives", "CEO", json={
        "code": ini["code"], "title": "x", "objective_id": ini["objective_id"],
        "owner_id": str(owner), "start_date": "2037-01-01",
        "planned_end_date": "2037-02-01"})  # fmt: skip
    assert dup.status_code == 409
    bad = await api.call("POST", "/execution/initiatives", "CEO", json={
        "code": uniq("INI"), "title": "x", "objective_id": str(uuid.uuid4()),
        "owner_id": str(owner), "start_date": "2037-01-01",
        "planned_end_date": "2037-02-01"})  # fmt: skip
    assert bad.status_code == 422
    rev = await patch(api, f"/execution/initiatives/{iid}", 1, planned_end_date="2036-01-01")
    assert rev.status_code == 422
    up = await patch(api, f"/execution/initiatives/{iid}", 1, status="at_risk", code=uniq("INI"),
                     title=None, weight_pct=40)  # fmt: skip
    assert up.status_code == 200 and up.json()["data"]["weight_pct"] == 40
    flt = await api.call("GET", "/execution/initiatives", "MANAGER", department_id=dept, params={
        "objective_id": ini["objective_id"], "status": "at_risk", "pillar": "S"})  # fmt: skip
    assert [x["id"] for x in flt.json()["data"]] == [iid]
    assert (await as_user(api, "GET", f"/execution/initiatives/{iid}", "EMP",
                          owner)).status_code == 200  # fmt: skip
    stranger = await as_user(api, "GET", f"/execution/initiatives/{iid}/milestones",
                             "EMP", uuid.uuid4())  # fmt: skip
    assert stranger.status_code == 403
    mgr = await patch(api, f"/execution/initiatives/{iid}", 2, role="MANAGER",
                      department_id=str(uuid.uuid4()))  # fmt: skip
    assert mgr.status_code == 403
    assert (await api.call("DELETE", f"/execution/initiatives/{iid}", "CEO")).status_code == 204
    assert (await api.call("GET", f"/execution/initiatives/{iid}", "CEO")).status_code == 404
    assert "execution.initiative_delete" in await audit_actions(db_session, iid)

"""T-131 — EP-42 meetings, EP-43 decisions, EP-45 projects (TC-EXE-001)."""

import uuid

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
HELD = "2037-06-01T09:00:00Z"


async def test_meeting_decision_task_chain(api: ApiClient, db_session: AsyncSession) -> None:
    dept, me = uuid.uuid4(), uuid.uuid4()
    m = await make(api, "/execution/meetings", {
        "title": "Giao ban", "held_at": HELD, "attendee_ids": [str(me)],
        "department_id": str(dept), "summary": "s"})  # fmt: skip
    assert m["attendee_ids"] == [str(me)] and m["transcript_id"] is None
    d = await make(api, "/execution/decisions", {
        "meeting_id": m["id"], "content": "Mở chi nhánh", "decided_at": HELD,
        "alternatives_rejected": "Không mở", "owner_id": str(me)})  # fmt: skip
    assert d["review_at"] == ["2037-07-01", "2037-07-31", "2037-08-30"]
    assert d["status"] == "open" and d["done_at"] is None
    t = await make_task(api, meeting_id=m["id"], decision_id=d["id"], task_source="meeting")
    assert t["decision_id"] == d["id"]
    up = await patch(api, f"/execution/decisions/{d['id']}", 1, status="done",
                     actual_outcome="ok", content=None)  # fmt: skip
    assert up.status_code == 200 and up.json()["data"]["done_at"] is not None
    blocked = await api.call("DELETE", f"/execution/meetings/{m['id']}", "CEO")
    assert blocked.status_code == 409
    mu = await patch(api, f"/execution/meetings/{m['id']}", 1, title="Giao ban T6", held_at=None)
    assert mu.status_code == 200 and mu.json()["data"]["title"] == "Giao ban T6"
    tr = await patch(api, f"/execution/meetings/{m['id']}", 2, transcript_id=str(uuid.uuid4()))
    assert tr.status_code == 422
    # filters
    lst = await api.call("GET", "/execution/meetings", "CEO", params={
        "from": "2037-05-31T00:00:00Z", "to": "2037-06-02T00:00:00Z",
        "department_id": str(dept)})  # fmt: skip
    assert [x["id"] for x in lst.json()["data"]] == [m["id"]]
    dl = await api.call("GET", "/execution/decisions", "CEO",
                        params={"meeting_id": m["id"], "status": "done"})  # fmt: skip
    assert [x["id"] for x in dl.json()["data"]] == [d["id"]]
    for flag in ("true", "false"):
        r = await api.call("GET", "/execution/decisions", "CEO",
                           params={"meeting_id": m["id"], "review_due": flag})  # fmt: skip
        assert r.status_code == 200
    # EMPLOYEE attendee sees the meeting + own decision; MANAGER of dept sees decision
    assert (await as_user(api, "GET", f"/execution/meetings/{m['id']}", "EMP",
                          me)).status_code == 200  # fmt: skip
    md = await api.call("GET", "/execution/decisions", "MANAGER", department_id=dept,
                        params={"meeting_id": m["id"]})  # fmt: skip
    assert [x["id"] for x in md.json()["data"]] == [d["id"]]
    other = await api.call("GET", f"/execution/decisions/{d['id']}", "MANAGER",
                           department_id=uuid.uuid4())  # fmt: skip
    assert other.status_code == 403
    me_d = await as_user(api, "GET", "/execution/decisions", "EMP", me)
    assert [x["id"] for x in me_d.json()["data"]] == [d["id"]]
    await api.call("DELETE", f"/execution/tasks/{t['id']}", "CEO")
    assert "execution.decision_update" in await audit_actions(db_session, d["id"])


async def test_meeting_and_decision_rules(api: ApiClient) -> None:
    me = uuid.uuid4()
    m = await as_user(api, "POST", "/execution/meetings", "EMP", me,
                      json={"title": "1:1", "held_at": HELD})  # fmt: skip
    assert m.status_code == 201 and m.json()["data"]["chair_id"] == str(me)
    mid = m.json()["data"]["id"]
    foreign = await as_user(api, "POST", "/execution/meetings", "EMP", me, json={
        "title": "x", "held_at": HELD, "chair_id": str(uuid.uuid4())})  # fmt: skip
    assert foreign.status_code == 403
    tr = await api.call("POST", "/execution/meetings", "CEO", json={
        "title": "x", "held_at": HELD, "transcript_id": str(uuid.uuid4())})  # fmt: skip
    assert tr.status_code == 422
    nf_meeting = await api.call("POST", "/execution/decisions", "CEO", json={
        "content": "x", "decided_at": HELD, "meeting_id": str(uuid.uuid4())})  # fmt: skip
    assert nf_meeting.status_code == 422
    own = await as_user(api, "POST", "/execution/decisions", "EMP", me, json={
        "content": "x", "decided_at": HELD, "meeting_id": mid, "status": "done",
        "review_at": ["2037-09-01"]})  # fmt: skip
    assert own.status_code == 201, own.text
    od = own.json()["data"]
    assert od["owner_id"] == str(me) and od["review_at"] == ["2037-09-01"] and od["done_at"]
    other_owner = await as_user(api, "PATCH", f"/execution/decisions/{od['id']}", "EMP",
                                me, json={"owner_id": str(uuid.uuid4()), "version": 1})  # fmt: skip
    assert other_owner.status_code == 403
    deleted = await as_user(api, "DELETE", f"/execution/meetings/{mid}", "EMP", me)
    assert deleted.status_code == 409
    lonely = await make(api, "/execution/meetings", {"title": "y", "held_at": HELD})
    assert (await api.call("DELETE", f"/execution/meetings/{lonely['id']}", "CEO")).status_code \
        == 204  # fmt: skip
    assert (await api.call("GET", f"/execution/meetings/{lonely['id']}", "CEO")).status_code \
        == 404  # fmt: skip
    nf = await api.call("GET", f"/execution/decisions/{uuid.uuid4()}", "CEO")
    assert nf.status_code == 404
    no_dept_mgr = await api.call("GET", "/execution/decisions", "MANAGER")
    assert no_dept_mgr.status_code == 200
    dept = uuid.uuid4()
    moved = await patch(api, f"/execution/meetings/{mid}", 1, department_id=str(dept))
    assert moved.status_code == 200 and moved.json()["data"]["department_id"] == str(dept)


async def test_project_crud(api: ApiClient, db_session: AsyncSession) -> None:
    dept, owner = uuid.uuid4(), uuid.uuid4()
    body = {"code": uniq("PRJ"), "name": "ABC Order v3", "owner_id": str(owner),
            "department_id": str(dept), "start_date": "2037-01-01", "due_date": "2037-06-30",
            "status": "active", "budget_amount": 500_000_000}  # fmt: skip
    p = await make(api, "/execution/projects", body)
    assert p["due_date"] == "2037-06-30" and p["currency"] == "VND"
    dup = await api.call("POST", "/execution/projects", "CEO", json=body)
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    bad = await api.call("POST", "/execution/projects", "CEO",
                         json={**body, "code": uniq("PRJ"), "due_date": "2036-01-01"})  # fmt: skip
    assert bad.status_code == 422
    up = await patch(api, f"/execution/projects/{p['id']}", 1, due_date="2037-07-31",
                     status="on_hold", code=uniq("PRJ"), name=None)  # fmt: skip
    assert up.status_code == 200 and up.json()["data"]["due_date"] == "2037-07-31"
    p2 = await make(api, "/execution/projects", {**body, "code": uniq("PRJ")})
    clash = await patch(api, f"/execution/projects/{p2['id']}", 1, code=up.json()["data"]["code"])
    assert clash.status_code == 409
    lst = await api.call("GET", "/execution/projects", "MANAGER", department_id=dept,
                         params={"status": "on_hold", "department_id": str(dept)})  # fmt: skip
    assert [x["id"] for x in lst.json()["data"]] == [p["id"]]
    assert (await as_user(api, "GET", f"/execution/projects/{p['id']}", "EMP",
                          owner)).status_code == 200  # fmt: skip
    assert (await as_user(api, "GET", f"/execution/projects/{p['id']}", "EMP",
                          uuid.uuid4())).status_code == 403  # fmt: skip
    t = await make_task(api, project_id=p["id"])
    assert (await api.call("DELETE", f"/execution/projects/{p['id']}", "CEO")).status_code == 409
    await api.call("DELETE", f"/execution/tasks/{t['id']}", "CEO")
    mv = await patch(api, f"/execution/projects/{p['id']}", 2, department_id=str(uuid.uuid4()),
                     role="MANAGER")  # fmt: skip
    assert mv.status_code == 403
    assert (await api.call("DELETE", f"/execution/projects/{p['id']}", "CEO")).status_code == 204
    assert (await api.call("GET", f"/execution/projects/{p['id']}", "CEO")).status_code == 404
    acts = await audit_actions(db_session, p["id"])
    assert acts == ["execution.project_create", "execution.project_delete",
                    "execution.project_update"]  # fmt: skip

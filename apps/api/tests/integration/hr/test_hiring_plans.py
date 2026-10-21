"""T-122 — EP-84 hiring plans, EP-85 submit, EP-86 approve + delay job (TC-HR-002, TC-HR-003)."""

import uuid
from datetime import date, timedelta
from typing import Any

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import HiringPlan
from app.modules.hr.services.hiring_service import detect_delayed_hiring_plans
from tests.conftest import ApiClient
from tests.integration.hr.helpers import audit_rows, events, make_department

pytestmark = pytest.mark.integration


def plan_body(dept: str, **kw: Any) -> dict[str, Any]:
    return {
        "department_id": dept, "position": "Kỹ sư bảo trì", "headcount": 3,
        "salary_min": 15_000_000, "salary_max": 25_000_000, "start_date": "2026-08-01",
        "target_date": "2026-09-30", "priority": "high", "budget_amount": 900_000_000, **kw,
    }  # fmt: skip


async def make_plan(api: ApiClient, dept: str, **kw: Any) -> dict[str, Any]:
    r = await api.call("POST", "/hr/hiring-plans", "HR_MANAGER", json=plan_body(dept, **kw))
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


async def approved_plan(api: ApiClient, dept: str, **kw: Any) -> dict[str, Any]:
    p = await make_plan(api, dept, **kw)
    assert (await api.call("POST", f"/hr/hiring-plans/{p['id']}/submit", "HR_MANAGER")).is_success
    r = await api.call("POST", f"/hr/hiring-plans/{p['id']}/approve", "CFO",
                       json={"decision": "approve", "reason": "Đủ ngân sách"})  # fmt: skip
    assert r.status_code == 200, r.text
    return dict(r.json()["data"])


async def test_plan_crud_and_validation(api: ApiClient, db_session: AsyncSession) -> None:
    dept = (await make_department(api))["id"]
    p = await make_plan(api, dept)
    assert p["status"] == "draft" and p["title"] == "Kỹ sư bảo trì" and p["filled"] == 0
    assert p["target_date"] == "2026-09-30" and p["budget_amount"] == 900_000_000

    for bad in ({"headcount": 0}, {"salary_max": 1}, {"target_date": "2026-07-01"},
                {"filled": 5}, {"department_id": str(uuid.uuid4())}):  # fmt: skip
        r = await api.call("POST", "/hr/hiring-plans", "HR_MANAGER", json=plan_body(dept, **bad))
        assert r.status_code == 422, bad

    u = await api.call(
        "PATCH",
        f"/hr/hiring-plans/{p['id']}",
        "HR_MANAGER",
        json={"headcount": 4, "salary_min": 16_000_000, "version": 1},
    )
    assert u.status_code == 200 and u.json()["data"]["headcount"] == 4
    for bad in ({"salary_min": 30_000_000}, {"target_date": "2026-07-01"}, {"filled": 9},
                {"department_id": str(uuid.uuid4())}):  # fmt: skip
        r = await api.call("PATCH", f"/hr/hiring-plans/{p['id']}", "HR_MANAGER",
                           json={**bad, "version": 2})  # fmt: skip
        assert r.status_code == 422, bad
    stale = await api.call("PATCH", f"/hr/hiring-plans/{p['id']}", "HR_MANAGER",
                           json={"headcount": 2, "version": 1})  # fmt: skip
    assert stale.status_code == 409

    g = await api.call("GET", f"/hr/hiring-plans/{p['id']}", "CEO")
    assert g.status_code == 200 and g.json()["data"]["version"] == 2
    assert (await api.call("GET", f"/hr/hiring-plans/{uuid.uuid4()}", "CEO")).status_code == 404
    assert (
        await api.call("DELETE", f"/hr/hiring-plans/{p['id']}", "HR_MANAGER")
    ).status_code == 204
    assert (await api.call("GET", f"/hr/hiring-plans/{p['id']}", "CEO")).status_code == 404
    actions = sorted(a for a, *_ in await audit_rows(db_session, p["id"]))
    assert actions == ["hr.hiring_plan_create", "hr.hiring_plan_delete", "hr.hiring_plan_update"]


async def test_submit_approve_reject_state_machine(
    api: ApiClient, db_session: AsyncSession
) -> None:
    dept = (await make_department(api))["id"]
    p = await make_plan(api, dept)
    url = f"/hr/hiring-plans/{p['id']}"
    early = await api.call("POST", f"{url}/approve", "CFO",
                           json={"decision": "approve", "reason": "ok"})  # fmt: skip
    assert early.status_code == 409 and early.json()["error"]["code"] == "CONFLICT_STATE"

    s = await api.call("POST", f"{url}/submit", "HR_MANAGER")
    assert s.status_code == 200 and s.json()["data"]["status"] == "submitted"
    again = await api.call("POST", f"{url}/submit", "HR_MANAGER")
    assert again.status_code == 409
    locked = await api.call("PATCH", url, "HR_MANAGER", json={"headcount": 9, "version": 2})
    assert locked.status_code == 409

    no_reason = await api.call("POST", f"{url}/approve", "CFO", json={"decision": "reject"})
    assert no_reason.status_code == 422
    blank = await api.call("POST", f"{url}/approve", "CFO",
                           json={"decision": "reject", "reason": "   "})  # fmt: skip
    assert blank.status_code == 422
    for role in ("HR_MANAGER", "CEO", "MANAGER"):
        r = await api.call("POST", f"{url}/approve", role,
                           json={"decision": "approve", "reason": "x"})  # fmt: skip
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_ROLE", role

    rej = await api.call("POST", f"{url}/approve", "CFO",
                         json={"decision": "reject", "reason": "Chưa có ngân sách"})  # fmt: skip
    assert rej.status_code == 200
    d = rej.json()["data"]
    assert d["status"] == "rejected" and d["reject_reason"] == "Chưa có ngân sách"
    assert d["approved_by"] is not None

    back = await api.call(
        "PATCH",
        url,
        "HR_MANAGER",
        json={"status": "draft", "headcount": 2, "version": d["version"]},
    )
    assert back.status_code == 200 and back.json()["data"]["reject_reason"] is None
    v = back.json()["data"]["version"]
    assert (await api.call("POST", f"{url}/submit", "HR_MANAGER")).status_code == 200
    ok = await api.call("POST", f"{url}/approve", "CFO",
                        json={"decision": "approve", "reason": "Duyệt"})  # fmt: skip
    assert ok.status_code == 200 and ok.json()["data"]["status"] == "approved"
    v = ok.json()["data"]["version"]
    assert v > 3

    illegal = await api.call("PATCH", url, "HR_MANAGER", json={"status": "completed", "version": v})
    assert illegal.status_code == 409
    content = await api.call("PATCH", url, "HR_MANAGER", json={"position": "x", "version": v})
    assert content.status_code == 409
    nodel = await api.call("DELETE", url, "HR_MANAGER")
    assert nodel.status_code == 409
    prog = await api.call("PATCH", url, "HR_MANAGER",
                          json={"status": "in_progress", "filled": 1, "budget_spent": 5,
                                "version": v})  # fmt: skip
    assert prog.status_code == 200 and prog.json()["data"]["filled"] == 1
    done = await api.call(
        "PATCH", url, "HR_MANAGER", json={"status": "completed", "version": v + 1}
    )
    assert done.status_code == 200
    frozen = await api.call("PATCH", url, "HR_MANAGER", json={"filled": 2, "version": v + 2})
    assert frozen.status_code == 409
    actions = {a for a, *_ in await audit_rows(db_session, p["id"])}
    assert {"hr.hiring_plan_submit", "hr.hiring_plan_reject", "hr.hiring_plan_approve"} <= actions


async def test_approver_must_differ_and_cancel(api: ApiClient) -> None:
    dept = (await make_department(api))["id"]
    creator = uuid.uuid4()
    r = await api.http.post(
        "/api/v1/hr/hiring-plans",
        json=plan_body(dept),
        headers=api.headers("HR_MANAGER", user_id=creator, idem=True),
    )
    pid = r.json()["data"]["id"]
    await api.http.post(
        f"/api/v1/hr/hiring-plans/{pid}/submit",
        headers=api.headers("HR_MANAGER", user_id=creator, idem=True),
    )
    same = await api.http.post(
        f"/api/v1/hr/hiring-plans/{pid}/approve",
        json={"decision": "approve", "reason": "x"},
        headers=api.headers("CFO", user_id=creator, idem=True),
    )
    assert same.status_code == 422 and same.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    missing = await api.call("POST", f"/hr/hiring-plans/{uuid.uuid4()}/approve", "CFO",
                             json={"decision": "approve", "reason": "x"})  # fmt: skip
    assert missing.status_code == 404

    draft = await make_plan(api, dept)
    c = await api.call("PATCH", f"/hr/hiring-plans/{draft['id']}", "HR_MANAGER",
                       json={"status": "cancelled", "version": 1})  # fmt: skip
    assert c.status_code == 200
    dead = await api.call("PATCH", f"/hr/hiring-plans/{draft['id']}", "HR_MANAGER",
                          json={"filled": 1, "version": 2})  # fmt: skip
    assert dead.status_code == 409
    gone = await api.call("DELETE", f"/hr/hiring-plans/{draft['id']}", "HR_MANAGER")
    assert gone.status_code == 204


async def test_plan_list_filters_and_scope(api: ApiClient) -> None:
    mine, other = (await make_department(api))["id"], (await make_department(api))["id"]
    late = await approved_plan(api, mine, start_date="2026-01-01", target_date="2026-02-01")
    fresh = await make_plan(api, mine, start_date="2099-01-01", target_date="2099-06-01")
    foreign = await make_plan(api, other)
    r = await api.call("GET", "/hr/hiring-plans", "CEO",
                       params={"department_id": mine, "delayed": "true"})  # fmt: skip
    assert [x["id"] for x in r.json()["data"]] == [late["id"]]
    r = await api.call("GET", "/hr/hiring-plans", "CEO",
                       params={"department_id": mine, "delayed": "false", "status": "draft",
                               "sort_by": "target_date"})  # fmt: skip
    assert [x["id"] for x in r.json()["data"]] == [fresh["id"]]

    dep = uuid.UUID(mine)
    m = await api.call("GET", "/hr/hiring-plans", "MANAGER", department_id=dep)
    ids = {x["id"] for x in m.json()["data"]}
    assert late["id"] in ids and foreign["id"] not in ids
    deny = await api.call("GET", f"/hr/hiring-plans/{foreign['id']}", "MANAGER", department_id=dep)
    assert deny.status_code == 403
    assert (await api.call("GET", "/hr/hiring-plans", "REVIEWER")).status_code == 403

    emp_id = uuid.uuid4()
    own = await make_plan(api, other, hiring_manager_id=str(emp_id))
    eh = api.headers("EMPLOYEE", user_id=emp_id)
    lst = await api.http.get("/api/v1/hr/hiring-plans", headers=eh)
    assert [x["id"] for x in lst.json()["data"]] == [own["id"]]
    assert (
        await api.http.get(f"/api/v1/hr/hiring-plans/{own['id']}", headers=eh)
    ).status_code == 200
    assert (await api.http.get(f"/api/v1/hr/hiring-plans/{foreign['id']}",
                               headers=eh)).status_code == 403  # fmt: skip


async def test_idempotent_plan_actions(api: ApiClient) -> None:
    dept = (await make_department(api))["id"]
    p = await make_plan(api, dept)
    h = api.headers("HR_MANAGER", idem=True)
    s1 = await api.http.post(f"/api/v1/hr/hiring-plans/{p['id']}/submit", headers=h)
    s2 = await api.http.post(f"/api/v1/hr/hiring-plans/{p['id']}/submit", headers=h)
    assert s1.status_code == s2.status_code == 200
    assert s1.json()["data"]["version"] == s2.json()["data"]["version"]
    body = {"decision": "approve", "reason": "ok"}
    ha = api.headers("CFO", idem=True)
    a1 = await api.http.post(f"/api/v1/hr/hiring-plans/{p['id']}/approve", json=body, headers=ha)
    a2 = await api.http.post(f"/api/v1/hr/hiring-plans/{p['id']}/approve", json=body, headers=ha)
    assert a1.status_code == a2.status_code == 200
    hc = api.headers("HR_MANAGER", idem=True)
    b = plan_body(dept)
    c1 = await api.http.post("/api/v1/hr/hiring-plans", json=b, headers=hc)
    c2 = await api.http.post("/api/v1/hr/hiring-plans", json=b, headers=hc)
    assert c1.json()["data"]["id"] == c2.json()["data"]["id"]


# ---------- TC-HR-003: FR-HR-04 delay job ----------
async def test_delayed_detection_once_per_plan(api: ApiClient, db_session: AsyncSession) -> None:
    dept = (await make_department(api))["id"]
    as_of = date(2031, 6, 30)
    late = await approved_plan(api, dept, start_date="2031-01-01", target_date="2031-05-01")
    edge = await approved_plan(api, dept, start_date="2031-01-01", target_date="2031-05-31")
    filled = await approved_plan(api, dept, start_date="2031-01-01", target_date="2031-04-01",
                                 headcount=1)  # fmt: skip
    await db_session.execute(
        update(HiringPlan).where(HiringPlan.id == uuid.UUID(filled["id"])).values(filled=1)
    )
    draft = await make_plan(api, dept, start_date="2031-01-01", target_date="2031-03-01")

    found = await detect_delayed_hiring_plans(db_session, as_of)
    mine = [f for f in found if str(f.department_id) == dept]
    assert [str(f.hiring_plan_id) for f in mine] == [late["id"]]
    assert mine[0].days_late == 60 and mine[0].unfilled == 3

    evs = await events(db_session, late["id"], "hr.hiring_plan_delayed")
    assert len(evs) == 1
    assert evs[0][1] == {"hiring_plan_id": late["id"], "department_id": dept,
                         "days_late": 60, "unfilled": 3}  # fmt: skip
    for other in (edge, filled, draft):
        assert await events(db_session, other["id"]) == []

    again = await detect_delayed_hiring_plans(db_session, as_of + timedelta(days=5))
    assert late["id"] not in {str(f.hiring_plan_id) for f in again}
    assert {str(f.hiring_plan_id) for f in again if str(f.department_id) == dept} == {edge["id"]}
    assert len(await events(db_session, late["id"], "hr.hiring_plan_delayed")) == 1
    row = (await db_session.execute(
        select(HiringPlan.delayed_notified_at).where(HiringPlan.id == uuid.UUID(late["id"]))
    )).scalar_one()  # fmt: skip
    assert row is not None

    # moving the milestone re-arms the notification (new target date)
    plan = (await api.call("GET", f"/hr/hiring-plans/{late['id']}", "CEO")).json()["data"]
    await db_session.execute(
        update(HiringPlan).where(HiringPlan.id == uuid.UUID(late["id"])).values(status="rejected")
    )
    moved = await api.call(
        "PATCH",
        f"/hr/hiring-plans/{late['id']}",
        "HR_MANAGER",
        json={"target_date": "2031-05-10", "version": plan["version"]},
    )
    assert moved.status_code == 200, moved.text
    await db_session.execute(
        update(HiringPlan).where(HiringPlan.id == uuid.UUID(late["id"])).values(status="approved")
    )
    third = await detect_delayed_hiring_plans(db_session, as_of + timedelta(days=5))
    assert late["id"] in {str(f.hiring_plan_id) for f in third}
    assert len(await events(db_session, late["id"], "hr.hiring_plan_delayed")) == 2

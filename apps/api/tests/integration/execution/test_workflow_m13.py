"""TC-M13-06/07/08 (T-622, R-DEC-45) — approval inbox, decide on the new path, task_reassign.

EP-WF-01 `assigned_to=me` = PENDING ∩ caller role in the current step ∩ scope (MGR = own
department, CEO all), never the caller's own requests. EP-TASK-19 opens `RULE-task_reassign`
requests; the final approve applies the reassignment in the same tx (hook `task_reassign`).
"""

import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.platform.services.approval_service import (
    RULE_SINGLE,
    RULE_TASK_REASSIGN,
    RULE_TWO_SIDED,
    ApprovalService,
)
from tests.conftest import ApiClient
from tests.integration.execution.helpers import as_user, make_task, outbox_for, patch

pytestmark = pytest.mark.integration

WF = "/workflow/approval-requests"


async def _emp_task(api: ApiClient, dept: uuid.UUID) -> tuple[dict[str, Any], uuid.UUID]:
    emp = uuid.uuid4()
    t = await make_task(api, department_id=str(dept), assignee_id=str(emp))
    return t, emp


async def _reassign(
    api: ApiClient, t: dict[str, Any], emp: uuid.UUID, dept: uuid.UUID, to: uuid.UUID | None = None
) -> Any:
    body = {"to_assignee_id": str(to or uuid.uuid4()), "reason": "quá tải"}
    return await as_user(api, "POST", f"/work/tasks/{t['id']}/reassign-requests", "EMP", emp,
                         department_id=dept, employee_id=emp, json=body)  # fmt: skip


async def _inbox(api: ApiClient, role: str, user: uuid.UUID, dept: Any = None, **p: Any) -> Any:
    return await as_user(api, "GET", WF, role, user, department_id=dept,
                         params={"limit": 100, **p})  # fmt: skip


def _ids(r: Any) -> set[str]:
    return {x["id"] for x in r.json()["data"]}


async def test_reassign_flow_approve(api: ApiClient, db_session: AsyncSession) -> None:
    dept = uuid.uuid4()
    t, emp = await _emp_task(api, dept)
    to = uuid.uuid4()
    r = await _reassign(api, t, emp, dept, to)
    assert r.status_code == 201, r.text
    req = r.json()["data"]
    assert (req["rule_code"], req["target_kind"], req["status"]) == (
        RULE_TASK_REASSIGN, "task_reassign", "PENDING")  # fmt: skip
    assert req["department_id"] == str(dept) and req["target_id"] == t["id"]
    assert req["title_key"] == "approval.task_reassign.title"
    assert req["params"]["to_assignee_id"] == str(to)
    ev = [p for e, p in await outbox_for(db_session, req["id"])]
    assert ev[0]["rule_code"] == RULE_TASK_REASSIGN and ev[0]["department_id"] == str(dept)

    dup = await _reassign(api, t, emp, dept)
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "CONFLICT_STATE"
    auth = {"Authorization": api.headers("EMP")["Authorization"]}
    no_idem = await api.http.post(f"/api/v1/work/tasks/{t['id']}/reassign-requests",
                                  json={"to_assignee_id": str(to), "reason": "x"},
                                  headers=auth)  # fmt: skip
    assert no_idem.status_code == 400

    # inbox: MGR of the department sees it; MGR elsewhere / requester / EMP do not
    mgr = uuid.uuid4()
    mine = await _inbox(api, "MGR", mgr, dept)
    assert req["id"] in _ids(mine) and mine.json()["meta"]["pending_count"] >= 1
    assert req["id"] not in _ids(await _inbox(api, "MGR", uuid.uuid4(), uuid.uuid4()))
    assert req["id"] in _ids(await _inbox(api, "CEO", uuid.uuid4()))
    assert req["id"] not in _ids(await _inbox(api, "DIR", uuid.uuid4()))  # rule = MGR only
    emp_inbox = await _inbox(api, "EMP", emp, dept)
    assert emp_inbox.status_code == 403 and emp_inbox.json()["error"]["code"] == "FORBIDDEN_ROLE"
    for role in ("REV", "ADM"):
        assert (await _inbox(api, role, uuid.uuid4())).status_code == 403
    flt = await _inbox(api, "MGR", mgr, dept, rule_code=RULE_SINGLE)
    assert req["id"] not in _ids(flt)
    assert req["id"] in _ids(await _inbox(api, "MGR", mgr, dept, target_kind="task_reassign"))

    det = await as_user(api, "GET", f"{WF}/{req['id']}", "MGR", mgr, department_id=dept)
    body = det.json()["data"]
    assert body["payload_diff"] == [{"field": "assignee_id", "before": str(emp),
                                     "after": str(to)}]  # fmt: skip
    assert body["timeline"][0]["decision"] == "requested"
    hidden = await as_user(api, "GET", f"{WF}/{req['id']}", "MGR", uuid.uuid4(),
                           department_id=uuid.uuid4())  # fmt: skip
    assert hidden.status_code == 404

    other_mgr = await as_user(api, "POST", f"{WF}/{req['id']}/decide", "MGR", uuid.uuid4(),
                              department_id=uuid.uuid4(), json={"decision": "approve"})  # fmt: skip
    assert other_mgr.status_code == 403 and other_mgr.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    ok = await as_user(api, "POST", f"{WF}/{req['id']}/decide", "MGR", mgr, department_id=dept,
                       json={"decision": "approve"})  # fmt: skip
    assert ok.status_code == 200 and ok.json()["data"]["status"] == "APPROVED"
    after = (await api.call("GET", f"/work/tasks/{t['id']}", "CEO")).json()["data"]
    assert after["assignee_id"] == str(to) and after["version"] == 2
    decided = [p for e, p in await outbox_for(db_session, req["id"])
               if e == "platform.approval_decided"]  # fmt: skip
    assert decided == [{"approval_request_id": req["id"], "rule_code": RULE_TASK_REASSIGN,
                        "target_kind": "task_reassign", "step": 1, "decision": "approve",
                        "status": "APPROVED"}]  # fmt: skip
    again = await as_user(api, "POST", f"{WF}/{req['id']}/decide", "MGR", mgr,
                          department_id=dept, json={"decision": "approve"})  # fmt: skip
    assert again.status_code == 409


async def test_reassign_version_conflict_reject_and_rules(api: ApiClient) -> None:
    dept = uuid.uuid4()
    t, emp = await _emp_task(api, dept)
    req = (await _reassign(api, t, emp, dept)).json()["data"]
    assert (await patch(api, f"/work/tasks/{t['id']}", 1, title="moved")).status_code == 200
    mgr = uuid.uuid4()
    stale = await as_user(api, "POST", f"{WF}/{req['id']}/decide", "MGR", mgr,
                          department_id=dept, json={"decision": "approve"})  # fmt: skip
    assert stale.status_code == 409
    still = await as_user(api, "GET", f"{WF}/{req['id']}", "MGR", mgr, department_id=dept)
    assert still.json()["data"]["status"] == "PENDING"
    no_reason = await as_user(api, "POST", f"{WF}/{req['id']}/decide", "MGR", mgr,
                              department_id=dept, json={"decision": "reject"})  # fmt: skip
    assert no_reason.status_code == 422
    rej = await as_user(api, "POST", f"{WF}/{req['id']}/decide", "MGR", mgr, department_id=dept,
                        json={"decision": "reject", "reason": "không"})  # fmt: skip
    assert rej.json()["data"]["status"] == "REJECTED"
    task = (await api.call("GET", f"/work/tasks/{t['id']}", "CEO")).json()["data"]
    assert task["assignee_id"] == str(emp)
    tl = (await as_user(api, "GET", f"{WF}/{req['id']}", "EMP", emp)).status_code
    assert tl == 403  # EMP lacks platform:approve

    # MGR in scope reassigns directly → 422; out of scope → 403; closed task → 409
    direct = await as_user(api, "POST", f"/work/tasks/{t['id']}/reassign-requests", "MGR",
                           mgr, department_id=dept,
                           json={"to_assignee_id": str(uuid.uuid4()), "reason": "x"})  # fmt: skip
    assert direct.status_code == 422
    assert direct.json()["error"]["details"]["reason"] == "direct_reassign_allowed"
    away = await as_user(api, "POST", f"/work/tasks/{t['id']}/reassign-requests", "MGR",
                         uuid.uuid4(), department_id=uuid.uuid4(),
                         json={"to_assignee_id": str(uuid.uuid4()), "reason": "x"})  # fmt: skip
    assert away.status_code == 403
    t2, emp2 = await _emp_task(api, dept)
    await patch(api, f"/work/tasks/{t2['id']}", 1, status="cancelled")
    assert (await _reassign(api, t2, emp2, dept)).status_code == 409
    other = await as_user(api, "POST", f"/work/tasks/{t2['id']}/reassign-requests", "EMP",
                          uuid.uuid4(), department_id=dept,
                          json={"to_assignee_id": str(uuid.uuid4()), "reason": "x"})  # fmt: skip
    assert other.status_code == 404  # not my task → read out of scope


async def test_rules_read_from_db(db_session: AsyncSession) -> None:
    svc = ApprovalService(db_session)
    single = await svc.rule(RULE_SINGLE)
    two = await svc.rule(RULE_TWO_SIDED)
    reassign = await svc.rule(RULE_TASK_REASSIGN)
    assert (single.approver_role_codes, single.second_approver_role_codes) == (["CEO", "DIR"], None)
    assert (two.approver_role_codes, two.second_approver_role_codes) == (["CEO"], ["DIR"])
    assert (reassign.target_kind, reassign.approver_role_codes, reassign.escalate_to_role_code,
            reassign.sla_hours) == ("task_reassign", ["MGR"], "DIR", 8)  # fmt: skip
    assert await svc.approver_roles(RULE_TASK_REASSIGN) == (("MGR",), "DIR")


async def test_ai_action_requests_on_new_path(api: ApiClient, db_session: AsyncSession) -> None:
    svc = ApprovalService(db_session)
    requester = uuid.uuid4()
    req = await svc.create_for_ai_action(
        ai_action_id=uuid.uuid4(), requested_by=requester, amount=600_000_000,
        currency="VND", payload={"kind": "expense"}, is_finance=True,
    )  # fmt: skip
    assert req.target_kind == "ai_action" and req.department_id is None
    ceo, dir_ = uuid.uuid4(), uuid.uuid4()
    assert str(req.id) in _ids(await _inbox(api, "CEO", ceo))
    assert str(req.id) not in _ids(await _inbox(api, "DIR", dir_))  # step 1 = CEO
    assert str(req.id) not in _ids(await _inbox(api, "MGR", uuid.uuid4(), uuid.uuid4()))
    assert str(req.id) not in _ids(await _inbox(api, "CEO", requester))  # own request
    r1 = await as_user(api, "POST", f"{WF}/{req.id}/decide", "CEO", ceo,
                       json={"decision": "approve"})  # fmt: skip
    assert r1.json()["data"]["step"] == 2 and r1.json()["data"]["rule_code"] == RULE_TWO_SIDED
    assert str(req.id) in _ids(await _inbox(api, "DIR", dir_))
    same = await as_user(api, "POST", f"{WF}/{req.id}/decide", "CEO", ceo,
                         json={"decision": "approve"})  # fmt: skip
    assert same.status_code == 403  # CEO is not a step-2 role
    # final approve without the AI hook (the AI action id here is synthetic — the hook path is
    # covered by test_ai_e2e.py::test_finance_action_opens_approval_and_executes_on_hook)
    dir_p = Principal(user_id=dir_, role="DIR", permissions=frozenset(ROLE_PERMISSIONS["DIR"]))
    r2 = await svc.decide(dir_p, req.id, decision="approve", reason=None)
    assert r2.status == "APPROVED" and r2.rule_code == RULE_TWO_SIDED
    det_r = await as_user(api, "GET", f"{WF}/{req.id}", "CEO", requester)
    assert det_r.status_code == 200, det_r.text
    det = det_r.json()["data"]
    assert [s["decision"] for s in det["timeline"]] == ["requested", "approve", "approve"]

"""TC-RSK-002 — EP-104 accept (CEO + reason), EP-106 lifecycle, scope per role (T-211, T-215)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import ApiClient
from tests.integration.risk.helpers import (
    audit_actions,
    make_risk,
    outbox_for,
    set_status,
    types,
)


async def test_accept_ceo_only_with_reason(api: ApiClient, db_session: AsyncSession) -> None:
    r = await make_risk(api)
    url = f"/risk/risks/{r['id']}/accept"
    deny = await api.call("POST", url, "RISK_MANAGER", json={"reason": "ok go"})
    assert deny.status_code == 403
    miss = await api.call("POST", url, "CEO", json={})
    assert miss.status_code == 422
    ok = await api.call("POST", url, "CEO", json={"reason": "Chấp nhận trong ngân sách"})
    assert ok.status_code == 200
    d = ok.json()["data"]
    assert d["status"] == "accepted" and d["accepted_reason"] and d["accepted_by"]
    assert "risk.risk_accept" in await audit_actions(db_session, r["id"])
    again = await api.call("POST", url, "CEO", json={"reason": "again"})
    assert again.status_code == 409
    closed = await set_status(api, r["id"], "closed")
    assert closed.status_code == 200
    assert (await api.call("POST", url, "CEO", json={"reason": "late"})).status_code == 409


async def test_lifecycle_transitions(api: ApiClient, db_session: AsyncSession) -> None:
    r = await make_risk(api, likelihood=3, impact=3)  # medium → no identified event
    rid = r["id"]
    assert (await set_status(api, rid, "proposed")).status_code == 409
    assert (await set_status(api, rid, "accepted")).status_code == 409
    for to in ("assessed", "mitigating", "monitoring"):
        res = await set_status(api, rid, to, reason="step")
        assert res.status_code == 200, res.text
    back = await set_status(api, rid, "mitigating")
    assert back.status_code == 200
    done = await set_status(api, rid, "closed")
    assert done.json()["data"]["status"] == "closed"
    assert (await set_status(api, rid, "monitoring")).status_code == 409
    ev = await outbox_for(db_session, rid)
    assert types(ev) == ["risk.risk_mitigated", "risk.risk_mitigated"]
    assert [e[1]["status"] for e in ev] == ["monitoring", "closed"]
    patch = await api.call("PATCH", f"/risk/risks/{rid}", "RISK_MANAGER", json={"version": 99})
    assert patch.status_code == 409
    a = await api.call(
        "POST",
        f"/risk/risks/{rid}/assessments",
        "RISK_MANAGER",
        json={"likelihood": 1, "impact": 1},
    )
    assert a.status_code == 409


async def test_owner_required_before_mitigating(api: ApiClient) -> None:
    r = await make_risk(api, likelihood=1, impact=2, owner_id=None)
    res = await set_status(api, r["id"], "mitigating")
    assert res.status_code == 422
    owner = str(uuid.uuid4())
    res = await set_status(api, r["id"], "mitigating", owner_id=owner)
    assert res.status_code == 200 and res.json()["data"]["owner_id"] == owner


async def test_manager_department_scope(api: ApiClient) -> None:
    dept, other = uuid.uuid4(), uuid.uuid4()
    mine = await make_risk(api, "MANAGER", department_id=dept)
    assert mine["department_id"] == str(dept)
    bad = await api.call(
        "POST", "/risk/risks", "MANAGER", department_id=dept,
        json={"title": "x", "category": "ai", "likelihood": 1, "impact": 1,
              "department_id": str(other)},
    )  # fmt: skip
    assert bad.status_code == 403 and bad.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    foreign = await make_risk(api, department_id=None, likelihood=1, impact=1, owner_id=None)
    lst = await api.call("GET", "/risk/risks", "MANAGER", department_id=dept, params={"limit": 100})
    ids = [x["id"] for x in lst.json()["data"]]
    assert mine["id"] in ids and foreign["id"] not in ids
    g = await api.call("GET", f"/risk/risks/{foreign['id']}", "MANAGER", department_id=dept)
    assert g.status_code == 403
    nodept = await api.call("GET", "/risk/risks", "MANAGER")
    assert nodept.status_code == 403
    other_mgr = await set_status(api, mine["id"], "assessed", role="MANAGER")
    assert other_mgr.status_code == 403  # token without department_id cannot see it


async def test_linked_and_reviewer_scope(api: ApiClient) -> None:
    deal = await make_risk(
        api, category="financial", linked_entities={"deal_id": str(uuid.uuid4())}
    )
    people = await make_risk(api, category="people")
    sales = await api.call("GET", "/risk/risks", "VP_SALES", params={"limit": 100})
    ids = [x["id"] for x in sales.json()["data"]]
    assert deal["id"] in ids and people["id"] not in ids
    hr = await api.call("GET", f"/risk/risks/{people['id']}", "HR_MANAGER")
    assert hr.status_code == 200
    assert (await api.call("GET", f"/risk/risks/{deal['id']}", "CPO")).status_code == 403
    assert (await api.call("GET", "/risk/risks", "REVIEWER")).status_code == 403
    assert (await api.call("GET", "/risk/risks", "EMPLOYEE")).status_code == 403

"""TC-RSK-004 — EP-103 mitigations, overdue, risk status sync, risk_mitigated (T-213)."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.risk.services import rules
from tests.conftest import ApiClient
from tests.integration.risk.helpers import (
    OWNER,
    audit_actions,
    make_risk,
    outbox_for,
    set_status,
    types,
)

FAR = "2037-06-30"
PAST = "2020-01-31"


async def make_mit(api: ApiClient, risk_id: str, role: str = "RISK_MANAGER", **kw: Any) -> Any:
    body = {"risk_id": risk_id, "title": "Giảm thiểu", "owner_id": OWNER, "due_date": FAR, **kw}
    return await api.call("POST", "/risk/mitigations", role, json=body)


async def test_mitigation_crud_and_sync(api: ApiClient, db_session: AsyncSession) -> None:
    r = await make_risk(api, likelihood=3, impact=3)
    m = await make_mit(api, r["id"])
    assert m.status_code == 201, m.text
    mid = m.json()["data"]["id"]
    assert m.json()["data"]["status"] == "planned" and m.json()["data"]["overdue"] is False
    up = await api.call(
        "PATCH", f"/risk/mitigations/{mid}", "RISK_MANAGER",
        json={"version": 1, "status": "in_progress", "progress_pct": 40, "owner_id": None},
    )  # fmt: skip
    assert up.status_code == 200 and up.json()["data"]["progress_pct"] == 40
    risk = (await api.call("GET", f"/risk/risks/{r['id']}", "CEO")).json()["data"]
    assert risk["status"] == "mitigating"
    blocked = await set_status(api, r["id"], "closed")
    assert blocked.status_code == 422  # mitigation in_progress
    done = await api.call(
        "PATCH", f"/risk/mitigations/{mid}", "RISK_MANAGER",
        json={"version": 2, "status": "done", "progress_pct": 100},
    )  # fmt: skip
    assert done.json()["data"]["completed_at"] is not None
    risk = (await api.call("GET", f"/risk/risks/{r['id']}", "CEO")).json()["data"]
    assert risk["status"] == "monitoring"
    ev = await outbox_for(db_session, r["id"])
    assert types(ev) == ["risk.risk_mitigated"] and ev[0][1]["status"] == "monitoring"
    expected = ["risk.mitigation_create", "risk.mitigation_update", "risk.mitigation_update"]
    assert await audit_actions(db_session, mid) == expected
    got = await api.call("GET", f"/risk/mitigations/{mid}", "CFO")
    assert got.status_code == 200
    reopen = await api.call(
        "PATCH",
        f"/risk/mitigations/{mid}",
        "RISK_MANAGER",
        json={"version": 3, "status": "planned"},
    )
    assert reopen.json()["data"]["completed_at"] is None


async def test_overdue_filter_and_validation(api: ApiClient) -> None:
    r = await make_risk(api)
    late = (await make_mit(api, r["id"], due_date=PAST)).json()["data"]
    ok = (await make_mit(api, r["id"], status="done")).json()["data"]
    assert late["overdue"] is True and ok["overdue"] is False and ok["completed_at"]
    res = await api.call(
        "GET", "/risk/mitigations", "CEO", params={"risk_id": r["id"], "overdue": True}
    )
    assert [x["id"] for x in res.json()["data"]] == [late["id"]]
    res = await api.call(
        "GET", "/risk/mitigations", "CEO", params={"risk_id": r["id"], "overdue": False}
    )
    assert [x["id"] for x in res.json()["data"]] == [ok["id"]]
    bad = await make_mit(api, r["id"], progress_pct=120)
    assert bad.status_code == 422
    assert (await make_mit(api, str(uuid.uuid4()))).status_code == 404
    assert (await make_mit(api, r["id"], role="CFO")).status_code == 403
    assert (await api.call("GET", f"/risk/mitigations/{uuid.uuid4()}", "CEO")).status_code == 404


async def test_mitigation_closed_risk_and_scope(api: ApiClient) -> None:
    dept = uuid.uuid4()
    r = await make_risk(api, likelihood=1, impact=1, owner_id=None)
    assert (await set_status(api, r["id"], "closed", owner_id=OWNER)).status_code == 200
    res = await make_mit(api, r["id"])
    assert res.status_code == 409
    mine = await make_risk(api, "MANAGER", department_id=dept)
    assert (await make_mit(api, mine["id"], role="MANAGER")).status_code == 403  # no dept in token
    m = await api.call(
        "POST", "/risk/mitigations", "MANAGER", department_id=dept,
        json={"risk_id": mine["id"], "title": "t", "owner_id": OWNER, "due_date": FAR},
    )  # fmt: skip
    assert m.status_code == 201
    lst = await api.call("GET", "/risk/mitigations", "MANAGER", department_id=dept,
                         params={"limit": 100})  # fmt: skip
    assert {x["risk_id"] for x in lst.json()["data"]} == {mine["id"]}


def test_heatmap_grid() -> None:
    grid = rules.heatmap([(1, 1), (5, 5), (5, 5)])
    assert len(grid) == 25
    assert grid[0] == {"likelihood": 1, "impact": 1, "count": 1}
    assert grid[-1] == {"likelihood": 5, "impact": 5, "count": 2}
    assert sum(c["count"] for c in grid) == 3

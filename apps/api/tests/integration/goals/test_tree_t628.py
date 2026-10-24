"""T-628 — EP-STR-01 tree, EP-STR-22, EP-PRF-06 (10 §7.2.3): TC-M14-03, 04, 06, 08, 09.

Data in an isolated far-future period (strategy 2300+n) so the demo seed does not interfere.
"""

import uuid
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.services.base import today
from app.modules.execution.services.kpi_rules import period_key_for
from tests.conftest import ApiClient
from tests.integration.execution.helpers import (
    as_user,
    make,
    make_strategic_objective,
    make_strategy,
    patch,
    uniq,
)

pytestmark = pytest.mark.integration


def _code() -> str:  # letters only — digit runs look like PII to the outbox guard
    return "K-" + uuid.uuid4().hex[:8].translate(str.maketrans("0123456789", "GHIJKLMNOP"))


async def _world(api: ApiClient, year: int, dept: uuid.UUID) -> dict[str, Any]:
    owner = uuid.uuid4()
    s = await make_strategy(api, period_start=f"{year}-01-01", period_end=f"{year + 1}-01-01")
    so = await make_strategic_objective(api, s["id"], pillar="C", department_id=str(dept))
    root = await make(api, "/kpis", {"code": _code(), "name": "Doanh thu", "unit": "tỷ",
                                     "target": 100, "owner_id": str(owner),
                                     "strategic_objective_id": so["id"],
                                     "department_id": str(dept)})  # fmt: skip
    child = await make(api, "/kpis", {"code": _code(), "name": "DT miền Bắc", "unit": "tỷ",
                                      "target": 40, "owner_id": str(owner),
                                      "parent_kpi_id": root["id"],
                                      "department_id": str(dept)})  # fmt: skip
    m = await api.call("POST", f"/kpis/{child['id']}/measurements", "CEO",
                       json={"period_key": f"{year}-01", "actual_value": 26})  # fmt: skip
    assert m.status_code == 201, m.text
    o = await make(api, "/objectives", {"title": uniq("O"), "owner_id": str(owner),
                                        "period_key": f"{year}-Q1", "department_id": str(dept),
                                        "strategic_objective_id": so["id"]})  # fmt: skip
    kr = await make(api, f"/objectives/{o['id']}/key-results", {
        "title": "Pipeline 3x", "baseline": 0, "target": 3, "unit": "x",
        "owner_id": str(owner)})  # fmt: skip
    sub = await make(api, "/objectives", {"title": uniq("O"), "owner_id": str(owner),
                                          "period_key": f"{year}-Q1", "parent_id": o["id"],
                                          "department_id": str(dept)})  # fmt: skip
    ini = await make(api, "/goals/initiatives", {
        "code": uniq("INI"), "title": "CRM", "owner_id": str(owner),
        "start_date": f"{year}-01-01", "planned_end_date": f"{year}-12-31",
        "strategic_objective_id": so["id"], "department_id": str(dept)})  # fmt: skip
    p = await make(api, "/work/projects", {
        "code": uniq("P"), "name": "CRM rollout", "owner_id": str(owner),
        "initiative_id": ini["id"], "department_id": str(dept)})  # fmt: skip
    loose = await make(api, "/objectives", {"title": uniq("LOOSE"), "owner_id": str(owner),
                                            "period_key": f"{year}-Q1"})  # fmt: skip
    return {"s": s, "so": so, "root": root, "child": child, "o": o, "kr": kr, "sub": sub,
            "ini": ini, "p": p, "loose": loose, "owner": owner}  # fmt: skip


def _so_of(tree: dict[str, Any], sid: str) -> dict[str, Any]:
    [s] = [x for x in tree["strategies"] if x["id"] == sid]
    [so] = s["strategic_objectives"]
    return dict(so)


async def test_goal_tree_structure(api: ApiClient, db_session: AsyncSession) -> None:
    """TC-M14-04: Strategy → SO → {KPI ▸ child, Objective ▸ KR ▸ child, Initiative ▸ Project}."""
    year = 2300 + uuid.uuid4().int % 600
    dept = uuid.uuid4()
    w = await _world(api, year, dept)
    r = await api.call("GET", "/goals/tree", "CEO", params={"period_key": f"{year}-Q1"})
    assert r.status_code == 200, r.text
    tree = r.json()["data"]
    so = _so_of(tree, w["s"]["id"])
    assert so["pillar"] == "C" and so["restricted"] is False
    [k] = so["kpis"]
    assert k["id"] == w["root"]["id"] and k["latest_evaluation"] is None
    [c] = k["children"]
    ev = c["latest_evaluation"]
    assert (ev["period_key"], ev["achievement_pct"], ev["band"]) == (f"{year}-01", 65, "CRITICAL")
    [o] = so["objectives"]
    assert o["id"] == w["o"]["id"] and o["at_risk_kr_count"] == 0
    assert [x["id"] for x in o["children"]] == [w["sub"]["id"]]
    assert o["key_results"][0]["title"] == "Pipeline 3x"
    assert o["key_results"][0]["at_risk"] is False
    [i] = so["initiatives"]
    assert i["projects"] == [{"id": w["p"]["id"], "code": w["p"]["code"],
                              "name": "CRM rollout", "status": w["p"]["status"]}]  # fmt: skip
    assert isinstance(i["on_track"], bool)
    assert w["loose"]["id"] in {x["id"] for x in tree["unaligned"]["objectives"]}
    other = await api.call("GET", "/goals/tree", "CEO", params={"period_key": f"{year}-Q3"})
    assert _so_of(other.json()["data"], w["s"]["id"])["objectives"] == []  # period filter
    one = await api.call("GET", "/goals/tree", "CEO", params={"strategy_id": w["s"]["id"]})
    assert [x["id"] for x in one.json()["data"]["strategies"]] == [w["s"]["id"]]
    assert one.json()["data"]["unaligned"] == {"kpis": [], "objectives": []}
    by_dept = await api.call("GET", "/goals/tree", "CEO", params={
        "period_key": f"{year}-Q1", "department_id": str(uuid.uuid4())})  # fmt: skip
    assert w["s"]["id"] not in {x["id"] for x in by_dept.json()["data"]["strategies"]}
    bad = await api.call("GET", "/goals/tree", "CEO", params={"period_key": "Q1"})
    assert bad.status_code == 422


async def test_goal_tree_query_count_is_constant(api: ApiClient, db_session: AsyncSession) -> None:
    """TC-M14-04: no N+1 — the statement count does not grow with the node count."""
    year = 2300 + uuid.uuid4().int % 600
    w = await _world(api, year, uuid.uuid4())
    params = {"strategy_id": w["s"]["id"], "period_key": f"{year}-Q1"}

    async def count() -> int:
        n = 0

        def bump(*_: Any) -> None:
            nonlocal n
            n += 1

        sync = db_session.bind.sync_engine if hasattr(db_session.bind, "sync_engine") else None
        target = sync if sync is not None else db_session.sync_session.bind
        event.listen(target, "before_cursor_execute", bump)
        try:
            assert (await api.call("GET", "/goals/tree", "CEO", params=params)).status_code == 200
        finally:
            event.remove(target, "before_cursor_execute", bump)
        return n

    first = await count()
    assert first > 0
    for _ in range(3):  # more KPIs, objectives, initiatives under the same SO
        await make(
            api,
            "/kpis",
            {
                "code": _code(),
                "name": "x",
                "unit": "x",
                "target": 1,
                "owner_id": str(w["owner"]),
                "parent_kpi_id": w["root"]["id"],
            },
        )
        await make(
            api,
            "/objectives",
            {
                "title": uniq("O"),
                "owner_id": str(w["owner"]),
                "period_key": f"{year}-Q1",
                "parent_id": w["o"]["id"],
            },
        )
        await make(api, "/goals/initiatives", {
            "code": uniq("INI"), "title": "x", "owner_id": str(w["owner"]),
            "start_date": f"{year}-01-01", "planned_end_date": f"{year}-12-31",
            "strategic_objective_id": w["so"]["id"]})  # fmt: skip
    assert await count() == first


async def test_tree_restricted_ancestors(api: ApiClient) -> None:
    """Out-of-scope ancestors of a visible node → `{id, code?, title?, restricted: true}`."""
    year = 2300 + uuid.uuid4().int % 600
    w = await _world(api, year, uuid.uuid4())
    me = uuid.uuid4()
    mine = await make(api, "/kpis", {"code": _code(), "name": "KPI của tôi", "unit": "x",
                                     "target": 1, "owner_id": str(me),
                                     "parent_kpi_id": w["child"]["id"]})  # fmt: skip
    r = await as_user(
        api,
        "GET",
        "/goals/tree",
        "EMPLOYEE",
        me,
        params={"strategy_id": w["s"]["id"], "period_key": f"{year}-Q1"},
    )
    assert r.status_code == 200, r.text
    so = _so_of(r.json()["data"], w["s"]["id"])
    assert so["restricted"] is True and so["pillar"] is None  # SO of another department
    [root] = so["kpis"]
    assert root["restricted"] is True and root["code"] == w["root"]["code"]
    assert root["latest_evaluation"] is None and root["owner_id"] is None
    [child] = root["children"]
    assert child["restricted"] is True
    [leaf] = child["children"]
    assert leaf["id"] == mine["id"] and leaf["restricted"] is False
    assert so["objectives"] == [] and so["initiatives"] == []  # nothing visible below


async def test_initiative_projects(api: ApiClient) -> None:
    """TC-M14-06: EP-STR-22 + 409 deleting an initiative that still has projects."""
    w = await _world(api, 2300 + uuid.uuid4().int % 600, uuid.uuid4())
    url = f"/goals/initiatives/{w['ini']['id']}/projects"
    r = await api.call("GET", url, "CEO")
    assert r.status_code == 200, r.text
    [p] = r.json()["data"]
    assert p["id"] == w["p"]["id"] and p["owner_id"] == str(w["owner"])
    assert set(p) == {"id", "code", "name", "status", "start_date", "planned_end_date",
                      "owner_id"}  # fmt: skip
    assert (await api.call("GET", f"/goals/initiatives/{uuid.uuid4()}/projects", "CEO")
            ).status_code == 404  # fmt: skip
    gone = await api.call("DELETE", f"/goals/initiatives/{w['ini']['id']}", "CEO")
    assert gone.status_code == 409
    assert (await patch(api, f"/work/projects/{p['id']}", 1, initiative_id=None)).status_code == 200
    assert (await api.call("GET", url, "CEO")).json()["data"] == []
    assert (await api.call("DELETE", f"/goals/initiatives/{w['ini']['id']}", "CEO")
            ).status_code == 204  # fmt: skip


async def test_check_ins_due(api: ApiClient, db_session: AsyncSession) -> None:
    """EP-PRF-06: KRs of active objectives in the current period + active KPIs of the caller."""
    me = uuid.uuid4()
    day = today()
    o = await make(api, "/objectives", {"title": uniq("O"), "owner_id": str(me),
                                        "period_key": period_key_for("QUARTER", day)})  # fmt: skip
    kr = await make(
        api,
        f"/objectives/{o['id']}/key-results",
        {"title": "KR của tôi", "baseline": 0, "target": 10, "unit": "x", "owner_id": str(me)},
    )
    await make(api, f"/objectives/{o['id']}/key-results", {
        "title": "KR khác", "baseline": 0, "target": 10, "unit": "x",
        "owner_id": str(uuid.uuid4()), "weight_pct": 0})  # fmt: skip
    assert (await patch(api, f"/objectives/{o['id']}", 1, status="active")).status_code == 200
    k = await make(api, "/kpis", {"code": _code(), "name": "KPI tôi", "unit": "%", "target": 90,
                                  "owner_id": str(me)})  # fmt: skip
    r = await as_user(api, "GET", "/goals/check-ins/due", "EMPLOYEE", me)
    assert r.status_code == 200, r.text
    rows = {x["target_id"]: x for x in r.json()["data"]}
    assert set(rows) == {kr["id"], k["id"]}
    assert rows[kr["id"]]["due"] is True and rows[kr["id"]]["prefill"] is None
    assert rows[k["id"]]["due"] is True and rows[k["id"]]["target_type"] == "kpi"
    ck = await as_user(api, "POST", f"/key-results/{kr['id']}/check-ins", "EMPLOYEE", me,
                       json={"value": 4, "confidence": "MEDIUM"})  # fmt: skip
    assert ck.status_code == 201, ck.text
    last = period_key_for("MONTH", day.replace(day=1) - timedelta(days=1))
    m = await api.call("POST", f"/kpis/{k['id']}/measurements", "CEO",
                       json={"period_key": last, "actual_value": 91})  # fmt: skip
    assert m.status_code == 201, m.text
    rows = {
        x["target_id"]: x
        for x in (await as_user(api, "GET", "/goals/check-ins/due", "EMPLOYEE", me)).json()["data"]
    }
    assert rows[kr["id"]]["due"] is False and rows[kr["id"]]["current_value"] == 4
    assert rows[kr["id"]]["confidence"] == "MEDIUM"
    assert rows[k["id"]]["due"] is False and rows[k["id"]]["current_value"] == 91


async def test_strategy_crud_contract_edges(api: ApiClient, db_session: AsyncSession) -> None:
    """TC-M14-03 (remainder of T-626): missing Idempotency-Key → 400; stale version → 409;
    soft delete keeps the row."""
    body = {"code": uniq("STR"), "name": "x", "owner_id": str(uuid.uuid4()),
            "period_start": "2390-01-01", "period_end": "2391-01-01"}  # fmt: skip
    no_key = await api.http.post("/api/v1/goals/strategies", json=body,
                                 headers=api.headers("CEO"))  # fmt: skip
    assert no_key.status_code == 400
    s = await make(api, "/goals/strategies", body)
    stale = await patch(api, f"/goals/strategies/{s['id']}", 7, name="y")
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "CONFLICT_STATE"
    so = await make_strategic_objective(api, s["id"])
    stale_so = await patch(api, f"/goals/strategic-objectives/{so['id']}", 3, title="y")
    assert stale_so.status_code == 409
    assert (await api.call("DELETE", f"/goals/strategic-objectives/{so['id']}", "CEO")
            ).status_code == 204  # fmt: skip
    assert (await api.call("DELETE", f"/goals/strategies/{s['id']}", "CEO")).status_code == 204
    row = await db_session.execute(
        text("SELECT deleted_at IS NOT NULL FROM execution.strategies WHERE id = :i"),
        {"i": s["id"]},
    )
    assert row.scalar() is True

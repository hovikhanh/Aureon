"""T-626 — Strategy + StrategicObjective (R-DEC-50, 05 §2.6): TC-M14-01, TC-M14-06 (T-626 part).

- EP-STR-02..11 CRUD: 409 duplicate code, 422 period, 422 `overlapping_active_strategy`,
  422 `has_live_children` / `has_live_links`, audit `execution.strategy_*`;
- scope skeleton (R-DEC-57): only CEO writes a Strategy, DIR only SO of its `scope_pillars`;
- EP-STR-13: `strategic_objective_id` required / must exist (422 `details.field`), `objective_id`
  optional; SO `progress_pct` follows its initiatives in the same transaction;
- migration 0016 backfill: every seeded Initiative has an SO (when the seed is loaded).
"""

import uuid
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import ApiClient
from tests.integration.execution.helpers import (
    audit_actions,
    make,
    make_strategic_objective,
    make_strategy,
    patch,
    uniq,
)

pytestmark = pytest.mark.integration


def _period(year: int) -> dict[str, str]:
    return {"period_start": f"{year}-01-01", "period_end": f"{year + 1}-01-01"}


async def test_strategy_crud_rules(api: ApiClient, db_session: AsyncSession) -> None:
    year = 2100 + uuid.uuid4().int % 800  # isolated period: overlap rule is tenant-wide
    s = await make_strategy(api, **_period(year), status="active")
    assert s["status"] == "active" and s["version"] == 1
    dup = await api.call("POST", "/goals/strategies", "CEO", json={
        "code": s["code"], "name": "x", "owner_id": str(uuid.uuid4()),
        **_period(year + 5)})  # fmt: skip
    assert dup.status_code == 409
    bad = await api.call("POST", "/goals/strategies", "CEO", json={
        "code": uniq("STR"), "name": "x", "owner_id": str(uuid.uuid4()),
        "period_start": f"{year}-06-01", "period_end": f"{year}-06-01"})  # fmt: skip
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "VALIDATION_ERROR"
    over = await api.call("POST", "/goals/strategies", "CEO", json={
        "code": uniq("STR"), "name": "x", "owner_id": str(uuid.uuid4()), "status": "active",
        "period_start": f"{year}-06-01", "period_end": f"{year + 1}-06-01"})  # fmt: skip
    assert over.status_code == 422
    assert over.json()["error"]["details"]["reason"] == "overlapping_active_strategy"
    draft = await make_strategy(api, period_start=f"{year}-06-01", period_end=f"{year + 1}-06-01")
    act = await patch(api, f"/goals/strategies/{draft['id']}", 1, status="active")
    assert act.status_code == 422
    for role in ("CFO", "MANAGER", "EMPLOYEE"):
        r = await api.call("POST", "/goals/strategies", role, json={
            "code": uniq("STR"), "name": "x", "owner_id": str(uuid.uuid4()),
            **_period(year)})  # fmt: skip
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_ROLE", role
    got = await api.call("GET", f"/goals/strategies/{s['id']}", "EMPLOYEE")
    assert got.status_code == 200
    lst = await api.call("GET", "/goals/strategies", "CEO",
                         params={"status": "active", "limit": 100})  # fmt: skip
    assert s["id"] in {x["id"] for x in lst.json()["data"]}
    up = await patch(api, f"/goals/strategies/{s['id']}", 1, vision="Dẫn đầu", name=None)
    assert up.status_code == 200 and up.json()["data"]["vision"] == "Dẫn đầu"
    so = await make_strategic_objective(api, s["id"])
    busy = await api.call("DELETE", f"/goals/strategies/{s['id']}", "CEO")
    assert busy.status_code == 422
    assert busy.json()["error"]["details"]["reason"] == "has_live_children"
    assert (await api.call("DELETE", f"/goals/strategic-objectives/{so['id']}", "CEO")
            ).status_code == 204  # fmt: skip
    assert (await api.call("DELETE", f"/goals/strategies/{s['id']}", "CEO")).status_code == 204
    assert (await api.call("GET", f"/goals/strategies/{s['id']}", "CEO")).status_code == 404
    acts = await audit_actions(db_session, s["id"])
    assert acts == ["execution.strategy_create", "execution.strategy_delete",
                    "execution.strategy_update"]  # fmt: skip


async def test_strategic_objective_scope_and_links(
    api: ApiClient, db_session: AsyncSession
) -> None:
    s = await make_strategy(api)
    so = await make_strategic_objective(api, s["id"], pillar="F", weight_pct=40, sort_order=2)
    assert so["status"] == "draft" and so["progress_pct"] == 0 and so["sort_order"] == 2
    dup = await api.call("POST", "/goals/strategic-objectives", "CEO", json={
        "strategy_id": s["id"], "code": so["code"], "title": "x",
        "owner_id": str(uuid.uuid4())})  # fmt: skip
    assert dup.status_code == 409
    ghost = await api.call("POST", "/goals/strategic-objectives", "CEO", json={
        "strategy_id": str(uuid.uuid4()), "code": uniq("SO"), "title": "x",
        "owner_id": str(uuid.uuid4())})  # fmt: skip
    assert ghost.status_code == 422 and ghost.json()["error"]["details"]["field"] == "strategy_id"
    # DIR writes only its pillar (CFO = DIR F); MGR / EMP never.
    mine = await make_strategic_objective(api, s["id"], role="CFO", pillar="F")
    other = await api.call("POST", "/goals/strategic-objectives", "CFO", json={
        "strategy_id": s["id"], "code": uniq("SO"), "title": "x", "pillar": "C",
        "owner_id": str(uuid.uuid4())})  # fmt: skip
    assert other.status_code == 403 and other.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    mgr = await api.call("POST", "/goals/strategic-objectives", "MANAGER", json={
        "strategy_id": s["id"], "code": uniq("SO"), "title": "x",
        "owner_id": str(uuid.uuid4())})  # fmt: skip
    assert mgr.status_code == 403 and mgr.json()["error"]["code"] == "FORBIDDEN_ROLE"
    up = await patch(api, f"/goals/strategic-objectives/{mine['id']}", 1, role="CFO",
                     title="Biên lợi nhuận", status="active")  # fmt: skip
    assert up.status_code == 200 and up.json()["data"]["status"] == "active"
    move = await patch(api, f"/goals/strategic-objectives/{mine['id']}", 2, role="CFO",
                       pillar="C")  # fmt: skip
    assert move.status_code == 403
    # read scope: company level (no department) is visible to everyone
    dept = uuid.uuid4()
    hidden = await make_strategic_objective(api, s["id"], department_id=str(dept), pillar="U")
    emp = await api.call("GET", f"/goals/strategic-objectives/{hidden['id']}", "EMPLOYEE")
    assert emp.status_code == 403 and emp.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    seen = await api.call("GET", "/goals/strategic-objectives", "EMPLOYEE",
                          params={"strategy_id": s["id"], "limit": 100})  # fmt: skip
    assert {x["id"] for x in seen.json()["data"]} == {so["id"], mine["id"]}
    mgr_in = await api.call("GET", f"/goals/strategic-objectives/{hidden['id']}", "MANAGER",
                            department_id=dept)  # fmt: skip
    assert mgr_in.status_code == 200
    flt = await api.call(
        "GET",
        "/goals/strategic-objectives",
        "CEO",
        params={"strategy_id": s["id"], "pillar": "F", "sort_by": "sort_order", "order": "asc"},
    )
    assert [x["id"] for x in flt.json()["data"]] == [mine["id"], so["id"]], flt.json()
    # links: KPI root + Objective root + Initiative → counts, delete blocked
    owner = uuid.uuid4()
    kpi = await make(api, "/kpis", {
        "code": uniq("KPI"), "name": "Biên LN", "unit": "%", "target": 20, "owner_id": str(owner),
        "strategic_objective_id": so["id"], "pillar": "F"})  # fmt: skip
    assert kpi["strategic_objective_id"] == so["id"] and kpi["pillar"] == "F"
    child = await api.call("POST", "/kpis", "CEO", json={
        "code": uniq("KPI"), "name": "c", "unit": "%", "target": 1, "owner_id": str(owner),
        "parent_kpi_id": kpi["id"],
        "strategic_objective_id": so["id"]})  # fmt: skip
    assert child.status_code == 422
    obj = await make(api, "/objectives", {"title": "o", "owner_id": str(owner),
                                          "period_key": "2037",
                                          "strategic_objective_id": so["id"]})  # fmt: skip
    assert obj["strategic_objective_id"] == so["id"]
    by_so = await api.call("GET", "/objectives", "CEO",
                           params={"strategic_objective_id": so["id"]})  # fmt: skip
    assert [x["id"] for x in by_so.json()["data"]] == [obj["id"]]
    kpis = await api.call("GET", "/kpis", "CEO", params={"strategic_objective_id": so["id"]})
    assert [x["id"] for x in kpis.json()["data"]] == [kpi["id"]]
    detail = (await api.call("GET", f"/goals/strategic-objectives/{so['id']}", "CEO")).json()
    assert (detail["data"]["kpi_count"], detail["data"]["objective_count"],
            detail["data"]["initiative_count"]) == (1, 1, 0)  # fmt: skip
    busy = await api.call("DELETE", f"/goals/strategic-objectives/{so['id']}", "CEO")
    assert busy.status_code == 422 and busy.json()["error"]["details"]["reason"] == "has_live_links"
    assert "execution.strategic_objective_create" in await audit_actions(db_session, so["id"])


async def _initiative(api: ApiClient, so_id: Any, **kw: Any) -> Any:
    return await api.call("POST", "/goals/initiatives", "CEO", json={
        "code": uniq("INI"), "title": "i", "owner_id": str(uuid.uuid4()),
        "start_date": "2037-01-01", "planned_end_date": "2037-12-31",
        **({"strategic_objective_id": str(so_id)} if so_id else {}), **kw})  # fmt: skip


async def test_initiative_requires_so_and_drives_progress(api: ApiClient) -> None:
    so = await make_strategic_objective(api)
    missing = await _initiative(api, None)
    assert missing.status_code == 422
    ghost = await _initiative(api, uuid.uuid4())
    assert ghost.status_code == 422
    assert ghost.json()["error"]["details"]["field"] == "strategic_objective_id"
    a = (await _initiative(api, so["id"], weight_pct=30)).json()["data"]
    b = (await _initiative(api, so["id"], weight_pct=10)).json()["data"]
    assert a["objective_id"] is None and a["strategic_objective_id"] == so["id"]
    url = f"/goals/initiatives/{a['id']}/milestones"
    await make(api, url, {"title": "m", "due_date": "2037-03-01", "status": "done"})
    got = (await api.call("GET", f"/goals/strategic-objectives/{so['id']}", "CEO")).json()
    assert got["data"]["progress_pct"] == 75  # (100×30 + 0×10) / 40
    flt = await api.call("GET", "/goals/initiatives", "CEO",
                         params={"strategic_objective_id": so["id"]})  # fmt: skip
    assert {x["id"] for x in flt.json()["data"]} == {a["id"], b["id"]}
    so2 = await make_strategic_objective(api)
    mv = await patch(api, f"/goals/initiatives/{a['id']}", 1, strategic_objective_id=so2["id"])
    assert mv.status_code == 200
    one = (await api.call("GET", f"/goals/strategic-objectives/{so['id']}", "CEO")).json()
    two = (await api.call("GET", f"/goals/strategic-objectives/{so2['id']}", "CEO")).json()
    assert (one["data"]["progress_pct"], two["data"]["progress_pct"]) == (0, 100)


async def test_migration_0016_backfill(db_session: AsyncSession) -> None:
    """TC-M14-01: schema in place; backfilled objectives pass their SO to their initiatives.

    The up/down/up round-trip itself is a CLI step (`alembic downgrade -1 && upgrade head`).
    """
    cols = await db_session.execute(text(
        "SELECT table_name, column_name, is_nullable FROM information_schema.columns "
        "WHERE table_schema = 'execution' AND column_name IN "
        "('strategic_objective_id', 'objective_id', 'pillar') "
        "AND table_name IN ('objectives', 'kpis', 'initiatives')"))  # fmt: skip
    got = {(t, c): n for t, c, n in cols}
    for t in ("objectives", "kpis", "initiatives"):
        assert got[(t, "strategic_objective_id")] == "YES"
    assert got[("initiatives", "objective_id")] == "YES" and ("kpis", "pillar") in got
    # backfill invariant: an initiative under a linked (root) objective carries the same SO
    gap = await db_session.execute(text(
        "SELECT count(*) FROM execution.initiatives i JOIN execution.objectives o "
        "ON o.id = i.objective_id WHERE i.deleted_at IS NULL AND o.strategic_objective_id "
        "IS NOT NULL AND i.strategic_objective_id IS NULL AND i.source = 'SEED'"))  # fmt: skip
    assert gap.scalar_one() == 0

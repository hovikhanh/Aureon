"""T-632 — goal scope R-DEC-57 (10 §7.2.3): TC-M14-14 (read), TC-M14-15 (write / check-in).

World: parent department P ▸ child C (via `/hr/departments`, so `core/org_scope` resolves the
subtree through the `hr` provider) + an unrelated department X. Far-future period isolates it.
"""

import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.org_scope import department_subtree
from tests.conftest import ApiClient
from tests.integration.execution.helpers import as_user, make, uniq
from tests.integration.hr.helpers import make_department

pytestmark = pytest.mark.integration


def _code() -> str:  # letters only — digit runs look like PII to the outbox guard
    return "K-" + uuid.uuid4().hex[:8].translate(str.maketrans("0123456789", "GHIJKLMNOP"))


async def _kpi(api: ApiClient, owner: uuid.UUID, dept: Any, pillar: str | None = None) -> Any:
    body = {"code": _code(), "name": "KPI", "unit": "%", "target": 100, "owner_id": str(owner),
            "department_id": None if dept is None else str(dept), "pillar": pillar}  # fmt: skip
    return await make(api, "/kpis", body)


async def _okr(api: ApiClient, owner: uuid.UUID, dept: Any, period: str) -> Any:
    body = {"title": uniq("O"), "owner_id": str(owner), "period_key": period,
            "department_id": str(dept)}  # fmt: skip
    o = await make(api, "/objectives", body)
    krs = [await make(api, f"/objectives/{o['id']}/key-results", {
        "title": uniq("KR"), "baseline": 0, "target": 10, "unit": "x", "owner_id": str(own)})
        for own in (owner, uuid.uuid4())]  # fmt: skip
    r = await api.call("PATCH", f"/objectives/{o['id']}", "CEO",
                       json={"status": "active", "version": o["version"]})  # fmt: skip
    assert r.status_code == 200, r.text
    return o, krs


async def _world(api: ApiClient) -> dict[str, Any]:
    parent = await make_department(api)
    child = await make_department(api, parent_id=parent["id"])
    other = await make_department(api)
    emp = uuid.uuid4()
    w = {"P": uuid.UUID(parent["id"]), "C": uuid.UUID(child["id"]),
         "X": uuid.UUID(other["id"]), "emp": emp}  # fmt: skip
    w["k_child"] = await _kpi(api, emp, w["C"])
    w["k_other"] = await _kpi(api, uuid.uuid4(), w["X"])
    w["k_pillar"] = await _kpi(api, uuid.uuid4(), w["X"], "C")
    w["k_company"] = await _kpi(api, uuid.uuid4(), None)
    return w


def _ids(r: Any) -> set[str]:
    assert r.status_code == 200, r.text
    return {x["id"] for x in r.json()["data"]}


async def test_department_subtree_provider(api: ApiClient, db_session: AsyncSession) -> None:
    parent = await make_department(api)
    child = await make_department(api, parent_id=parent["id"])
    grand = await make_department(api, parent_id=child["id"])
    p = uuid.UUID(parent["id"])
    got = await department_subtree(db_session, (p,))
    assert got == {p, uuid.UUID(child["id"]), uuid.UUID(grand["id"])}
    assert await department_subtree(db_session, ()) == set()


async def _get(api: ApiClient, role: str, user: uuid.UUID, url: str, **kw: Any) -> int:
    r = await as_user(api, "GET", url, role, user, **kw)
    return int(r.status_code) if r.status_code != 403 else r.json()["error"]["code"]


async def test_read_scope(api: ApiClient) -> None:
    """TC-M14-14: MGR/DIR department subtree (+ pillar for DIR), EMP own, CEO all."""
    w = await _world(api)
    ks = {n: f"/kpis/{w[n]['id']}" for n in ("k_child", "k_other", "k_pillar", "k_company")}
    mgr, dir_, emp = uuid.uuid4(), uuid.uuid4(), w["emp"]
    expect = {
        ("MANAGER", mgr, w["P"]): {"k_child": 200, "k_other": "FORBIDDEN_SCOPE",
                                   "k_pillar": "FORBIDDEN_SCOPE", "k_company": 200},
        ("VP_SALES", dir_, w["P"]): {"k_child": 200, "k_other": "FORBIDDEN_SCOPE",
                                    "k_pillar": 200, "k_company": 200},
        ("EMPLOYEE", emp, w["C"]): {"k_child": 200, "k_other": "FORBIDDEN_SCOPE",
                                    "k_pillar": "FORBIDDEN_SCOPE",
                                    "k_company": "FORBIDDEN_SCOPE"},
        ("CEO", uuid.uuid4(), None): dict.fromkeys(ks, 200),
    }  # fmt: skip
    for (role, user, dept), want in expect.items():
        got = {n: await _get(api, role, user, url, department_id=dept) for n, url in ks.items()}
        assert got == want, role
    # list: MGR of the parent sees the child department's KPIs, not X
    lst = await as_user(api, "GET", "/kpis", "MANAGER", mgr, department_id=w["P"],
                        params={"department_id": str(w["C"])})  # fmt: skip
    assert w["k_child"]["id"] in _ids(lst)
    lst = await as_user(api, "GET", "/kpis", "MANAGER", mgr, department_id=w["P"],
                        params={"department_id": str(w["X"])})  # fmt: skip
    assert _ids(lst) == set()
    mine = await as_user(api, "GET", "/kpis", "EMPLOYEE", emp, department_id=w["C"],
                         params={"limit": 100})  # fmt: skip
    assert _ids(mine) == {w["k_child"]["id"]}
    # tree department filter inside the subtree is allowed, outside → 403
    ok = await as_user(api, "GET", "/goals/tree", "MANAGER", mgr, department_id=w["P"],
                       params={"department_id": str(w["C"])})  # fmt: skip
    assert ok.status_code == 200, ok.text
    bad = await as_user(api, "GET", "/goals/tree", "MANAGER", mgr, department_id=w["P"],
                        params={"department_id": str(w["X"])})  # fmt: skip
    assert bad.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    for role in ("REVIEWER", "ADMIN"):
        r = await api.call("GET", ks["k_child"], role)
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_ROLE"
    other_tenant = await api.call("GET", ks["k_child"], "CEO", tenant_id=uuid.uuid4())
    assert other_tenant.status_code == 404


async def test_write_scope(api: ApiClient) -> None:
    """TC-M14-15: EMP check-in own only; EMP cannot create; MGR/DIR within the subtree."""
    w = await _world(api)
    year = 2300 + uuid.uuid4().int % 600
    _, (kr_emp, kr_other) = await _okr(api, w["emp"], w["C"], f"{year}-Q1")
    emp = {"department_id": w["C"]}

    def ci(value: int) -> dict[str, Any]:
        return {"value": value, "confidence": "MEDIUM"}

    ok = await as_user(api, "POST", f"/key-results/{kr_emp['id']}/check-ins", "EMPLOYEE",
                       w["emp"], json=ci(3), **emp)  # fmt: skip
    assert ok.status_code == 201, ok.text
    assert ok.json()["data"]["user_id"] == str(w["emp"])
    r = await as_user(api, "POST", f"/key-results/{kr_other['id']}/check-ins", "EMPLOYEE",
                      w["emp"], json=ci(3), **emp)  # fmt: skip
    assert r.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    r = await as_user(api, "POST", f"/kpis/{w['k_other']['id']}/check-ins", "EMPLOYEE",
                      w["emp"], json=ci(3), **emp)  # fmt: skip
    assert r.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    body = {"code": _code(), "name": "KPI", "unit": "%", "target": 1, "owner_id": str(w["emp"])}
    for url, b in (("/kpis", body),
                   ("/objectives", {"title": "x", "owner_id": str(w["emp"]),
                                    "period_key": f"{year}-Q1"}),
                   ("/goals/initiatives", {"code": uniq("INI"), "title": "x",
                                           "owner_id": str(w["emp"]),
                                           "start_date": f"{year}-01-01",
                                           "planned_end_date": f"{year}-02-01",
                                           "strategic_objective_id": str(uuid.uuid4())}),
                   ("/goals/strategies", {"code": uniq("S"), "name": "x",
                                          "period_start": f"{year}-01-01",
                                          "period_end": f"{year + 1}-01-01",
                                          "owner_id": str(w["emp"])})):  # fmt: skip
        r = await as_user(api, "POST", url, "EMPLOYEE", w["emp"], json=b, **emp)
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_ROLE", url
    r = await as_user(api, "PATCH", f"/kpis/{w['k_child']['id']}", "EMPLOYEE", w["emp"],
                      json={"name": "x", "version": w["k_child"]["version"]}, **emp)  # fmt: skip
    assert r.json()["error"]["code"] == "FORBIDDEN_ROLE"
    mgr = uuid.uuid4()
    for url, b in (("/goals/strategies", {"code": uniq("S"), "name": "x",
                                          "period_start": f"{year}-01-01",
                                          "period_end": f"{year + 1}-01-01",
                                          "owner_id": str(mgr)}),
                   ("/goals/strategic-objectives", {"strategy_id": str(uuid.uuid4()),
                                                    "code": uniq("SO"), "title": "x",
                                                    "owner_id": str(mgr)})):  # fmt: skip
        r = await as_user(api, "POST", url, "MANAGER", mgr, json=b, department_id=w["P"])
        assert r.json()["error"]["code"] == "FORBIDDEN_ROLE", url
    so = {"strategy_id": str(uuid.uuid4()), "code": uniq("SO"), "title": "x",
          "owner_id": str(mgr), "pillar": "F"}  # fmt: skip
    r = await as_user(api, "POST", "/goals/strategic-objectives", "VP_SALES", mgr, json=so,
                      department_id=w["P"])  # fmt: skip
    assert r.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    # MGR of P: pin_department accepts the child department, not X
    r = await as_user(api, "POST", "/kpis", "MANAGER", mgr, department_id=w["P"],
                      json={**body, "code": _code(), "department_id": str(w["C"])})  # fmt: skip
    assert r.status_code == 201 and r.json()["data"]["department_id"] == str(w["C"])
    r = await as_user(api, "POST", "/kpis", "MANAGER", mgr, department_id=w["P"],
                      json={**body, "code": _code(), "department_id": str(w["X"])})  # fmt: skip
    assert r.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    r = await as_user(api, "PATCH", f"/kpis/{w['k_other']['id']}", "MANAGER", mgr,
                      department_id=w["P"], json={"name": "x",
                                                  "version": w["k_other"]["version"]})  # fmt: skip
    assert r.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    # MGR of P checks in on behalf inside the subtree: `user_id` = MGR
    r = await as_user(api, "POST", f"/key-results/{kr_other['id']}/check-ins", "MANAGER", mgr,
                      json=ci(4), department_id=w["P"])  # fmt: skip
    assert r.status_code == 201 and r.json()["data"]["user_id"] == str(mgr)
    r = await as_user(api, "POST", f"/kpis/{w['k_other']['id']}/check-ins", "MANAGER", mgr,
                      json=ci(4), department_id=w["P"])  # fmt: skip
    assert r.json()["error"]["code"] == "FORBIDDEN_SCOPE"

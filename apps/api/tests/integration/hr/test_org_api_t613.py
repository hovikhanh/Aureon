"""T-613 — D01 Organization API (EP-ORG-01..24, 10 §7.2.1; R-DEC-29/30/35).

TC-M12-04 tree `as_of`, TC-M12-05 CRUD/archive, TC-M12-06 audit + outbox, TC-M12-07 EP-HR
assignment link, TC-M12-11 RBAC (hr:admin, ADM scope `s`, EMP/REV/MGR, DIR khác khối).
"""

from datetime import date, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.seed.ids import seed_uuid
from tests.conftest import ApiClient
from tests.integration.hr.helpers import (
    ORG_ID,
    audit_rows,
    events,
    make_department,
    make_employee,
    uniq,
)

pytestmark = pytest.mark.integration
SAL = str(seed_uuid("department", "SAL"))
TODAY = date.today()


def data(r: Any, status: int = 200) -> Any:
    assert r.status_code == status, r.text
    return r.json()["data"] if status != 204 else None


def reason(r: Any) -> str:
    assert r.status_code == 422, r.text
    return str(r.json()["error"]["details"]["reason"])


# ---------- TC-M12-05 CRUD ----------
async def test_organization_crud_and_archive(api: ApiClient, db_session: AsyncSession) -> None:
    code = uniq("O")
    org = data(await api.call("POST", "/org/organizations", "CEO",
                              json={"code": code, "name": "Công ty con"}), 201)  # fmt: skip
    assert org["valid_from"] == TODAY.isoformat() and org["valid_to"] is None
    dup = await api.call("POST", "/org/organizations", "ADMIN", json={"code": code, "name": "x"})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    url = f"/org/organizations/{org['id']}"
    upd = data(await api.call("PATCH", url, "ADMIN", json={"name": "Đổi", "version": 1}))
    assert upd["version"] == 2
    stale = await api.call("PATCH", url, "ADMIN", json={"name": "y", "version": 1})
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "CONFLICT_STATE"
    dept = await make_department(api, organization_id=org["id"])
    assert reason(await api.call("DELETE", url, "CEO")) == "has_live_children"
    data(await api.call("DELETE", f"/hr/departments/{dept['id']}", "CEO"), 204)
    data(await api.call("DELETE", url, "CEO"), 204)
    assert (await api.call("GET", url, "CEO")).status_code == 404
    listed = data(await api.call("GET", "/org/organizations", "CEO",
                                 params={"include_archived": "true", "q": code}))  # fmt: skip
    assert [o["valid_to"] for o in listed] == [(TODAY + timedelta(days=1)).isoformat()]
    actions = sorted(a for a, *_ in await audit_rows(db_session, org["id"]))
    assert actions == ["hr.organization_archive", "hr.organization_create",
                       "hr.organization_update"]  # fmt: skip
    evts = await events(db_session, org["id"], "hr.org_structure_changed")
    assert [p["change"] for _, p in evts] == ["created", "updated", "archived"]


async def test_department_org_fields_and_rules(api: ApiClient) -> None:
    root = await make_department(api)
    assert root["organization_id"] == ORG_ID and root["valid_to"] is None
    child = await make_department(api, parent_id=root["id"])
    cyc = await api.call("PATCH", f"/hr/departments/{root['id']}", "CEO",
                         json={"parent_id": child["id"], "version": 1})  # fmt: skip
    assert reason(cyc) == "parent_cycle"
    no_org = await api.call("POST", "/hr/departments", "CEO", json={"name": "x", "code": uniq()})
    assert no_org.status_code == 422
    assert reason(await api.call("DELETE", f"/hr/departments/{root['id']}", "CEO")) == (
        "has_live_children"
    )
    data(await api.call("DELETE", f"/hr/departments/{child['id']}", "ADMIN"), 204)
    on = data(await api.call("GET", "/hr/departments", "CEO",
                             params={"as_of": TODAY.isoformat(), "limit": 100,
                                     "parent_id": root["id"]}))  # fmt: skip
    assert on == []


async def test_team_and_position_crud(api: ApiClient, db_session: AsyncSession) -> None:
    dept = await make_department(api)
    team = data(await api.call("POST", "/org/teams", "HR_MANAGER", json={
        "department_id": dept["id"], "code": uniq("T"), "name": "Team A"}), 201)  # fmt: skip
    pos = data(await api.call("POST", "/org/positions", "HR_MANAGER", json={
        "department_id": dept["id"], "code": uniq("P"), "title": "Chuyên viên",
        "headcount_budget": 2}), 201)  # fmt: skip
    assert (pos["filled"], pos["vacant"]) == (0, 2)
    emp = await make_employee(api, dept["id"])
    a = data(await api.call("POST", "/org/assignments", "HR_MANAGER", json={
        "employee_id": emp["id"], "department_id": dept["id"], "team_id": team["id"],
        "position_id": pos["id"], "valid_from": TODAY.isoformat()}), 201)  # fmt: skip
    assert a["team_id"] == team["id"]
    got = data(await api.call("GET", f"/org/positions/{pos['id']}", "CEO"))
    assert (got["filled"], got["vacant"]) == (1, 1)
    assert reason(await api.call("DELETE", f"/org/teams/{team['id']}", "CEO")) == (
        "has_live_children"
    )
    assert reason(await api.call("DELETE", f"/org/positions/{pos['id']}", "CEO")) == (
        "has_live_children"
    )
    upd = data(await api.call("PATCH", f"/org/teams/{team['id']}", "CEO",
                              json={"name": "Team B", "version": 1}))  # fmt: skip
    assert upd["name"] == "Team B"
    listed = data(await api.call("GET", "/org/teams", "CEO",
                                 params={"department_id": dept["id"]}))  # fmt: skip
    assert [t["id"] for t in listed] == [team["id"]]
    assert {act for act, *_ in await audit_rows(db_session, a["id"])} == {"hr.assignment_create"}


# ---------- TC-M12-02/07 assignments over HTTP ----------
async def test_assignment_endpoints(api: ApiClient) -> None:
    d1, d2 = await make_department(api), await make_department(api)
    emp = await make_employee(api, d1["id"])
    hist = data(await api.call("GET", "/org/assignments", "CEO",
                               params={"employee_id": emp["id"]}))  # fmt: skip
    assert len(hist) == 1 and hist[0]["valid_from"] == "2025-01-15"
    future = (TODAY + timedelta(days=3)).isoformat()
    body = {"employee_id": emp["id"], "department_id": d2["id"], "valid_from": future}
    assert reason(await api.call("POST", "/org/assignments", "CEO", json=body)) == "future"
    body["valid_from"] = "2025-01-15"
    assert reason(await api.call("POST", "/org/assignments", "CEO", json=body)) == (
        "not_after_current"
    )
    body |= {"valid_from": "2026-01-01", "manager_id": emp["id"]}
    assert reason(await api.call("POST", "/org/assignments", "CEO", json=body)) == "manager_self"
    body.pop("manager_id")
    new = data(await api.call("POST", "/org/assignments", "CEO", json=body), 201)
    q = {"employee_id": emp["id"], "as_of": "2025-12-31"}
    old = data(await api.call("GET", "/org/assignments", "CEO", params=q))
    assert [o["department_id"] for o in old] == [d1["id"]]
    assert (
        data(await api.call("GET", f"/hr/employees/{emp['id']}", "CEO"))["department_id"]
        == (d2["id"])
    )
    closed = data(await api.call("PATCH", f"/org/assignments/{new['id']}", "CEO",
                                 json={"valid_to": TODAY.isoformat(), "reason": "Nghỉ",
                                       "version": new["version"]}))  # fmt: skip
    assert closed["valid_to"] == TODAY.isoformat()
    bad = await api.call("GET", "/org/tree", "CEO", params={"as_of": "20-10-2026"})
    assert bad.status_code == 400


async def test_employee_patch_effective_from(api: ApiClient) -> None:
    d1, d2 = await make_department(api), await make_department(api)
    emp = await make_employee(api, d1["id"])
    body = {"department_id": d2["id"], "effective_from": "2026-02-01", "version": emp["version"]}
    data(await api.call("PATCH", f"/hr/employees/{emp['id']}", "HR_MANAGER", json=body))
    hist = data(await api.call("GET", "/org/assignments", "CEO",
                               params={"employee_id": emp["id"]}))  # fmt: skip
    assert [(h["department_id"], h["valid_from"], h["valid_to"]) for h in hist] == [
        (d1["id"], "2025-01-15", "2026-02-01"), (d2["id"], "2026-02-01", None)]  # fmt: skip


# ---------- TC-M12-04 tree ----------
async def test_tree_as_of_and_no_level4(api: ApiClient) -> None:
    tree = data(await api.call("GET", "/org/tree", "CEO", params={"as_of": "2026-10-20"}))
    assert tree["organization"]["code"] == "ABC"
    codes = {d["code"] for d in tree["departments"]}
    assert {"BOD", "SAL", "HR"} <= codes
    total = sum(d["headcount"] for d in tree["departments"])
    assert total == sum(len(d["members"]) for d in tree["departments"]) > 100
    member_keys = {k for d in tree["departments"] for m in d["members"] for k in m}
    assert not member_keys & {"email", "phone", "date_of_birth", "national_id", "bank_account"}
    early = data(await api.call("GET", "/org/tree", "CEO", params={"as_of": "2012-06-01"}))
    assert sum(d["headcount"] for d in early["departments"]) < total


# ---------- TC-M12-11 RBAC ----------
async def test_rbac(api: ApiClient) -> None:
    body = {"code": uniq("O"), "name": "x"}
    for role in ("MANAGER", "EMPLOYEE", "REVIEWER", "CFO"):
        r = await api.call("POST", "/org/organizations", role, json=body)
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_ROLE", role
    for role in ("EMPLOYEE", "REVIEWER"):
        r = await api.call("GET", "/org/tree", role)
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_SCOPE", role
    assert (await api.call("GET", "/org/tree", "VP_SALES")).status_code == 403
    # ADM: structure yes, records no (R-DEC-30)
    assert (await api.call("GET", "/org/tree", "ADMIN")).status_code == 200
    for url in ("/hr/employees", f"/hr/employees/{seed_uuid('employee', 'NV-0010')}",
                f"/hr/employees/{seed_uuid('employee', 'NV-0010')}/salary-history",
                "/hr/hiring-plans"):  # fmt: skip
        r = await api.call("GET", url, "ADMIN")
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_SCOPE", url
    # MGR sees own department subtree only
    mine = data(await api.call("GET", "/org/tree", "MANAGER", department_id=SAL))
    assert {d["id"] for d in mine["departments"]} == {SAL}
    q = {"department_id": str(seed_uuid("department", "HR"))}
    other = await api.call("GET", "/org/assignments", "MANAGER", department_id=SAL, params=q)
    assert other.status_code == 403


async def test_tenant_isolation(api: ApiClient) -> None:
    from tests.integration.test_tenant_isolation import TENANT_B

    dept = await make_department(api)
    team = data(await api.call("POST", "/org/teams", "CEO", json={
        "department_id": dept["id"], "code": uniq("T"), "name": "A"}), 201)  # fmt: skip
    for url in (f"/org/organizations/{ORG_ID}", f"/org/teams/{team['id']}"):
        assert (await api.call("GET", url, "CEO", tenant_id=TENANT_B)).status_code == 404
    other = await api.call("GET", "/org/tree", "CEO", tenant_id=TENANT_B)
    assert other.status_code == 404

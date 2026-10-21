"""T-121 — EP-81 departments, EP-82 employees, EP-83 salary history (TC-HR-001)."""

import json
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import ApiClient
from tests.integration.hr.helpers import (
    audit_rows,
    employee_body,
    events,
    make_department,
    make_employee,
    token_headers,
    uniq,
)

pytestmark = pytest.mark.integration
SALARY = 27_350_000
LEVEL4 = ("date_of_birth", "address", "national_id", "bank_account", "emergency_contact")


# ---------- EP-81 ----------
async def test_department_crud_and_cycle(api: ApiClient, db_session: AsyncSession) -> None:
    root = await make_department(api)
    child = await make_department(api, parent_id=root["id"])
    assert child["parent_id"] == root["id"] and child["version"] == 1
    dup = await api.call("POST", "/hr/departments", "HR_MANAGER",
                         json={"name": "x", "code": root["code"]})  # fmt: skip
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    bad_parent = await api.call(
        "POST",
        "/hr/departments",
        "HR_MANAGER",
        json={"name": "x", "code": uniq(), "parent_id": str(uuid.uuid4())},
    )
    assert bad_parent.status_code == 422

    cyc = await api.call("PATCH", f"/hr/departments/{root['id']}", "HR_MANAGER",
                         json={"parent_id": child["id"], "version": 1})  # fmt: skip
    assert cyc.status_code == 422 and cyc.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    self_loop = await api.call("PATCH", f"/hr/departments/{root['id']}", "HR_MANAGER",
                               json={"parent_id": root["id"], "version": 1})  # fmt: skip
    assert self_loop.status_code == 422

    emp = await make_employee(api, child["id"])
    p = await api.call("PATCH", f"/hr/departments/{child['id']}", "HR_MANAGER",
                       json={"name": "Đổi tên", "manager_id": emp["id"]},
                       headers={"If-Match": "1"})  # fmt: skip
    assert p.status_code == 200, p.text
    assert p.json()["data"]["manager_id"] == emp["id"] and p.json()["data"]["version"] == 2
    stale = await api.call("PATCH", f"/hr/departments/{child['id']}", "HR_MANAGER",
                           json={"name": "y", "version": 1})  # fmt: skip
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "CONFLICT_STATE"
    taken = await api.call("PATCH", f"/hr/departments/{child['id']}", "HR_MANAGER",
                           json={"code": root["code"], "version": 2})  # fmt: skip
    assert taken.status_code == 409

    got = await api.call("GET", f"/hr/departments/{child['id']}", "EMPLOYEE")
    assert got.status_code == 200 and got.json()["data"]["name"] == "Đổi tên"
    assert (await api.call("GET", f"/hr/departments/{uuid.uuid4()}", "CEO")).status_code == 404
    lst = await api.call("GET", "/hr/departments", "CEO",
                         params={"parent_id": root["id"], "sort_by": "name"})  # fmt: skip
    assert [d["id"] for d in lst.json()["data"]] == [child["id"]]
    assert lst.json()["meta"]["pagination"]["total"] == 1
    actions = sorted(a for a, *_ in await audit_rows(db_session, child["id"]))
    assert actions == ["hr.department_create", "hr.department_update"]


async def test_department_permissions(api: ApiClient) -> None:
    body = {"name": "x", "code": uniq()}
    assert (await api.call("POST", "/hr/departments", "CEO", json=body)).status_code == 403
    assert (await api.call("GET", "/hr/departments", "CFO")).status_code == 403
    assert (await api.call("GET", "/hr/departments", "ADMIN")).status_code == 403


# ---------- EP-82 ----------
async def test_employee_crud_onboard_terminate(api: ApiClient, db_session: AsyncSession) -> None:
    dept = await make_department(api)
    e = await make_employee(api, dept["id"], emergency_contact={"name": "Mẹ"})
    assert e["title"] == "Kế toán viên" and e["contract_type"] == "full_time"
    assert e["national_id"] == "079090001234" and e["status"] == "probation"
    assert await events(db_session, e["id"]) == []

    # same title in the same department reuses the position
    e2 = await make_employee(api, dept["id"], status="active")
    assert e2["title"] == "Kế toán viên"
    assert [t for t, _ in await events(db_session, e2["id"])] == ["hr.employee_onboarded"]

    on = await api.call("PATCH", f"/hr/employees/{e['id']}", "HR_MANAGER",
                        json={"status": "active", "contract_type": "contract",
                              "full_name": "Trần Thị Bình", "version": 1})  # fmt: skip
    assert on.status_code == 200, on.text
    assert on.json()["data"]["contract_type"] == "contract"
    evs = await events(db_session, e["id"], "hr.employee_onboarded")
    assert len(evs) == 1
    assert set(evs[0][1]) == {"employee_id", "department_id", "hire_date"}

    no_date = await api.call("PATCH", f"/hr/employees/{e['id']}", "HR_MANAGER",
                             json={"status": "terminated", "version": 2})  # fmt: skip
    assert no_date.status_code == 422
    early = await api.call("PATCH", f"/hr/employees/{e['id']}", "HR_MANAGER",
                           json={"status": "terminated", "termination_date": "2024-01-01",
                                 "version": 2})  # fmt: skip
    assert early.status_code == 422
    off = await api.call("PATCH", f"/hr/employees/{e['id']}", "HR_MANAGER",
                         json={"status": "terminated", "termination_date": "2026-09-30",
                               "title": "Kế toán trưởng", "version": 2})  # fmt: skip
    assert off.status_code == 200 and off.json()["data"]["title"] == "Kế toán trưởng"
    term = await events(db_session, e["id"], "hr.employee_terminated")
    assert len(term) == 1 and term[0][1]["termination_date"] == "2026-09-30"

    q = await api.call("GET", "/hr/employees", "CEO",
                       params={"q": "tran thi", "department_id": dept["id"],
                               "status": "terminated"})  # fmt: skip
    assert [x["id"] for x in q.json()["data"]] == [e["id"]]
    by_code = await api.call("GET", "/hr/employees", "CEO", params={"q": e2["employee_code"]})
    assert [x["id"] for x in by_code.json()["data"]] == [e2["id"]]

    assert (await api.call("DELETE", f"/hr/employees/{e['id']}", "HR_MANAGER")).status_code == 204
    assert (await api.call("GET", f"/hr/employees/{e['id']}", "CEO")).status_code == 404
    actions = sorted(a for a, *_ in await audit_rows(db_session, e["id"]))
    assert actions == ["hr.employee_create", "hr.employee_delete"] + ["hr.employee_update"] * 2


async def test_employee_validation(api: ApiClient) -> None:
    dept = await make_department(api)
    e = await make_employee(api, dept["id"])
    body = employee_body(dept["id"], employee_code=e["employee_code"])
    dup = await api.call("POST", "/hr/employees", "HR_MANAGER", json=body)
    assert dup.status_code == 409
    dup_mail = await api.call("POST", "/hr/employees", "HR_MANAGER",
                              json=employee_body(dept["id"], email=e["email"]))  # fmt: skip
    assert dup_mail.status_code == 409
    no_dept = await api.call("POST", "/hr/employees", "HR_MANAGER",
                             json=employee_body(str(uuid.uuid4())))  # fmt: skip
    assert no_dept.status_code == 422
    no_mgr = await api.call(
        "POST",
        "/hr/employees",
        "HR_MANAGER",
        json=employee_body(dept["id"], manager_id=str(uuid.uuid4())),
    )
    assert no_mgr.status_code == 422

    boss = await make_employee(api, dept["id"], manager_id=e["id"])
    loop = await api.call("PATCH", f"/hr/employees/{e['id']}", "HR_MANAGER",
                          json={"manager_id": boss["id"], "version": 1})  # fmt: skip
    assert loop.status_code == 422
    dup_code = await api.call(
        "PATCH",
        f"/hr/employees/{boss['id']}",
        "HR_MANAGER",
        json={"employee_code": e["employee_code"], "version": 1},
    )
    assert dup_code.status_code == 409
    no_title = await api.call(
        "PATCH",
        f"/hr/employees/{boss['id']}",
        "HR_MANAGER",
        json={"title": None, "contract_type": None, "version": 1},
    )
    assert no_title.status_code == 200 and no_title.json()["data"]["title"] is None
    assert no_title.json()["data"]["contract_type"] is None


async def test_level4_masking_by_role(api: ApiClient) -> None:
    dept = await make_department(api)
    e = await make_employee(api, dept["id"], emergency_contact={"phone": "0901234567"})
    for role in ("CEO", "HR_MANAGER"):
        d = (await api.call("GET", f"/hr/employees/{e['id']}", role)).json()["data"]
        assert d["address"] == "12 Lê Lợi, Q1" and d["bank_account"] == "0123456789012"
    mgr = await api.call("GET", f"/hr/employees/{e['id']}", "MANAGER",
                         department_id=uuid.UUID(dept["id"]))  # fmt: skip
    assert mgr.status_code == 200
    data = mgr.json()["data"]
    assert all(data[f] == {"masked": True} for f in LEVEL4)
    assert "079090001234" not in mgr.text and "12 Lê Lợi" not in mgr.text
    lst = await api.call("GET", "/hr/employees", "MANAGER", department_id=uuid.UUID(dept["id"]))
    assert all(x["national_id"] == {"masked": True} for x in lst.json()["data"])


async def test_employee_scoping(api: ApiClient) -> None:
    mine, other = await make_department(api), await make_department(api)
    a = await make_employee(api, mine["id"])
    b = await make_employee(api, other["id"])
    dep = uuid.UUID(mine["id"])
    lst = await api.call("GET", "/hr/employees", "MANAGER", department_id=dep)
    ids = {x["id"] for x in lst.json()["data"]}
    assert a["id"] in ids and b["id"] not in ids
    peek = await api.call("GET", "/hr/employees", "MANAGER", department_id=dep,
                          params={"department_id": other["id"]})  # fmt: skip
    assert peek.status_code == 403 and peek.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    one = await api.call("GET", f"/hr/employees/{b['id']}", "MANAGER", department_id=dep)
    assert one.status_code == 403
    assert (await api.call("GET", "/hr/employees", "MANAGER")).status_code == 403  # no dept

    me = token_headers("EMPLOYEE", email=a["email"].upper())
    own = await api.http.get(f"/api/v1/hr/employees/{a['id']}", headers=me)
    assert own.status_code == 200 and own.json()["data"]["address"] == {"masked": True}
    other_one = await api.http.get(f"/api/v1/hr/employees/{b['id']}", headers=me)
    assert other_one.status_code == 403
    mine_list = await api.http.get("/api/v1/hr/employees", headers=me)
    assert [x["id"] for x in mine_list.json()["data"]] == [a["id"]]

    rev = await api.call("GET", "/hr/employees", "REVIEWER")
    assert rev.status_code == 403 and rev.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    assert (await api.call("GET", f"/hr/employees/{a['id']}", "REVIEWER")).status_code == 403
    assert (await api.call("GET", "/hr/employees", "CFO")).status_code == 403
    w = await api.call("POST", "/hr/employees", "MANAGER", json=employee_body(mine["id"]))
    assert w.status_code == 403 and w.json()["error"]["code"] == "FORBIDDEN_ROLE"


# ---------- EP-83 ----------
async def test_salary_history_rules(api: ApiClient, db_session: AsyncSession) -> None:
    dept = await make_department(api)
    e = await make_employee(api, dept["id"])
    url = f"/hr/employees/{e['id']}/salary-history"
    body = {"effective_date": "2026-01-01", "base_salary": SALARY, "reason": "Tăng lương"}
    c = await api.call("POST", url, "HR_MANAGER", json=body)
    assert c.status_code == 201, c.text
    s = c.json()["data"]
    assert s["base_salary"] == SALARY and s["currency"] == "VND"
    dup = await api.call("POST", url, "HR_MANAGER", json=body)
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    zero = await api.call(
        "POST", url, "HR_MANAGER", json={**body, "base_salary": 0, "effective_date": "2026-02-01"}
    )
    assert zero.status_code == 422
    await api.call("POST", url, "HR_MANAGER", json={**body, "effective_date": "2026-07-01",
                                                    "base_salary": SALARY + 1})  # fmt: skip

    for role in ("CEO", "HR_MANAGER"):
        r = await api.call("GET", url, role, params={"sort_by": "effective_date", "order": "asc"})
        assert r.status_code == 200
        assert [x["effective_date"] for x in r.json()["data"]] == ["2026-01-01", "2026-07-01"]
    for role in ("MANAGER", "EMPLOYEE", "REVIEWER"):
        r = await api.call("GET", url, role, department_id=uuid.UUID(dept["id"]))
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_SALARY", role
        assert str(SALARY) not in r.text
    assert (await api.call("GET", url, "CFO")).status_code == 403
    missing = f"/hr/employees/{uuid.uuid4()}/salary-history"
    assert (await api.call("GET", missing, "CEO")).status_code == 404
    assert (await api.call("POST", missing, "HR_MANAGER", json=body)).status_code == 404

    evs = await events(db_session, s["id"], "hr.salary_updated")
    assert len(evs) == 1
    assert set(evs[0][1]) == {"employee_id", "department_id", "effective_date"}


async def test_no_salary_or_pii_leaks(api: ApiClient, db_session: AsyncSession) -> None:
    """No salary value in any outbox payload / non-privileged response; audit masks it."""
    dept = await make_department(api)
    e = await make_employee(api, dept["id"], status="active")
    url = f"/hr/employees/{e['id']}/salary-history"
    s = await api.call("POST", url, "HR_MANAGER",
                       json={"effective_date": "2026-03-01", "base_salary": SALARY})  # fmt: skip
    sid = s.json()["data"]["id"]
    off = await api.call("PATCH", f"/hr/employees/{e['id']}", "HR_MANAGER",
                         json={"status": "terminated", "termination_date": "2026-10-01",
                               "version": 1})  # fmt: skip
    assert off.status_code == 200

    payloads = [p for agg in (e["id"], sid) for _, p in await events(db_session, agg)]
    assert len(payloads) == 3
    dump = json.dumps(payloads)
    for secret in (str(SALARY), "079090001234", "0123456789012", e["email"], "Lê Lợi"):
        assert secret not in dump

    for role in ("MANAGER", "EMPLOYEE"):
        r = await api.call("GET", f"/hr/employees/{e['id']}", role,
                           department_id=uuid.UUID(dept["id"]))  # fmt: skip
        assert str(SALARY) not in r.text and "079090001234" not in r.text

    rows = await audit_rows(db_session, sid)
    assert rows and rows[0][2]["base_salary"] == "••••"
    assert str(SALARY) not in json.dumps([r[2] for r in rows])
    emp_rows = await audit_rows(db_session, e["id"])
    blob = json.dumps([[r[1], r[2]] for r in emp_rows], ensure_ascii=False)
    assert "079090001234" not in blob and "0123456789012" not in blob and "Lê Lợi" not in blob


async def test_idempotent_employee_create(api: ApiClient) -> None:
    dept = await make_department(api)
    body = employee_body(dept["id"])
    h = api.headers("HR_MANAGER", idem=True)
    r1 = await api.http.post("/api/v1/hr/employees", json=body, headers=h)
    r2 = await api.http.post("/api/v1/hr/employees", json=body, headers=h)
    assert r1.status_code == 201 and r1.json()["data"]["id"] == r2.json()["data"]["id"]
    no_key = await api.http.post("/api/v1/hr/employees", json=body,
                                 headers={"Authorization": h["Authorization"]})  # fmt: skip
    assert no_key.status_code == 400
    d = {"name": "Idem", "code": uniq()}
    h2 = api.headers("HR_MANAGER", idem=True)
    a = await api.http.post("/api/v1/hr/departments", json=d, headers=h2)
    b = await api.http.post("/api/v1/hr/departments", json=d, headers=h2)
    assert a.json()["data"]["id"] == b.json()["data"]["id"]
    sal = {"effective_date": "2026-01-01", "base_salary": SALARY}
    surl = f"/api/v1/hr/employees/{r1.json()['data']['id']}/salary-history"
    h3 = api.headers("HR_MANAGER", idem=True)
    s1 = await api.http.post(surl, json=sal, headers=h3)
    s2 = await api.http.post(surl, json=sal, headers=h3)
    assert s1.status_code == 201 and s1.json()["data"]["id"] == s2.json()["data"]["id"]

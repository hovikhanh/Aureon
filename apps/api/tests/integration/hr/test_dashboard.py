"""T-123 — EP-80 HR dashboard (10 §5) + EP-87 workload (TC-HR-004 integration part).

The DB is shared: company-wide numbers are asserted as deltas against a baseline taken in the
same rolled-back transaction; department-scoped (MANAGER) numbers are asserted exactly.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.models import Task
from tests.conftest import ApiClient
from tests.integration.execution.helpers import make_task
from tests.integration.hr.helpers import make_department, make_employee

pytestmark = pytest.mark.integration
P = {"period": "2026-09"}
SALARY_A, SALARY_B = 20_000_000, 30_000_000


async def dash(api: ApiClient, role: str, dept: Any = None, **params: str) -> dict[str, Any]:
    r = await api.call("GET", "/hr/dashboard", role, params={**P, **params},
                       department_id=dept)  # fmt: skip
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "private, max-age=60"
    assert r.headers["vary"] == "Authorization"
    return dict(r.json()["data"])


async def seed(api: ApiClient) -> str:
    dept = (await make_department(api))["id"]
    a = await make_employee(api, dept, status="active", hire_date="2024-09-01")
    b = await make_employee(api, dept, status="on_leave", hire_date="2025-03-01")
    await make_employee(api, dept, status="active", hire_date="2026-09-10")  # new hire
    await make_employee(api, dept, status="terminated", hire_date="2023-01-01",
                        termination_date="2026-09-20")  # fmt: skip
    await make_employee(api, dept, status="terminated", hire_date="2022-01-01",
                        termination_date="2026-03-31")  # fmt: skip
    for emp, amount in ((a, SALARY_A), (b, SALARY_B)):
        r = await api.call(
            "POST",
            f"/hr/employees/{emp['id']}/salary-history",
            "HR_MANAGER",
            json={"effective_date": "2026-01-01", "base_salary": amount},
        )
        assert r.status_code == 201
    late = await api.call("POST", "/hr/hiring-plans", "HR_MANAGER", json={
        "department_id": dept, "position": "Kỹ sư", "headcount": 2, "start_date": "2026-01-01",
        "target_date": "2026-02-01"})  # fmt: skip
    pid = late.json()["data"]["id"]
    await api.call("POST", f"/hr/hiring-plans/{pid}/submit", "HR_MANAGER")
    ok = await api.call("POST", f"/hr/hiring-plans/{pid}/approve", "CFO",
                        json={"decision": "approve", "reason": "ok"})  # fmt: skip
    assert ok.status_code == 200
    return str(dept)


async def test_dashboard_manager_exact(api: ApiClient) -> None:
    dept = await seed(api)
    d = await dash(api, "MANAGER", uuid.UUID(dept))
    s = d["summary"]
    assert d["pillar"] == "O" and d["period"]["key"] == "2026-09"
    assert d["period"]["start_date"] == "2026-09-01" and d["period"]["end_date"] == "2026-09-30"
    assert (s["headcount"], s["active"], s["on_leave"]) == (3, 2, 1)
    assert (s["terminated"], s["new_hires"], s["open_positions"]) == (1, 1, 2)
    # BR-HR-01: 1 leaver, headcount 31/08 = 3, 30/09 = 3 → 1/3 × 12 × 100
    assert s["turnover_rate_pct"] == 400.0
    assert s["avg_tenure_months"] == 14.0  # (24 + 18 + 0) / 3
    assert "payroll_total" not in s and s["revenue_per_employee"] is None
    assert d["status"] == "critical" and d["metrics"] == [] and d["open_alerts"] is None
    ht = d["headcount_trend"]
    assert len(ht) == 12 and ht[-1] == {"period_key": "2026-09", "headcount": 3}
    assert ht[0]["period_key"] == "2025-10" and ht[0]["headcount"] == 4
    tt = {p["period_key"]: p["turnover_rate_pct"] for p in d["turnover_trend"]}
    assert tt["2026-03"] == 342.9  # 1 / ((4 + 3) / 2) × 1200 and tt["2026-05"] == 0.0


async def test_dashboard_company_payroll_visibility(api: ApiClient) -> None:
    base = {r: (await dash(api, r))["summary"] for r in ("CEO", "CFO", "RISK_MANAGER")}
    await seed(api)
    ceo = (await dash(api, "CEO"))["summary"]
    assert ceo["headcount"] - base["CEO"]["headcount"] == 3
    assert ceo["payroll_total"] - base["CEO"]["payroll_total"] == SALARY_A + SALARY_B
    assert ceo["currency"] == "VND"
    cfo = (await dash(api, "CFO"))["summary"]
    assert cfo["payroll_total"] == ceo["payroll_total"]
    risk = await api.call("GET", "/hr/dashboard", "RISK_MANAGER", params=P)
    assert "payroll_total" not in risk.json()["data"]["summary"]
    assert str(SALARY_A) not in risk.text and str(SALARY_B) not in risk.text
    hr = await api.call("GET", "/hr/dashboard", "HR_MANAGER", params={"period": "current_quarter"})
    assert hr.status_code == 200 and "payroll_total" in hr.json()["data"]["summary"]


async def test_dashboard_permissions_and_params(api: ApiClient) -> None:
    for role in ("EMPLOYEE", "VP_SALES", "ADMIN", "REVIEWER"):
        r = await api.call("GET", "/hr/dashboard", role)
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_ROLE", role
    bad = await api.call("GET", "/hr/dashboard", "CEO", params={"period": "custom"})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "BAD_REQUEST"
    no_dept = await api.call("GET", "/hr/dashboard", "MANAGER")
    assert no_dept.status_code == 403 and no_dept.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    default = await api.call("GET", "/hr/dashboard", "CEO")
    assert default.json()["data"]["period"]["type"] == "current_month"


async def test_workload_from_execution(api: ApiClient, db_session: AsyncSession) -> None:
    """EP-87 reads execution workload via its public service (T-133 merge)."""
    dept, busy, calm = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    ids = [await make_task(api, assignee_id=str(busy), department_id=str(dept),
                           estimate_hours="30") for _ in range(2)]  # fmt: skip
    ids.append(await make_task(api, assignee_id=str(calm), department_id=str(dept)))
    back = datetime(2026, 9, 1, tzinfo=UTC)  # open across both weeks before 30/09
    await db_session.execute(update(Task).where(Task.id.in_([uuid.UUID(t["id"]) for t in ids]))
                             .values(created_at=back))  # fmt: skip
    r = await api.call("GET", "/hr/workload", "MANAGER", department_id=dept,
                       params={"period": "2026-09", "department_id": str(dept)})  # fmt: skip
    assert r.status_code == 200, r.text
    rows = r.json()["data"]
    assert rows[0] == {"employee_ref": str(busy), "open_tasks": 2, "load_pct": 150.0,
                       "overloaded": True}  # fmt: skip
    assert rows[1] == {"employee_ref": str(calm), "open_tasks": 1, "load_pct": 10.0,
                       "overloaded": False}  # fmt: skip


async def test_workload_scope(api: ApiClient) -> None:
    dept = uuid.uuid4()
    r = await api.call("GET", "/hr/workload", "HR_MANAGER", params={"period": "2026-09"})
    assert r.status_code == 200 and isinstance(r.json()["data"], list)
    assert r.headers.get("cache-control") != "private, max-age=60"
    own = await api.call("GET", "/hr/workload", "MANAGER", department_id=dept,
                         params={"department_id": str(dept)})  # fmt: skip
    assert own.status_code == 200
    other = await api.call("GET", "/hr/workload", "MANAGER", department_id=dept,
                           params={"department_id": str(uuid.uuid4())})  # fmt: skip
    assert other.status_code == 403
    assert (await api.call("GET", "/hr/workload", "EMPLOYEE")).status_code == 403
    assert (
        await api.call("GET", "/hr/workload", "CEO", params={"period": "bad"})
    ).status_code == 400

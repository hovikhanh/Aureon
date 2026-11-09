"""TC-V4-17 — D-21 / R-DEC-198: the CEO creates, reads (list + detail), updates and deletes every
business record of every module, with no ownership / department limit.

Business integrity stays: where a hard delete would orphan data or break an invariant, the
module's own archive / soft delete / state rule applies and the API answers with a business error
(`409 CONFLICT_STATE`, `422 BUSINESS_RULE_VIOLATION`) — never a permission error.

All calls run as one CEO identity (`CEO`), except the hiring-plan decision which the approval
engine reserves for someone other than the requester (separation of duties, R-DEC-173).
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.modules.platform.services.metric_store import MetricStore
from app.workers.consumers import load_metric_providers
from tests.conftest import ApiClient
from tests.integration.hr.helpers import ORG_ID, employee_body
from tests.integration.hr.helpers import uniq as hr_uniq

pytestmark = pytest.mark.integration

CEO = uuid.uuid4()
TODAY = datetime.now(UTC).date()
FUTURE = (TODAY + timedelta(days=30)).isoformat()


@pytest.fixture(autouse=True)
def _business_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_config(), "business_date_override", TODAY)


def _u(prefix: str = "X") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


async def ceo(
    api: ApiClient, method: str, url: str, *, json: Any = None, params: Any = None,
    user_id: uuid.UUID = CEO,
) -> Any:  # fmt: skip
    h = api.headers("CEO", user_id=user_id, idem=method == "POST")
    return await api.http.request(method, f"/api/v1{url}", json=json, params=params, headers=h)


def ok(r: Any, status: int = 200) -> Any:
    assert r.status_code == status, f"{r.request.method} {r.request.url} → {r.text}"
    return None if status == 204 else r.json()["data"]


def refused(r: Any, status: int, code: str) -> None:
    assert r.status_code == status, f"{r.request.method} {r.request.url} → {r.text}"
    assert r.json()["error"]["code"] == code, r.text


async def in_list(api: ApiClient, url: str, id_: str, params: dict[str, Any] | None = None) -> bool:
    """Walk every page of a list endpoint (default page = 20) looking for `id_`."""
    offset = 0
    while True:
        r = await ceo(api, "GET", url, params={**(params or {}), "limit": 100, "offset": offset})
        rows = ok(r)
        if any(x["id"] == id_ for x in rows):
            return True
        if not ((r.json().get("meta") or {}).get("pagination") or {}).get("has_next"):
            return False
        offset += 100


async def crud(
    api: ApiClient, base: str, body: dict[str, Any], patch: dict[str, Any], *,
    list_params: dict[str, Any] | None = None, delete: bool = True,
) -> dict[str, Any]:  # fmt: skip
    """C → R (list + detail) → U → (D → 404 and gone from the list)."""
    made = ok(await ceo(api, "POST", base, json=body), 201)
    url = f"{base}/{made['id']}"
    assert ok(await ceo(api, "GET", url))["id"] == made["id"]
    assert await in_list(api, base, made["id"], list_params), base
    up = ok(await ceo(api, "PATCH", url, json={**patch, "version": made["version"]}))
    for k, v in patch.items():
        assert up[k] == v, (base, k, up[k])
    assert ok(await ceo(api, "GET", url))["version"] == made["version"] + 1
    if delete:
        ok(await ceo(api, "DELETE", url), 204)
        assert (await ceo(api, "GET", url)).status_code == 404
        assert not await in_list(api, base, made["id"], list_params)
    return dict(up)


# ---------------------------------------------------------------- finance
async def test_ceo_finance_crud(api: ApiClient) -> None:
    await crud(api, "/finance/revenues",
               {"amount": 1_500_000_000, "category": "service", "recognized_on": "2061-03-10"},
               {"amount": 1_600_000_000})  # fmt: skip
    dept = str(uuid.uuid4())
    await crud(api, "/finance/expenses",
               {"title": "Thuê kho", "amount": 50_000_000, "category": "office",
                "department_id": dept, "spent_on": "2061-03-12"},
               {"amount": 55_000_000}, list_params={"department_id": dept})  # fmt: skip
    # cash position: no DELETE endpoint (EP-65 — a period's closing balance is corrected, not
    # removed)
    cash = await crud(api, "/finance/cash-positions",
                      {"period": "2061-03", "closing_balance": 9_000_000_000,
                       "cash_source": "bank_statement"},
                      {"closing_balance": 8_500_000_000}, delete=False)  # fmt: skip
    assert (await ceo(api, "DELETE", f"/finance/cash-positions/{cash['id']}")).status_code == 405
    await crud(api, "/finance/budgets",
               {"department_id": dept, "fiscal_year": 2061, "quarter": "Q1",
                "allocated_amount": 1_000_000_000, "category": "marketing"},
               {"allocated_amount": 1_200_000_000},
               list_params={"department_id": dept})  # fmt: skip
    # forecast: no DELETE endpoint (EP-66 — a new forecast supersedes the old one)
    await crud(api, "/finance/forecasts",
               {"scenario": "base", "horizon": "3m", "confidence_pct": 75,
                "lines": [{"period_key": f"2061-0{m}", "revenue": 1000, "expense": 800}
                          for m in (1, 2, 3)]},
               {"confidence_pct": 90}, delete=False)  # fmt: skip

    inv_body = {
        "client_id": str(uuid.uuid4()), "client_name": "Cty XYZ", "number": _u("HD"),
        "issued_on": "2061-03-01", "due_date": "2061-04-01", "status": "sent",
        "lines": [{"description": "Máy in", "quantity": 2, "unit_price": 10_000_000}],
    }  # fmt: skip
    inv = await crud(api, "/finance/invoices", inv_body, {"notes": "CEO sửa"}, delete=False)
    url = f"/finance/invoices/{inv['id']}"
    paid = ok(
        await ceo(
            api,
            "POST",
            f"{url}/pay",
            json={"amount_paid": 5_000_000, "paid_at": "2061-03-15T00:00:00Z"},
        )
    )
    assert paid["paid_amount"] == 5_000_000
    # integrity: an invoice with payments cannot be deleted → business error, not 403
    refused(await ceo(api, "DELETE", url), 409, "CONFLICT_STATE")
    draft = ok(
        await ceo(
            api,
            "POST",
            "/finance/invoices",
            json={**inv_body, "number": _u("HD"), "status": "draft"},
        ),
        201,
    )
    ok(await ceo(api, "DELETE", f"/finance/invoices/{draft['id']}"), 204)
    assert (await ceo(api, "GET", f"/finance/invoices/{draft['id']}")).status_code == 404


async def test_ceo_revenue_write_moves_the_finance_dashboard(
    api: ApiClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A CEO-entered revenue + target shows in METRIC-FIN-01 live and after the store recompute."""
    today, closed = date(2062, 5, 20), "2062-04"
    monkeypatch.setattr(get_config(), "business_date_override", today)

    def fin01(metrics: list[dict[str, Any]]) -> dict[str, Any]:
        return next(m for m in metrics if m["metric_code"] == "METRIC-FIN-01")

    before = fin01(ok(await ceo(api, "GET", "/finance/dashboard"))["metrics"])
    assert before["value"] is None
    ok(
        await ceo(
            api,
            "POST",
            "/finance/revenues",
            json={"amount": 900_000_000, "category": "service", "recognized_on": "2062-04-15"},
        ),
        201,
    )
    ok(await ceo(api, "POST", "/sales/targets", json={
        "period_type": "month", "period_key": closed, "scope": "team",
        "target_amount": 1_000_000_000}), 201)  # fmt: skip
    after = fin01(ok(await ceo(api, "GET", "/finance/dashboard"))["metrics"])
    assert (after["value"], after["period_key"]) == (90.0, closed)

    load_metric_providers()  # what the worker / beat job loads before `recompute_metrics`
    await MetricStore(db_session).recompute(today, {"finance", "sales"})
    await db_session.flush()
    stored = ok(await ceo(api, "GET", "/dashboard/metrics", params={"period": closed}))
    assert (fin01(stored)["value"], fin01(stored)["period_key"]) == (90.0, closed)


# ---------------------------------------------------------------- sales
async def test_ceo_sales_crud(api: ApiClient) -> None:
    client = await crud(api, "/sales/clients", {"name": _u("Cty")}, {"name": _u("Cty")},
                        delete=False)  # fmt: skip
    cid = client["id"]
    deal_body = {"name": _u("Deal"), "client_id": cid, "deal_value": 800_000_000,
                 "probability_pct": 20, "expected_close_date": FUTURE,
                 "owner_id": str(uuid.uuid4())}  # fmt: skip
    deal = await crud(api, "/sales/deals", deal_body, {"deal_value": 900_000_000}, delete=False,
                      list_params={"client_id": cid})  # fmt: skip
    did = deal["id"]
    moved = ok(await ceo(api, "POST", f"/sales/deals/{did}/stage", json={"to_stage": "qualified"}))
    assert moved["stage"] == "qualified"
    assert ok(await ceo(api, "GET", f"/sales/deals/{did}/stage-history"))

    contract = await crud(api, "/sales/contracts", {
        "contract_number": _u("HD"), "client_id": cid, "deal_id": did,
        "contract_value": 1_200_000_000, "signed_at": "2026-09-01",
        "effective_date": "2026-09-05", "expiry_date": "2027-09-04", "status": "active",
    }, {"contract_value": 1_300_000_000}, list_params={"client_id": cid})  # fmt: skip
    assert contract["contract_value"] == 1_300_000_000

    ok(await ceo(api, "DELETE", f"/sales/deals/{did}"), 204)  # D-21: the CEO deletes deals
    assert (await ceo(api, "GET", f"/sales/deals/{did}")).status_code == 404
    ok(await ceo(api, "DELETE", f"/sales/clients/{cid}"), 204)
    assert (await ceo(api, "GET", f"/sales/clients/{cid}")).status_code == 404

    await crud(api, "/sales/targets",
               {"period_type": "month", "period_key": "2061-02", "scope": "team",
                "target_amount": 5_000_000_000},
               {"target_amount": 6_000_000_000})  # fmt: skip


async def test_ceo_sales_delete_keeps_integrity(api: ApiClient) -> None:
    """A client with live deals is not hard-deleted — business error, not permission."""
    c = ok(await ceo(api, "POST", "/sales/clients", json={"name": _u("Cty")}), 201)
    ok(await ceo(api, "POST", "/sales/deals", json={
        "name": _u("Deal"), "client_id": c["id"], "deal_value": 1, "probability_pct": 20,
        "expected_close_date": FUTURE, "owner_id": str(uuid.uuid4())}), 201)  # fmt: skip
    refused(await ceo(api, "DELETE", f"/sales/clients/{c['id']}"), 409, "CONFLICT_STATE")
    assert ok(await ceo(api, "GET", f"/sales/clients/{c['id']}"))["id"] == c["id"]


# ---------------------------------------------------------------- hr
async def test_ceo_hr_crud(api: ApiClient) -> None:
    dept = await crud(api, "/hr/departments",
                      {"name": "Phòng CEO lập", "code": hr_uniq("D"), "organization_id": ORG_ID},
                      {"name": "Phòng CEO sửa"}, delete=False)  # fmt: skip
    did = dept["id"]
    emp = await crud(api, "/hr/employees", employee_body(did), {"title": "Trưởng nhóm"},
                     list_params={"department_id": did}, delete=False)  # fmt: skip
    assert emp["date_of_birth"] == "1990-05-01"  # level-4 field visible to the CEO (ROLE-01)

    sal_url = f"/hr/employees/{emp['id']}/salary-history"
    s = ok(await ceo(api, "POST", sal_url, json={"effective_date": "2026-01-01",
                                                 "base_salary": 30_000_000}), 201)  # fmt: skip
    assert [x["id"] for x in ok(await ceo(api, "GET", sal_url))] == [s["id"]]
    assert ok(await ceo(api, "GET", sal_url))[0]["base_salary"] == 30_000_000

    # a department with a live employee is not archived (FR-ORG-03) → business error
    refused(await ceo(api, "DELETE", f"/hr/departments/{did}"), 422, "BUSINESS_RULE_VIOLATION")
    ok(await ceo(api, "DELETE", f"/hr/employees/{emp['id']}"), 204)  # soft delete
    assert (await ceo(api, "GET", f"/hr/employees/{emp['id']}")).status_code == 404
    empty = ok(
        await ceo(
            api,
            "POST",
            "/hr/departments",
            json={"name": "Phòng trống", "code": hr_uniq("D"), "organization_id": ORG_ID},
        ),
        201,
    )
    ok(await ceo(api, "DELETE", f"/hr/departments/{empty['id']}"), 204)
    assert (await ceo(api, "GET", f"/hr/departments/{empty['id']}")).status_code == 404


async def test_ceo_hiring_plan_lifecycle(api: ApiClient) -> None:
    dept = ok(
        await ceo(
            api,
            "POST",
            "/hr/departments",
            json={"name": "Phòng tuyển", "code": hr_uniq("D"), "organization_id": ORG_ID},
        ),
        201,
    )
    body = {"department_id": dept["id"], "position": "Kỹ sư", "headcount": 2,
            "salary_min": 15_000_000, "salary_max": 25_000_000, "start_date": "2026-08-01",
            "target_date": "2026-09-30", "priority": "high",
            "budget_amount": 600_000_000}  # fmt: skip
    plan = await crud(api, "/hr/hiring-plans", body, {"headcount": 3}, delete=False,
                      list_params={"department_id": dept["id"]})  # fmt: skip
    url = f"/hr/hiring-plans/{plan['id']}"
    sub = ok(await ceo(api, "POST", f"{url}/submit"))
    assert sub["status"] == "submitted"
    # the approval engine never lets the requester decide their own request (SoD, R-DEC-173)
    approver = uuid.uuid4()
    dec = ok(await ceo(api, "POST", f"{url}/approve", user_id=approver,
                       json={"decision": "approve", "reason": "Đủ ngân sách"}))  # fmt: skip
    assert dec["status"] == "approved"
    other = ok(await ceo(api, "POST", "/hr/hiring-plans", json=body), 201)
    ok(await ceo(api, "DELETE", f"/hr/hiring-plans/{other['id']}"), 204)
    assert (await ceo(api, "GET", f"/hr/hiring-plans/{other['id']}")).status_code == 404


async def test_ceo_org_structure_crud(api: ApiClient) -> None:
    await crud(api, "/org/organizations", {"code": hr_uniq("O"), "name": "Công ty con"},
               {"name": "Công ty con 2"}, list_params={"include_archived": "false"})  # fmt: skip
    dept = ok(
        await ceo(
            api,
            "POST",
            "/hr/departments",
            json={"name": "Phòng tổ chức", "code": hr_uniq("D"), "organization_id": ORG_ID},
        ),
        201,
    )
    did = dept["id"]
    team = await crud(api, "/org/teams", {"department_id": did, "code": hr_uniq("T"),
                                          "name": "Team A"}, {"name": "Team B"},
                      list_params={"department_id": did}, delete=False)  # fmt: skip
    pos = await crud(api, "/org/positions", {"department_id": did, "code": hr_uniq("P"),
                                             "title": "Chuyên viên", "headcount_budget": 2},
                     {"headcount_budget": 3}, list_params={"department_id": did},
                     delete=False)  # fmt: skip
    emp = ok(await ceo(api, "POST", "/hr/employees", json=employee_body(did)), 201)
    a = ok(await ceo(api, "POST", "/org/assignments", json={
        "employee_id": emp["id"], "department_id": did, "team_id": team["id"],
        "position_id": pos["id"],
        "valid_from": (TODAY - timedelta(days=1)).isoformat()}), 201)  # fmt: skip
    hist = ok(await ceo(api, "GET", "/org/assignments", params={"employee_id": emp["id"]}))
    assert a["id"] in {h["id"] for h in hist}
    # assignments have no DELETE: history is closed with valid_to (effective-dated, FR-DATA-07)
    closed = ok(
        await ceo(
            api,
            "PATCH",
            f"/org/assignments/{a['id']}",
            json={"valid_to": TODAY.isoformat(), "reason": "Đổi vị trí", "version": a["version"]},
        )
    )
    assert closed["valid_to"] == TODAY.isoformat()
    # integrity: team / position with a live child are archived only when empty
    ok(await ceo(api, "DELETE", f"/org/teams/{team['id']}"), 204)
    ok(await ceo(api, "DELETE", f"/org/positions/{pos['id']}"), 204)


async def test_ceo_user_admin(api: ApiClient) -> None:
    email = f"ceo-{uuid.uuid4().hex[:8]}@abc.test"
    u = ok(await ceo(api, "POST", "/platform/users", json={
        "email": email, "full_name": "Người dùng CEO tạo", "role_code": "MGR",
        "initial_password": "Mat-khau-dai-12345"}), 201)  # fmt: skip
    url = f"/platform/users/{u['id']}"
    assert ok(await ceo(api, "GET", url))["email"] == email
    assert u["id"] in {
        x["id"] for x in ok(await ceo(api, "GET", "/platform/users", params={"q": email}))
    }
    up = ok(await ceo(api, "PATCH", url, json={"full_name": "Đổi tên", "version": u["version"]}))
    assert up["full_name"] == "Đổi tên"
    # users are deactivated, never hard-deleted (audit trail, EP-ADM-09)
    off = ok(await ceo(api, "POST", f"{url}/deactivate", json={"reason": "Nghỉ việc"}))
    assert off["is_active"] is False
    back = ok(await ceo(api, "POST", f"{url}/reactivate", json={"reason": "Quay lại"}))
    assert back["is_active"] is True


# ---------------------------------------------------------------- product
async def test_ceo_product_crud(api: ApiClient) -> None:
    owner = str(uuid.uuid4())
    p = await crud(api, "/product/products", {"code": _u("P"), "name": "SP CEO", "owner_id": owner},
                   {"name": "SP CEO 2"}, delete=False)  # fmt: skip
    pid = p["id"]
    await crud(api, "/product/features", {"product_id": pid, "name": "Báo giá"},
               {"name": "Báo giá nhanh"}, list_params={"product_id": pid})  # fmt: skip
    await crud(api, "/product/roadmap-items",
               {"product_id": pid, "title": "QR", "quarter": "2061-Q1",
                "target_date": "2061-03-15"},
               {"title": "QR v2"}, list_params={"product_id": pid})  # fmt: skip
    # release: no DELETE (a version is history; it moves through its status)
    rel = await crud(api, "/product/releases", {"product_id": pid, "release_version": "1.0.0"},
                     {"release_version": "1.0.1"}, list_params={"product_id": pid},
                     delete=False)  # fmt: skip
    murl = f"/product/products/{pid}/metrics"
    m = ok(await ceo(api, "POST", murl, json={"period_key": "2061-03", "mau": 1200,
                                              "churn_rate_pct": 2.5}), 201)  # fmt: skip
    assert m["id"] in {x["id"] for x in ok(await ceo(api, "GET", murl))}
    # integrity (05 §5.4): a product with an open release is not deleted → business error
    refused(await ceo(api, "DELETE", f"/product/products/{pid}"), 422, "BUSINESS_RULE_VIOLATION")
    ok(await ceo(api, "PATCH", f"/product/releases/{rel['id']}", json={
        "status": "released", "released_at": "2061-03-20T00:00:00Z",
        "version": rel["version"]}))  # fmt: skip
    ok(await ceo(api, "DELETE", f"/product/products/{pid}"), 204)
    assert (await ceo(api, "GET", f"/product/products/{pid}")).status_code == 404


# ---------------------------------------------------------------- risk
async def test_ceo_risk_crud(api: ApiClient) -> None:
    owner = str(uuid.uuid4())
    r = await crud(api, "/risk/risks", {"title": _u("Risk"), "category": "financial",
                                        "likelihood": 3, "impact": 4, "owner_id": owner},
                   {"title": _u("Risk2")}, delete=False)  # fmt: skip
    rid = r["id"]
    aurl = f"/risk/risks/{rid}/assessments"
    a = ok(await ceo(api, "POST", aurl, json={"likelihood": 4, "impact": 4}), 201)
    assert a["id"] in {x["id"] for x in ok(await ceo(api, "GET", aurl))}
    await crud(api, "/risk/mitigations", {"risk_id": rid, "title": "Giảm thiểu",
                                          "owner_id": owner, "due_date": FUTURE},
               {"progress_pct": 50.0}, list_params={"risk_id": rid}, delete=False)  # fmt: skip
    sc = ok(
        await ceo(api, "POST", "/risk/scenarios", json={"risk_ids": [rid], "horizon_months": 3}),
        201,
    )
    assert sc["scenario_id"]
    acc = ok(await ceo(api, "POST", f"/risk/risks/{rid}/accept", json={"reason": "Chấp nhận"}))
    assert acc["status"] == "accepted"
    # risks / mitigations have no DELETE: a risk is closed (register history, FR-RSK-01)
    other = ok(await ceo(api, "POST", "/risk/risks", json={
        "title": _u("Risk"), "category": "operational", "likelihood": 2, "impact": 2,
        "owner_id": owner}), 201)  # fmt: skip
    done = ok(await ceo(api, "POST", f"/risk/risks/{other['id']}/status",
                        json={"to_status": "closed"}))  # fmt: skip
    assert done["status"] == "closed"


# ---------------------------------------------------------------- execution / goals
async def test_ceo_goals_crud(api: ApiClient) -> None:
    owner = str(uuid.uuid4())
    strat = await crud(api, "/goals/strategies", {
        "code": _u("STR"), "name": "Chiến lược", "period_start": "2061-01-01",
        "period_end": "2062-01-01", "owner_id": owner}, {"name": "Chiến lược 2"},
        delete=False)  # fmt: skip
    so = await crud(api, "/goals/strategic-objectives", {
        "strategy_id": strat["id"], "code": _u("SO"), "title": "MTCL", "owner_id": owner},
        {"title": "MTCL 2"}, delete=False)  # fmt: skip
    obj = await crud(api, "/objectives", {"title": "Tăng trưởng", "owner_id": owner,
                                          "period_key": "2061-Q1"},
                     {"title": "Tăng trưởng 2"}, delete=False)  # fmt: skip
    oid = obj["id"]
    kr = ok(
        await ceo(
            api,
            "POST",
            f"/objectives/{oid}/key-results",
            json={"title": "KR", "baseline": 0, "target": 100, "unit": "%", "owner_id": owner},
        ),
        201,
    )
    assert kr["id"] in {
        x["id"] for x in ok(await ceo(api, "GET", f"/objectives/{oid}/key-results"))
    }
    kr2 = ok(await ceo(api, "PATCH", f"/key-results/{kr['id']}",
                       json={"target": 120, "version": kr["version"]}))  # fmt: skip
    assert kr2["target"] == 120
    kr_b = ok(await ceo(api, "POST", f"/objectives/{oid}/key-results", json={
        "title": "KR2", "baseline": 0, "target": 10, "unit": "%", "owner_id": owner,
        "weight_pct": 0}), 201)  # fmt: skip
    ok(
        await ceo(
            api, "PATCH", f"/objectives/{oid}", json={"status": "active", "version": obj["version"]}
        )
    )
    ci = ok(await ceo(api, "POST", f"/key-results/{kr['id']}/check-ins",
                      json={"value": 40, "confidence": "HIGH"}), 201)  # fmt: skip
    assert ci["id"] in {
        x["id"]
        for x in ok(await ceo(api, "GET", "/goals/check-ins", params={"key_result_id": kr["id"]}))
    }
    # integrity: an objective with key results is not deleted
    refused(await ceo(api, "DELETE", f"/objectives/{oid}"), 409, "CONFLICT_STATE")
    ok(await ceo(api, "DELETE", f"/key-results/{kr['id']}"), 204)
    ok(await ceo(api, "DELETE", f"/key-results/{kr_b['id']}"), 204)

    kpi = await crud(api, "/kpis", {"code": _u("KPI"), "name": "Giao đúng hạn", "unit": "%",
                                    "target": 95, "owner_id": owner},
                     {"target": 97}, delete=False)  # fmt: skip
    kurl = f"/kpis/{kpi['id']}"
    mm = ok(await ceo(api, "POST", f"{kurl}/measurements",
                      json={"period_key": "2061-02", "actual_value": 90}), 201)  # fmt: skip
    assert mm["id"] in {x["id"] for x in ok(await ceo(api, "GET", f"{kurl}/measurements"))}
    tg = ok(
        await ceo(
            api,
            "POST",
            f"{kurl}/targets",
            json={"period_key": "2061-03", "valid_from": "2061-03-01", "target": 98},
        ),
        201,
    )
    assert tg["id"] in {x["id"] for x in ok(await ceo(api, "GET", f"{kurl}/targets"))}
    ok(await ceo(api, "POST", f"{kurl}/check-ins", json={"value": 96, "confidence": "HIGH"}), 201)
    assert ok(await ceo(api, "GET", f"{kurl}/check-ins"))
    ok(await ceo(api, "DELETE", kurl), 204)
    assert (await ceo(api, "GET", kurl)).status_code == 404
    ok(await ceo(api, "DELETE", f"/objectives/{oid}"), 204)
    ok(await ceo(api, "DELETE", f"/goals/strategic-objectives/{so['id']}"), 204)
    ok(await ceo(api, "DELETE", f"/goals/strategies/{strat['id']}"), 204)
    assert (await ceo(api, "GET", f"/goals/strategies/{strat['id']}")).status_code == 404


async def test_ceo_work_crud(api: ApiClient) -> None:
    owner = str(uuid.uuid4())
    await crud(api, "/work/tasks", {"title": _u("Task")}, {"title": _u("Task2")})
    await crud(api, "/work/projects", {
        "code": _u("PRJ"), "name": "ABC Order v3", "owner_id": owner,
        "start_date": "2061-01-01", "due_date": "2061-06-30", "status": "active"},
        {"name": "ABC Order v4"})  # fmt: skip
    held = "2061-03-01T08:00:00Z"
    m = await crud(api, "/execution/meetings", {"title": "Giao ban", "held_at": held},
                   {"title": "Giao ban T3"}, delete=False)  # fmt: skip
    d = await crud(api, "/execution/decisions", {
        "meeting_id": m["id"], "content": "Mở chi nhánh", "decided_at": held,
        "owner_id": owner}, {"content": "Mở chi nhánh Đà Nẵng"}, delete=False)  # fmt: skip
    # decisions have no DELETE (Decision Log 30/60/90 history) — closed by status
    closed = ok(
        await ceo(
            api,
            "PATCH",
            f"/execution/decisions/{d['id']}",
            json={"status": "cancelled", "version": d["version"]},
        )
    )
    assert closed["status"] == "cancelled"
    # integrity: a meeting with a decision is not deleted
    refused(await ceo(api, "DELETE", f"/execution/meetings/{m['id']}"), 409, "CONFLICT_STATE")
    lone = ok(
        await ceo(api, "POST", "/execution/meetings", json={"title": "x", "held_at": held}), 201
    )
    ok(await ceo(api, "DELETE", f"/execution/meetings/{lone['id']}"), 204)
    await crud(api, "/calendar/events", {"title": "Họp HĐQT", "starts_at": held},
               {"title": "Họp HĐQT Q1"})  # fmt: skip

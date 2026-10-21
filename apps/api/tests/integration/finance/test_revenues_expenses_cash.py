"""T-101 — EP-61 revenues, EP-62 expenses, EP-65 cash positions (FR-FIN-01/02/04)."""

import uuid
from typing import Any

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_LOGS
from app.modules.finance.models import CashPosition
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration

REV = {"amount": 1_500_000_000, "category": "product_sales", "recognized_on": "2026-09-30"}


async def _audit_actions(db: AsyncSession, target_id: str) -> list[str]:
    rows = await db.execute(
        select(AUDIT_LOGS.c.action).where(AUDIT_LOGS.c.target_id == uuid.UUID(target_id))
    )
    return sorted(r[0] for r in rows)


# ---------- revenues ----------
async def test_revenue_crud_roundtrip(api: ApiClient, db_session: AsyncSession) -> None:
    r = await api.call("POST", "/finance/revenues", json=REV)
    assert r.status_code == 201, r.text
    rev = r.json()["data"]
    assert rev["period"] == "2026-09" and rev["currency"] == "VND" and rev["version"] == 1
    rid = rev["id"]

    got = await api.call("GET", f"/finance/revenues/{rid}")
    assert got.json()["data"]["amount"] == 1_500_000_000

    p = await api.call(
        "PATCH", f"/finance/revenues/{rid}",
        json={"amount": 1_600_000_000, "recognized_on": "2026-10-01", "version": 1},
    )  # fmt: skip
    assert p.status_code == 200, p.text
    assert p.json()["data"]["period"] == "2026-10" and p.json()["data"]["version"] == 2

    stale = await api.call("PATCH", f"/finance/revenues/{rid}", json={"amount": 9, "version": 1})
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "CONFLICT_STATE"

    d = await api.call("DELETE", f"/finance/revenues/{rid}")
    assert d.status_code == 204
    assert (await api.call("GET", f"/finance/revenues/{rid}")).status_code == 404
    assert await _audit_actions(db_session, rid) == [
        "finance.revenue_create", "finance.revenue_delete", "finance.revenue_update",
    ]  # fmt: skip


@pytest.mark.parametrize("amount", [0, -5])
async def test_revenue_amount_must_be_positive(api: ApiClient, amount: int) -> None:
    r = await api.call("POST", "/finance/revenues", json={**REV, "amount": amount})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


async def test_revenue_list_filters_and_pagination(api: ApiClient) -> None:
    client = str(uuid.uuid4())
    for day, cat in (("2026-08-05", "service"), ("2026-09-05", "service"), ("2026-09-06", "other")):
        body = {**REV, "recognized_on": day, "category": cat, "client_id": client}
        assert (await api.call("POST", "/finance/revenues", json=body)).status_code == 201
    r = await api.call(
        "GET", "/finance/revenues",
        params={"client_id": client, "period": "2026-09", "limit": 1, "sort_by": "recognized_on"},
    )  # fmt: skip
    body = r.json()
    assert r.status_code == 200
    assert body["meta"]["pagination"] == {"total": 2, "limit": 1, "offset": 0, "has_next": True}
    assert body["data"][0]["recognized_on"] == "2026-09-06"
    r2 = await api.call(
        "GET", "/finance/revenues", params={"client_id": client, "category": "other"}
    )
    assert r2.json()["meta"]["pagination"]["total"] == 1
    bad = await api.call("GET", "/finance/revenues", params={"period": "2026-13"})
    assert bad.status_code == 400


async def test_revenue_permissions(api: ApiClient) -> None:
    assert (await api.call("POST", "/finance/revenues", "CEO", json=REV)).status_code == 403
    assert (await api.call("GET", "/finance/revenues", "VP_SALES")).status_code == 403
    assert (await api.call("GET", "/finance/revenues", "CEO")).status_code == 200


async def test_revenue_idempotent_create(api: ApiClient) -> None:
    h = api.headers("CFO", idem=True)
    r1 = await api.http.post("/api/v1/finance/revenues", json=REV, headers=h)
    r2 = await api.http.post("/api/v1/finance/revenues", json=REV, headers=h)
    assert r1.json()["data"]["id"] == r2.json()["data"]["id"]
    no_key = {"Authorization": h["Authorization"]}
    r3 = await api.http.post("/api/v1/finance/revenues", json=REV, headers=no_key)
    assert r3.status_code == 400


# ---------- expenses ----------
def _exp(dept: uuid.UUID | None, **kw: Any) -> dict[str, Any]:
    return {
        "title": "Thuê văn phòng", "amount": 200_000_000, "category": "office",
        "department_id": str(dept) if dept else None, "spent_on": "2026-09-10", **kw,
    }  # fmt: skip


async def test_expense_crud_and_vendor_mapping(api: ApiClient, db_session: AsyncSession) -> None:
    r = await api.call("POST", "/finance/expenses", json=_exp(None, vendor="Cty Nam Long"))
    assert r.status_code == 201, r.text
    e = r.json()["data"]
    assert e["vendor"] == "Cty Nam Long" and e["period"] == "2026-09"
    p = await api.call(
        "PATCH", f"/finance/expenses/{e['id']}",
        json={"vendor": "Cty B", "spent_on": "2026-10-02"}, headers={"If-Match": "1"},
    )  # fmt: skip
    assert p.status_code == 200 and p.json()["data"]["vendor"] == "Cty B"
    assert p.json()["data"]["period"] == "2026-10"
    assert (await api.call("GET", f"/finance/expenses/{e['id']}")).status_code == 200
    no_version = await api.call("PATCH", f"/finance/expenses/{e['id']}", json={"amount": 5})
    assert no_version.status_code == 422
    assert (await api.call("DELETE", f"/finance/expenses/{e['id']}")).status_code == 204
    assert len(await _audit_actions(db_session, e["id"])) == 3


async def test_expense_recurring_needs_period(api: ApiClient) -> None:
    r = await api.call("POST", "/finance/expenses", json=_exp(None, is_recurring=True))
    assert r.status_code == 422 and r.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    ok = await api.call(
        "POST", "/finance/expenses", json=_exp(None, is_recurring=True, recurrence_period="monthly")
    )
    assert ok.status_code == 201
    neg = await api.call("POST", "/finance/expenses", json=_exp(None, amount=0))
    assert neg.status_code == 422


async def test_manager_scoped_to_own_department(api: ApiClient) -> None:
    mine, other = uuid.uuid4(), uuid.uuid4()
    r = await api.call("POST", "/finance/expenses", "MANAGER", json=_exp(mine), department_id=mine)
    assert r.status_code == 201
    eid = r.json()["data"]["id"]
    deny = await api.call(
        "POST", "/finance/expenses", "MANAGER", json=_exp(other), department_id=mine
    )
    assert deny.status_code == 403 and deny.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    other_id = (await api.call("POST", "/finance/expenses", json=_exp(other))).json()["data"]["id"]

    lst = await api.call("GET", "/finance/expenses", "MANAGER", department_id=mine)
    ids = {x["id"] for x in lst.json()["data"]}
    assert eid in ids and other_id not in ids
    peek = await api.call(
        "GET", "/finance/expenses", "MANAGER", department_id=mine,
        params={"department_id": str(other)},
    )  # fmt: skip
    assert peek.status_code == 403
    get_other = await api.call(
        "GET", f"/finance/expenses/{other_id}", "MANAGER", department_id=mine
    )
    assert get_other.status_code == 403
    move = await api.call(
        "PATCH", f"/finance/expenses/{eid}", "MANAGER", department_id=mine,
        json={"department_id": str(other), "version": 1},
    )  # fmt: skip
    assert move.status_code == 403
    by_dept = await api.call(
        "GET", "/finance/expenses", params={"department_id": str(other), "category": "office",
                                            "period": "2026-09"},
    )  # fmt: skip
    assert [x["id"] for x in by_dept.json()["data"]] == [other_id]


# ---------- cash positions ----------
async def test_cash_position_lifecycle(api: ApiClient, db_session: AsyncSession) -> None:
    # isolate from seeded / earlier positions (rolled back with the test transaction)
    await db_session.execute(
        update(CashPosition).where(CashPosition.deleted_at.is_(None)).values(deleted_at=func.now())
    )
    base = {"cash_source": "bank_statement"}
    a = await api.call(
        "POST", "/finance/cash-positions", json={**base, "period": "2031-08", "closing_balance": 10}
    )
    assert a.status_code == 201, a.text
    assert a.json()["data"]["opening_balance"] is None
    b = await api.call(
        "POST", "/finance/cash-positions", json={**base, "period": "2031-09", "closing_balance": 7}
    )
    bd = b.json()["data"]
    assert bd["opening_balance"] == 10
    dup = await api.call(
        "POST", "/finance/cash-positions", json={**base, "period": "2031-09", "closing_balance": 1}
    )
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    neg = await api.call(
        "POST", "/finance/cash-positions", json={"period": "2031-10", "closing_balance": -1}
    )
    assert neg.status_code == 422
    badp = await api.call(
        "POST", "/finance/cash-positions", json={"period": "31-10", "closing_balance": 1}
    )
    assert badp.status_code == 422

    p = await api.call(
        "PATCH", f"/finance/cash-positions/{bd['id']}", json={"closing_balance": 8, "version": 1}
    )
    assert p.status_code == 200 and p.json()["data"]["closing_balance"] == 8
    g = await api.call("GET", f"/finance/cash-positions/{bd['id']}")
    assert g.json()["data"]["version"] == 2
    lst = await api.call(
        "GET", "/finance/cash-positions",
        params={"from": "2031-08", "to": "2031-09", "sort_by": "period", "order": "asc"},
    )  # fmt: skip
    assert [x["period"] for x in lst.json()["data"]] == ["2031-08", "2031-09"]
    assert (await api.call("GET", f"/finance/cash-positions/{uuid.uuid4()}")).status_code == 404
    assert await _audit_actions(db_session, bd["id"]) == [
        "finance.cash_position_create", "finance.cash_position_update",
    ]  # fmt: skip

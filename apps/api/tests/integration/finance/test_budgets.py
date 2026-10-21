"""T-102 — EP-63 budgets, EP-64 status, BR-FIN-05 `EVT-finance.budget_exceeded` (TC-FIN-002)."""

import uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.envelope import OUTBOX
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration


def _budget(dept: uuid.UUID, **kw: Any) -> dict[str, Any]:
    return {
        "department_id": str(dept), "fiscal_year": 2031, "quarter": "Q3",
        "allocated_amount": 1_000_000_000, "category": "marketing", **kw,
    }  # fmt: skip


def _expense(dept: uuid.UUID, amount: int, day: str = "2031-08-15") -> dict[str, Any]:
    return {
        "title": "Quảng cáo", "amount": amount, "category": "marketing",
        "department_id": str(dept), "spent_on": day,
    }  # fmt: skip


async def _events(db: AsyncSession, budget_id: str) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(OUTBOX.c.payload).where(
            OUTBOX.c.event_type == "finance.budget_exceeded",
            OUTBOX.c.aggregate_id == uuid.UUID(budget_id),
        )
    )
    return [r[0] for r in rows]


async def test_budget_crud_and_duplicate(api: ApiClient) -> None:
    dept = uuid.uuid4()
    r = await api.call("POST", "/finance/budgets", json=_budget(dept))
    assert r.status_code == 201, r.text
    b = r.json()["data"]
    assert b["period"] == "2031-Q3" and b["category"] == "marketing"
    assert b["categories"] == [{"category": "marketing", "allocated_amount": 1_000_000_000}]

    dup = await api.call("POST", "/finance/budgets", json=_budget(dept, allocated_amount=5))
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"

    year = await api.call("POST", "/finance/budgets", json=_budget(dept, quarter=None))
    assert year.status_code == 201 and year.json()["data"]["period"] == "2031"

    p = await api.call(
        "PATCH", f"/finance/budgets/{b['id']}",
        json={"allocated_amount": 2_000_000_000, "notes": "tăng", "version": 1,
              "categories": [{"category": "marketing", "allocated_amount": 2_000_000_000}]},
    )  # fmt: skip
    assert p.status_code == 200, p.text
    assert p.json()["data"]["allocated_amount"] == 2_000_000_000
    assert (await api.call("GET", f"/finance/budgets/{b['id']}")).json()["data"]["version"] == 2

    lst = await api.call(
        "GET", "/finance/budgets",
        params={"department_id": str(dept), "fiscal_year": 2031, "quarter": "Q3"},
    )  # fmt: skip
    assert [x["id"] for x in lst.json()["data"]] == [b["id"]]
    assert (await api.call("DELETE", f"/finance/budgets/{b['id']}")).status_code == 204
    assert (await api.call("GET", f"/finance/budgets/{b['id']}")).status_code == 404
    bad = await api.call("POST", "/finance/budgets", json=_budget(dept, allocated_amount=0))
    assert bad.status_code == 422


async def test_budget_exceeded_published_once(api: ApiClient, db_session: AsyncSession) -> None:
    dept = uuid.uuid4()
    b = (await api.call("POST", "/finance/budgets", json=_budget(dept))).json()["data"]
    await api.call("POST", "/finance/expenses", json=_expense(dept, 900_000_000))
    assert await _events(db_session, b["id"]) == []

    st = await api.call("GET", "/finance/budgets/status", params={"department_id": str(dept)})
    row = st.json()["data"][0]
    assert row["budget_utilization_pct"] == 90.0 and row["status"] == "ok"

    await api.call("POST", "/finance/expenses", json=_expense(dept, 200_000_000, "2031-09-01"))
    events = await _events(db_session, b["id"])
    assert len(events) == 1
    ev = events[0]
    assert ev["budget_utilization_pct"] == 110.0 and ev["period"] == "2031-Q3"
    assert ev["department_id"] == str(dept)

    # Further spend in the same period: no second event (1 lần/phòng ban/kỳ).
    await api.call("POST", "/finance/expenses", json=_expense(dept, 50_000_000, "2031-07-02"))
    assert len(await _events(db_session, b["id"])) == 1

    st2 = await api.call(
        "GET", "/finance/budgets/status", "CEO",
        params={"period": "2031-Q3", "department_id": str(dept)},
    )  # fmt: skip
    row2 = st2.json()["data"][0]
    assert row2["spent_amount"] == 1_150_000_000 and row2["status"] == "critical"
    # Expense in another quarter does not count.
    await api.call("POST", "/finance/expenses", json=_expense(dept, 10, "2031-10-01"))
    st3 = await api.call(
        "GET", "/finance/budgets/status", params={"period": "2031-08", "department_id": str(dept)}
    )
    assert st3.json()["data"][0]["spent_amount"] == 1_150_000_000


async def test_budget_cut_below_spend_triggers_event(
    api: ApiClient, db_session: AsyncSession
) -> None:
    dept = uuid.uuid4()
    b = (await api.call("POST", "/finance/budgets", json=_budget(dept))).json()["data"]
    await api.call("POST", "/finance/expenses", json=_expense(dept, 800_000_000))
    p = await api.call(
        "PATCH", f"/finance/budgets/{b['id']}", json={"allocated_amount": 700_000_000},
        headers={"If-Match": "1"},
    )  # fmt: skip
    assert p.status_code == 200
    assert len(await _events(db_session, b["id"])) == 1


async def test_budget_status_period_param_and_permissions(api: ApiClient) -> None:
    dept = uuid.uuid4()
    await api.call("POST", "/finance/budgets", json=_budget(dept, quarter=None))
    year = await api.call(
        "GET", "/finance/budgets/status", "HR_MANAGER",
        params={"period": "2031", "department_id": str(dept)},
    )  # fmt: skip
    assert year.status_code == 200 and year.json()["data"][0]["period"] == "2031"
    bad = await api.call("GET", "/finance/budgets/status", params={"period": "Q3-2031"})
    assert bad.status_code == 400
    assert (await api.call("GET", "/finance/budgets", "HR_MANAGER")).status_code == 403
    assert (
        await api.call("POST", "/finance/budgets", "CEO", json=_budget(dept))
    ).status_code == 403

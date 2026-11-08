"""D-07 — scope marks of `finance:*` / `sales:*` (02 §5.3) with real tokens per role.

REV `◑r`: nothing outside a review session. MGR `◑d`: own department for read and write, company
records (no department) out of reach. Unscoped roles keep the whole company.
"""

import uuid
from datetime import date
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance.models import Budget, Expense
from tests.conftest import ApiClient
from tests.integration.sales.helpers import make_client, make_deal

pytestmark = pytest.mark.integration

MINE, OTHER = uuid.uuid4(), uuid.uuid4()
COMPANY_READS = ("/finance/revenues", "/finance/invoices", "/finance/cash-positions",
                 "/finance/forecasts", "/finance/cash-flow-forecast")  # fmt: skip
FINANCE_READS = (*COMPANY_READS, "/finance/expenses", "/finance/budgets")
SALES_READS = ("/sales/clients", "/sales/deals", "/sales/targets", "/sales/contracts")


def _denied(r: Any) -> bool:
    return r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_SCOPE"


async def _budget(db: AsyncSession, dept: uuid.UUID, quarter: str = "Q1") -> Budget:
    b = Budget(department_id=dept, fiscal_year=2043, quarter=quarter, allocated_amount=100,
               currency="VND", categories=[], source="MANUAL")  # fmt: skip
    db.add(b)
    await db.flush()
    return b


async def _expense(db: AsyncSession, dept: uuid.UUID | None) -> Expense:
    e = Expense(title="chi", amount=5, currency="VND", category="office", department_id=dept,
                expense_date=date(2043, 1, 10), period_key="2043-01", is_recurring=False,
                source="MANUAL", origin="manual")  # fmt: skip
    db.add(e)
    await db.flush()
    return e


# ---------- REV ◑r ----------
@pytest.mark.parametrize("url", [*FINANCE_READS, *SALES_READS])
async def test_reviewer_has_no_general_read(api: ApiClient, url: str) -> None:
    assert _denied(await api.call("GET", url, "REVIEWER"))


async def test_reviewer_cannot_read_by_id(api: ApiClient, db_session: AsyncSession) -> None:
    client = await make_client(api)
    deal = await make_deal(api, client["id"])
    expense = await _expense(db_session, MINE)
    budget = await _budget(db_session, MINE)
    for url in (f"/sales/deals/{deal['id']}", f"/sales/clients/{client['id']}",
                f"/sales/deals/{deal['id']}/stage-history", f"/finance/expenses/{expense.id}",
                f"/finance/budgets/{budget.id}"):  # fmt: skip
        assert _denied(await api.call("GET", url, "REVIEWER")), url


async def test_reviewer_has_no_funnel_or_aggregate(api: ApiClient) -> None:
    assert _denied(await api.call("GET", "/sales/funnel", "REVIEWER"))
    assert (await api.call("GET", "/sales/pipeline", "REVIEWER")).status_code == 403
    assert (await api.call("GET", "/finance/dashboard", "REVIEWER")).status_code == 403


# ---------- MGR ◑d: company records ----------
@pytest.mark.parametrize("url", COMPANY_READS)
async def test_manager_has_no_company_records(api: ApiClient, url: str) -> None:
    assert _denied(await api.call("GET", url, "MANAGER", department_id=MINE))


@pytest.mark.parametrize(
    ("url", "body"),
    [
        ("/finance/revenues", {"amount": 5, "category": "service", "recognized_on": "2043-01-05"}),
        ("/finance/cash-positions", {"period": "2043-01", "closing_balance": 5,
                                     "cash_source": "bank_statement"}),
        ("/finance/cash-flow-forecast/recompute", {}),
    ],
)  # fmt: skip
async def test_manager_cannot_write_company_records(
    api: ApiClient, url: str, body: dict[str, Any]
) -> None:
    assert _denied(await api.call("POST", url, "MANAGER", department_id=MINE, json=body))


async def test_manager_cannot_pay_or_read_an_invoice(api: ApiClient) -> None:
    client = await make_client(api)
    inv = await api.call("POST", "/finance/invoices", "CFO", json={
        "direction": "OUT", "client_id": client["id"], "client_name": client["name"],
        "number": uuid.uuid4().hex[:8], "issued_on": "2043-01-05", "due_date": "2043-02-05",
        "status": "sent", "lines": [{"description": "x", "quantity": 1, "unit_price": 100,
                                     "vat_pct": 10}],
    })  # fmt: skip
    assert inv.status_code == 201, inv.text
    url = f"/finance/invoices/{inv.json()['data']['id']}"
    assert _denied(await api.call("GET", url, "MANAGER", department_id=MINE))
    pay = {"amount_paid": 10, "paid_at": "2043-01-20T00:00:00Z", "method": "bank_transfer"}
    assert _denied(await api.call("POST", f"{url}/pay", "MANAGER", department_id=MINE, json=pay))


# ---------- MGR ◑d: budgets ----------
async def test_manager_budget_list_is_pinned(api: ApiClient, db_session: AsyncSession) -> None:
    mine, other = await _budget(db_session, MINE), await _budget(db_session, OTHER)
    r = await api.call("GET", "/finance/budgets", "MANAGER", department_id=MINE)
    ids = [b["id"] for b in r.json()["data"]]
    assert str(mine.id) in ids and str(other.id) not in ids
    asked = {"department_id": str(OTHER)}
    assert _denied(await api.call("GET", "/finance/budgets", "MANAGER", department_id=MINE,
                                  params=asked))  # fmt: skip
    s = await api.call("GET", "/finance/budgets/status", "MANAGER", department_id=MINE)
    assert [x["department_id"] for x in s.json()["data"]] == [str(MINE)]
    assert _denied(await api.call("GET", "/finance/budgets/status", "MANAGER", department_id=MINE,
                                  params=asked))  # fmt: skip


async def test_manager_budget_object_level(api: ApiClient, db_session: AsyncSession) -> None:
    mine, other = await _budget(db_session, MINE), await _budget(db_session, OTHER)
    ok = await api.call("GET", f"/finance/budgets/{mine.id}", "MANAGER", department_id=MINE)
    assert ok.status_code == 200
    url = f"/finance/budgets/{other.id}"
    assert _denied(await api.call("GET", url, "MANAGER", department_id=MINE))
    patch = {"allocated_amount": 7, "version": 1}
    assert _denied(await api.call("PATCH", url, "MANAGER", department_id=MINE, json=patch))
    assert _denied(await api.call("DELETE", url, "MANAGER", department_id=MINE))
    up = await api.call("PATCH", f"/finance/budgets/{mine.id}", "MANAGER", department_id=MINE,
                        json=patch)  # fmt: skip
    assert up.status_code == 200 and up.json()["data"]["allocated_amount"] == 7


async def test_manager_creates_budgets_for_their_department_only(api: ApiClient) -> None:
    body = {"fiscal_year": 2043, "quarter": "Q2", "allocated_amount": 100}
    theirs = {**body, "department_id": str(OTHER)}
    assert _denied(await api.call("POST", "/finance/budgets", "MANAGER", department_id=MINE,
                                  json=theirs))  # fmt: skip
    own = {**body, "department_id": str(MINE)}
    r = await api.call("POST", "/finance/budgets", "MANAGER", department_id=MINE, json=own)
    assert r.status_code == 201, r.text


# ---------- MGR ◑d: expenses ----------
async def test_manager_expenses_object_level(api: ApiClient, db_session: AsyncSession) -> None:
    mine, other = await _expense(db_session, MINE), await _expense(db_session, OTHER)
    unassigned = await _expense(db_session, None)
    r = await api.call("GET", "/finance/expenses", "MANAGER", department_id=MINE)
    ids = {e["id"] for e in r.json()["data"]}
    assert str(mine.id) in ids and not {str(other.id), str(unassigned.id)} & ids
    for e in (other, unassigned):
        url = f"/finance/expenses/{e.id}"
        assert _denied(await api.call("GET", url, "MANAGER", department_id=MINE))
        assert _denied(await api.call("DELETE", url, "MANAGER", department_id=MINE))


async def test_manager_expense_cannot_use_another_budget(
    api: ApiClient, db_session: AsyncSession
) -> None:
    other = await _budget(db_session, OTHER)
    body = {"title": "chi", "amount": 5, "category": "office", "spent_on": "2043-01-10",
            "department_id": str(MINE), "budget_id": str(other.id)}  # fmt: skip
    assert _denied(await api.call("POST", "/finance/expenses", "MANAGER", department_id=MINE,
                                  json=body))  # fmt: skip
    mine = await _expense(db_session, MINE)
    patch = {"budget_id": str(other.id), "version": 1}
    assert _denied(await api.call("PATCH", f"/finance/expenses/{mine.id}", "MANAGER",
                                  department_id=MINE, json=patch))  # fmt: skip


async def test_manager_without_department_sees_nothing(api: ApiClient) -> None:
    for url in ("/finance/budgets", "/finance/expenses"):
        assert _denied(await api.call("GET", url, "MANAGER"))


# ---------- MGR ◑d: sales ----------
async def test_manager_sales_cross_department(api: ApiClient) -> None:
    client = await make_client(api)
    theirs = await make_deal(api, client["id"], "MANAGER", department_id=OTHER)
    mine = await make_deal(api, client["id"], "MANAGER", department_id=MINE)
    r = await api.call("GET", "/sales/deals", "MANAGER", department_id=MINE, params={"limit": 100})
    ids = {d["id"] for d in r.json()["data"]}
    assert mine["id"] in ids and theirs["id"] not in ids
    url = f"/sales/deals/{theirs['id']}"
    assert _denied(await api.call("GET", url, "MANAGER", department_id=MINE))


# ---------- nothing widened, nothing narrowed for unscoped roles ----------
@pytest.mark.parametrize("url", FINANCE_READS)
async def test_finance_director_and_ceo_keep_the_company_view(api: ApiClient, url: str) -> None:
    assert (await api.call("GET", url, "CFO")).status_code == 200
    assert (await api.call("GET", url, "CEO")).status_code == 200


@pytest.mark.parametrize("url", [*FINANCE_READS, *SALES_READS])
async def test_employee_stays_denied(api: ApiClient, url: str) -> None:
    assert (await api.call("GET", url, "EMPLOYEE")).status_code == 403

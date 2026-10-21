"""T-104 — EP-67 invoices (+ lines), EP-68 pay → events (TC-FIN-004)."""

import uuid
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.envelope import OUTBOX
from app.modules.finance.services.invoice_service import InvoiceService, today
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration


def _inv(**kw: Any) -> dict[str, Any]:
    return {
        "client_id": str(uuid.uuid4()), "client_name": "Cty XYZ",
        "number": f"T{uuid.uuid4().hex[:8]}", "issued_on": "2031-09-01",
        "due_date": "2031-10-01",
        "lines": [
            {"description": "Máy in", "quantity": 2, "unit_price": 10_000_000},
            {"description": "Bảo trì", "quantity": 1.5, "unit_price": 1_000_000},
        ],
        **kw,
    }  # fmt: skip


async def _events(db: AsyncSession, evt: str, agg: str) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(OUTBOX.c.payload).where(
            OUTBOX.c.event_type == evt, OUTBOX.c.aggregate_id == uuid.UUID(agg)
        )
    )
    return [r[0] for r in rows]


async def test_create_invoice_totals_and_event(api: ApiClient, db_session: AsyncSession) -> None:
    r = await api.call("POST", "/finance/invoices", json=_inv())
    assert r.status_code == 201, r.text
    inv = r.json()["data"]
    assert [ln["amount"] for ln in inv["lines"]] == [20_000_000, 1_500_000]
    assert inv["subtotal"] == 21_500_000 and inv["vat_pct"] == 10
    assert inv["vat_amount"] == 2_150_000 and inv["total_amount"] == 23_650_000
    assert inv["amount_due"] == 23_650_000 and inv["status"] == "sent"
    ev = await _events(db_session, "finance.invoice_created", inv["id"])
    assert len(ev) == 1 and ev[0]["total_amount"] == 23_650_000
    assert "client_name" not in ev[0]


async def test_pay_partial_then_full(api: ApiClient, db_session: AsyncSession) -> None:
    inv = (await api.call("POST", "/finance/invoices", json=_inv())).json()["data"]
    url = f"/finance/invoices/{inv['id']}/pay"
    p1 = await api.call(
        "POST", url, json={"amount_paid": 10_000_000, "paid_at": "2031-09-15T03:00:00Z"}
    )
    assert p1.status_code == 200, p1.text
    assert (
        p1.json()["data"]["status"] == "partial" and p1.json()["data"]["amount_due"] == 13_650_000
    )
    assert await _events(db_session, "finance.invoice_paid", inv["id"]) == []
    over = await api.call(
        "POST", url, json={"amount_paid": 99_000_000, "paid_at": "2031-09-20T00:00:00Z"}
    )
    assert over.status_code == 422
    full = {"amount_paid": 13_650_000, "paid_at": "2031-09-20T00:00:00Z", "method": "bank_transfer"}
    p2 = await api.call("POST", url, json=full)
    d = p2.json()["data"]
    assert d["status"] == "paid" and d["amount_due"] == 0 and d["paid_at"].startswith("2031-09-20")
    ev = await _events(db_session, "finance.invoice_paid", inv["id"])
    assert len(ev) == 1 and ev[0]["days_to_pay"] == 19
    again = await api.call("POST", url, json={"amount_paid": 1, "paid_at": "2031-09-21T00:00:00Z"})
    assert again.status_code == 409 and again.json()["error"]["code"] == "CONFLICT_STATE"
    cannot_edit = await api.call(
        "PATCH", f"/finance/invoices/{inv['id']}", json={"version": d["version"], "notes": "x"}
    )
    assert cannot_edit.status_code == 409
    cannot_delete = await api.call("DELETE", f"/finance/invoices/{inv['id']}")
    assert cannot_delete.status_code == 409


@pytest.mark.parametrize(
    ("patch", "status", "code"),
    [
        ({"lines": []}, 422, "VALIDATION_ERROR"),
        ({"due_date": "2031-09-01"}, 422, "BUSINESS_RULE_VIOLATION"),
        ({"client_id": None}, 422, "BUSINESS_RULE_VIOLATION"),
        ({"lines": [{"description": "a", "quantity": 1, "unit_price": 1, "vat_pct": 8},
                    {"description": "b", "quantity": 1, "unit_price": 1, "vat_pct": 10}]},
         422, "BUSINESS_RULE_VIOLATION"),
        ({"lines": [{"description": "a", "quantity": 1, "unit_price": 1, "vat_pct": 7}]},
         422, "VALIDATION_ERROR"),
    ],
)  # fmt: skip
async def test_invoice_validation(
    api: ApiClient, patch: dict[str, Any], status: int, code: str
) -> None:
    r = await api.call("POST", "/finance/invoices", json=_inv(**patch))
    assert r.status_code == status and r.json()["error"]["code"] == code


async def test_duplicate_number_and_in_invoice(api: ApiClient) -> None:
    body = _inv()
    assert (await api.call("POST", "/finance/invoices", json=body)).status_code == 201
    dup = await api.call("POST", "/finance/invoices", json={**body, "client_id": str(uuid.uuid4())})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    incoming = _inv(direction="IN", client_id=None, counterparty_name="NCC A",
                    counterparty_tax_code="0301234567", number=body["number"])  # fmt: skip
    assert (await api.call("POST", "/finance/invoices", json=incoming)).status_code == 201


async def test_draft_edit_lines_cancel_delete(api: ApiClient) -> None:
    inv = (await api.call("POST", "/finance/invoices", json=_inv(status="draft"))).json()["data"]
    url = f"/finance/invoices/{inv['id']}"
    p = await api.call(
        "PATCH", url, json={"version": 1, "lines": [{"description": "x", "quantity": 1,
                                                       "unit_price": 100, "vat_pct": 5}]},
    )  # fmt: skip
    assert p.status_code == 200, p.text
    assert p.json()["data"]["total_amount"] == 105 and len(p.json()["data"]["lines"]) == 1
    nopay = await api.call(
        "POST", f"{url}/pay", json={"amount_paid": 1, "paid_at": "2031-09-02T00:00:00Z"}
    )
    assert nopay.status_code == 409
    sent = await api.call(
        "PATCH", url, json={"version": 2, "status": "sent", "due_date": "2031-11-01"}
    )
    assert sent.json()["data"]["status"] == "sent"
    back = await api.call("PATCH", url, json={"version": 3, "status": "draft"})
    assert back.status_code == 409
    lines_sent = await api.call("PATCH", url, json={"version": 3, "lines": _inv()["lines"]})
    assert lines_sent.status_code == 409
    bad_due = await api.call("PATCH", url, json={"version": 3, "due_date": "2031-08-01"})
    assert bad_due.status_code == 422
    assert (await api.call("DELETE", url)).status_code == 204
    assert (await api.call("GET", url)).status_code == 404


async def test_cancel_with_payment_is_conflict(api: ApiClient) -> None:
    inv = (await api.call("POST", "/finance/invoices", json=_inv())).json()["data"]
    await api.call("POST", f"/finance/invoices/{inv['id']}/pay",
                   json={"amount_paid": 5, "paid_at": "2031-09-05T00:00:00Z"})  # fmt: skip
    r = await api.call(
        "PATCH", f"/finance/invoices/{inv['id']}", json={"version": 2, "status": "cancelled"}
    )
    assert r.status_code == 409


async def test_overdue_filter_and_daily_job(api: ApiClient, db_session: AsyncSession) -> None:
    client = str(uuid.uuid4())
    past = (today() - timedelta(days=40)).isoformat()
    due = (today() - timedelta(days=10)).isoformat()
    late_body = _inv(client_id=client, issued_on=past, due_date=due)
    late = (await api.call("POST", "/finance/invoices", json=late_body)).json()["data"]
    fresh = (await api.call("POST", "/finance/invoices", json=_inv(client_id=client))).json()[
        "data"
    ]
    assert late["overdue"] and late["days_overdue"] == 10 and not fresh["overdue"]

    ov = await api.call("GET", "/finance/invoices", params={"client_id": client, "overdue": True})
    assert [x["id"] for x in ov.json()["data"]] == [late["id"]]
    not_ov = await api.call(
        "GET", "/finance/invoices", params={"client_id": client, "overdue": False}
    )
    assert [x["id"] for x in not_ov.json()["data"]] == [fresh["id"]]
    by_period = await api.call(
        "GET", "/finance/invoices",
        params={"client_id": client, "period": "2031-09", "direction": "OUT", "status": "sent"},
    )  # fmt: skip
    assert [x["id"] for x in by_period.json()["data"]] == [fresh["id"]]

    svc = InvoiceService(db_session)
    assert await svc.mark_overdue() >= 1
    assert await svc.mark_overdue() == 0
    got = (await api.call("GET", f"/finance/invoices/{late['id']}")).json()["data"]
    assert got["status"] == "overdue" and got["version"] == 2
    total, overdue_ar = await svc.repo.receivables(today())
    assert total >= overdue_ar >= late["total_amount"]


async def test_invoice_permissions_and_404(api: ApiClient) -> None:
    assert (await api.call("GET", f"/finance/invoices/{uuid.uuid4()}")).status_code == 404
    assert (await api.call("POST", "/finance/invoices", "CEO", json=_inv())).status_code == 403
    assert (await api.call("GET", "/finance/invoices", "VP_SALES")).status_code == 403

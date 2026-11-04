"""TC-M8-01 — R-DEC-172: the CFO issues an OUT invoice from the customer's tax code (MST).

The CFO (DIR khối F) cannot read the sales client list (khối C) and must not be given it; an OUT
invoice still needs its client. The backend resolves the unique client holding that MST through
the sales module's public service and links it — only id + name cross the module boundary.
"""

import uuid
from typing import Any

import pytest

from tests.conftest import ApiClient

pytestmark = pytest.mark.integration


def _mst() -> str:
    return "03" + str(uuid.uuid4().int)[:8]


def _out(**kw: Any) -> dict[str, Any]:
    return {
        "direction": "OUT", "number": f"M8{uuid.uuid4().hex[:8]}", "issued_on": "2031-09-01",
        "due_date": "2031-10-01",
        "lines": [{"description": "Máy in", "quantity": 1, "unit_price": 5_000_000}],
        **kw,
    }  # fmt: skip


async def test_cfo_links_out_invoice_by_tax_code_without_reading_clients(api: ApiClient) -> None:
    mst = _mst()
    c = await api.call(
        "POST", "/sales/clients", "VP_SALES", json={"name": f"Khách M8 {mst}", "tax_code": mst}
    )
    assert c.status_code == 201, c.text
    client = c.json()["data"]

    assert (
        await api.call("GET", "/sales/clients", "CFO")
    ).status_code == 403  # no list for the CFO
    r = await api.call("POST", "/finance/invoices", "CFO", json=_out(counterparty_tax_code=mst))
    assert r.status_code == 201, r.text
    inv = r.json()["data"]
    assert inv["client_id"] == client["id"]
    assert inv["client_name"] == client["name"]  # snapshot from the linked client


@pytest.mark.parametrize(
    ("extra", "field"),
    [({"counterparty_tax_code": "0399999999999"}, "counterparty_tax_code"), ({}, "client_id")],
)
async def test_out_invoice_without_resolvable_client_is_refused(
    api: ApiClient, extra: dict[str, Any], field: str
) -> None:
    r = await api.call("POST", "/finance/invoices", "CFO", json=_out(**extra))
    assert r.status_code == 422, r.text
    err = r.json()["error"]
    assert (err["code"], err["details"]["field"]) == ("BUSINESS_RULE_VIOLATION", field)


async def test_explicit_client_id_still_wins(api: ApiClient) -> None:
    cid = str(uuid.uuid4())
    r = await api.call(
        "POST", "/finance/invoices", "CFO", json=_out(client_id=cid, counterparty_tax_code=_mst())
    )
    assert r.status_code == 201 and r.json()["data"]["client_id"] == cid

"""T-113 — EP-78 contracts L C R U D (TC-SAL-003)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import ApiClient
from tests.integration.sales.helpers import audit_actions, make_client, make_deal

pytestmark = pytest.mark.integration

TODAY = datetime.now(UTC).date()


def body(client_id: str, **kw: Any) -> dict[str, Any]:
    return {
        "contract_number": f"HD-{uuid.uuid4().hex[:12]}", "client_id": client_id,
        "contract_value": 1_200_000_000, "signed_at": "2026-09-01",
        "effective_date": "2026-09-05", "expiry_date": "2027-09-04", "status": "active",
        "is_recurring": True, "renewal_notice_days": 30,
        "payment_terms": [{"due_date": "2026-10-05", "amount": 600_000_000,
                           "description": "Đợt 1"}],
        **kw,
    }  # fmt: skip


async def test_contract_crud(api: ApiClient, db_session: AsyncSession) -> None:
    c = await make_client(api)
    d = await make_deal(api, c["id"])
    r = await api.call("POST", "/sales/contracts", "VP_SALES", json=body(c["id"], deal_id=d["id"]))
    assert r.status_code == 201, r.text
    k = r.json()["data"]
    assert k["payment_terms"][0]["due_date"] == "2026-10-05" and k["deal_id"] == d["id"]
    kid = k["id"]
    dup = await api.call(
        "POST", "/sales/contracts", "VP_SALES",
        json=body(c["id"], contract_number=k["contract_number"]),
    )  # fmt: skip
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    p = await api.call(
        "PATCH", f"/sales/contracts/{kid}", "VP_SALES",
        json={"status": "terminated", "payment_terms": [], "contract_number": "HD-NEW-"
              + uuid.uuid4().hex[:6], "client_id": c["id"], "deal_id": None, "version": 1},
    )  # fmt: skip
    assert p.status_code == 200, p.text
    assert p.json()["data"]["status"] == "terminated" and p.json()["data"]["payment_terms"] == []
    stale = await api.call("PATCH", f"/sales/contracts/{kid}", "VP_SALES", json={"version": 1})
    assert stale.status_code == 409
    bad_exp = await api.call(
        "PATCH", f"/sales/contracts/{kid}", "VP_SALES",
        json={"expiry_date": "2026-01-01", "version": 2},
    )  # fmt: skip
    assert bad_exp.status_code == 422
    assert (await api.call("GET", f"/sales/contracts/{kid}", "CEO")).status_code == 200
    assert (await api.call("DELETE", f"/sales/contracts/{kid}", "CEO")).status_code == 403
    assert (await api.call("DELETE", f"/sales/contracts/{kid}", "VP_SALES")).status_code == 204
    assert (await api.call("GET", f"/sales/contracts/{kid}", "VP_SALES")).status_code == 404
    assert await audit_actions(db_session, kid) == [
        "sales.contract_create", "sales.contract_delete", "sales.contract_update",
    ]  # fmt: skip


@pytest.mark.parametrize(
    "patch",
    [{"contract_value": 0}, {"expiry_date": "2026-09-01"}, {"client_id": str(uuid.uuid4())},
     {"deal_id": str(uuid.uuid4())}],
)  # fmt: skip
async def test_contract_validation(api: ApiClient, patch: dict[str, Any]) -> None:
    c = await make_client(api)
    r = await api.call("POST", "/sales/contracts", "VP_SALES", json={**body(c["id"]), **patch})
    assert r.status_code == 422 and r.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


async def test_contract_list_filters_expiring(api: ApiClient) -> None:
    c = await make_client(api)
    soon = (TODAY + timedelta(days=20)).isoformat()
    later = (TODAY + timedelta(days=200)).isoformat()
    a = await api.call(
        "POST", "/sales/contracts", "VP_SALES",
        json=body(c["id"], effective_date="2026-01-01", expiry_date=soon),
    )  # fmt: skip
    await api.call(
        "POST", "/sales/contracts", "VP_SALES",
        json=body(c["id"], effective_date="2026-01-01", expiry_date=later, status="draft"),
    )  # fmt: skip
    r = await api.call(
        "GET", "/sales/contracts", "VP_SALES",
        params={"client_id": c["id"], "expiring_within_days": 30, "status": "active",
                "sort_by": "expiry_date"},
    )  # fmt: skip
    assert [x["id"] for x in r.json()["data"]] == [a.json()["data"]["id"]]
    every = await api.call("GET", "/sales/contracts", "VP_SALES", params={"client_id": c["id"]})
    assert every.json()["meta"]["pagination"]["total"] == 2
    assert (await api.call("GET", "/sales/contracts", "CFO")).status_code == 403


async def test_contract_manager_scope(api: ApiClient) -> None:
    mine, other = uuid.uuid4(), uuid.uuid4()
    c = await make_client(api)
    own_deal = await make_deal(api, c["id"], "MANAGER", department_id=mine)
    other_deal = await make_deal(api, c["id"], department_id=str(other))
    ok = await api.call(
        "POST", "/sales/contracts", "MANAGER", department_id=mine,
        json=body(c["id"], deal_id=own_deal["id"]),
    )  # fmt: skip
    assert ok.status_code == 201
    no_deal = await api.call(
        "POST", "/sales/contracts", "MANAGER", department_id=mine, json=body(c["id"])
    )
    assert no_deal.status_code == 403
    foreign = await api.call("POST", "/sales/contracts", "VP_SALES",
                             json=body(c["id"], deal_id=other_deal["id"]))  # fmt: skip
    fid = foreign.json()["data"]["id"]
    get_f = await api.call("GET", f"/sales/contracts/{fid}", "MANAGER", department_id=mine)
    assert get_f.status_code == 403
    lst = await api.call(
        "GET", "/sales/contracts", "MANAGER", department_id=mine, params={"client_id": c["id"]}
    )
    assert [x["id"] for x in lst.json()["data"]] == [ok.json()["data"]["id"]]
    move = await api.call(
        "PATCH", f"/sales/contracts/{ok.json()['data']['id']}", "MANAGER", department_id=mine,
        json={"deal_id": other_deal["id"], "version": 1},
    )  # fmt: skip
    assert move.status_code == 403
    ceo = await api.call("POST", "/sales/contracts", "CEO", json=body(c["id"]))
    assert ceo.status_code == 403

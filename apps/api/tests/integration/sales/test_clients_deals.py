"""T-111 — EP-71 clients, EP-72 deals, EP-73 stage, EP-74 stage-history (TC-SAL-001)."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_LOGS
from app.modules.sales.services.sales_service import normalize_name
from tests.conftest import ApiClient
from tests.integration.sales.helpers import (
    audit_actions,
    deal_body,
    make_client,
    make_deal,
    outbox_for,
    stage,
    uniq,
)

pytestmark = pytest.mark.integration


# ---------- clients ----------
async def test_client_crud_contacts_and_audit_mask(
    api: ApiClient, db_session: AsyncSession
) -> None:
    contact = {"name": "Nguyễn Văn A", "email": "a@abc.test", "phone": "0901234567"}
    c = await make_client(api, industry="retail", size="medium", contacts=[contact])
    assert c["contacts"] == [contact] and c["size"] == "medium" and c["status"] == "prospect"
    cid = c["id"]
    assert (await api.call("GET", f"/sales/clients/{cid}", "CEO")).status_code == 200
    p = await api.call(
        "PATCH", f"/sales/clients/{cid}", "VP_SALES",
        json={"size": "enterprise", "contacts": [], "status": "active", "version": 1},
    )  # fmt: skip
    assert p.status_code == 200, p.text
    d = p.json()["data"]
    assert d["size"] == "enterprise" and d["contacts"] == [] and d["version"] == 2
    stale = await api.call("PATCH", f"/sales/clients/{cid}", "VP_SALES", json={"version": 1})
    assert stale.status_code == 409
    rows = await db_session.execute(
        select(AUDIT_LOGS.c.after).where(
            AUDIT_LOGS.c.target_id == uuid.UUID(cid), AUDIT_LOGS.c.action == "sales.client_create"
        )
    )
    assert "a@abc.test" not in str(rows.scalar_one())
    assert (await api.call("DELETE", f"/sales/clients/{cid}", "VP_SALES")).status_code == 204
    assert (await api.call("GET", f"/sales/clients/{cid}", "VP_SALES")).status_code == 404
    assert await audit_actions(db_session, cid) == [
        "sales.client_create", "sales.client_delete", "sales.client_update",
    ]  # fmt: skip


async def test_client_duplicates_and_similar(api: ApiClient) -> None:
    base = uniq("Công ty Thiết bị")
    tax = str(uuid.uuid4().int)[:10]
    first = await make_client(api, name=base, tax_code=tax)
    dup = await api.call("POST", "/sales/clients", "VP_SALES", json={"name": base.upper()})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    assert dup.json()["error"]["details"]["similar_clients"][0]["id"] == first["id"]
    dup_tax = await api.call(
        "POST", "/sales/clients", "VP_SALES", json={"name": uniq(), "tax_code": tax}
    )
    assert dup_tax.status_code == 409
    near = await make_client(api, name=base + " x")
    assert first["id"] in {s["id"] for s in near["similar_clients"]}
    rename = await api.call(
        "PATCH", f"/sales/clients/{near['id']}", "VP_SALES", json={"name": base, "version": 1}
    )
    assert rename.status_code == 409


async def test_client_list_search_and_scope(api: ApiClient) -> None:
    tag = uuid.uuid4().hex
    a = await make_client(api, name=f"Đại Phát {tag}", industry=tag)
    await make_client(api, name=f"Khác {tag}", industry="other")
    r = await api.call("GET", "/sales/clients", "VP_SALES", params={"q": f"dai phat {tag}"})
    assert [x["id"] for x in r.json()["data"]] == [a["id"]]
    r2 = await api.call(
        "GET", "/sales/clients", "MANAGER", params={"industry": tag, "sort_by": "name"}
    )
    assert r2.json()["meta"]["pagination"]["total"] == 1
    assert (await api.call("GET", "/sales/clients", "CFO")).status_code == 403
    assert normalize_name("  Công-ty  ĐẠI phát ") == "cong ty dai phat"
    ceo = await api.call("POST", "/sales/clients", "CEO", json={"name": uniq()})
    assert ceo.status_code == 403 and ceo.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    mgr_ok = await api.call("POST", "/sales/clients", "MANAGER", json={"name": uniq()})
    assert mgr_ok.status_code == 201
    mgr_edit = await api.call(
        "PATCH", f"/sales/clients/{a['id']}", "MANAGER", json={"notes": "x", "version": 1}
    )
    assert mgr_edit.status_code == 403
    assert (await api.call("DELETE", f"/sales/clients/{a['id']}", "MANAGER")).status_code == 403


async def test_client_with_deal_cannot_be_deleted(api: ApiClient) -> None:
    c = await make_client(api)
    await make_deal(api, c["id"])
    r = await api.call("DELETE", f"/sales/clients/{c['id']}", "VP_SALES")
    assert r.status_code == 409 and r.json()["error"]["code"] == "CONFLICT_STATE"


# ---------- deals ----------
async def test_deal_crud_rules(api: ApiClient, db_session: AsyncSession) -> None:
    c = await make_client(api)
    d = await make_deal(api, c["id"], tags=["hn"])
    assert d["stage"] == "lead" and d["weighted_value"] == 160_000_000  # BR-SAL-02
    did = d["id"]
    p = await api.call(
        "PATCH", f"/sales/deals/{did}", "VP_SALES",
        json={"probability_pct": 50, "deal_value": 1_000_000_000, "owner_id": str(uuid.uuid4()),
              "client_id": c["id"]}, headers={"If-Match": "1"},
    )  # fmt: skip
    assert p.status_code == 200, p.text
    assert p.json()["data"]["weighted_value"] == 500_000_000
    bad_val = await api.call(
        "PATCH", f"/sales/deals/{did}", "VP_SALES", json={"deal_value": 0, "version": 2}
    )
    assert bad_val.status_code == 422
    bad_client = await api.call(
        "PATCH", f"/sales/deals/{did}", "VP_SALES",
        json={"client_id": str(uuid.uuid4()), "version": 2},
    )  # fmt: skip
    assert bad_client.status_code == 422
    for role in ("MANAGER", "CEO"):
        assert (await api.call("DELETE", f"/sales/deals/{did}", role)).status_code == 403
    assert (await api.call("DELETE", f"/sales/deals/{did}", "VP_SALES")).status_code == 204
    assert (await api.call("GET", f"/sales/deals/{did}", "VP_SALES")).status_code == 404
    assert await audit_actions(db_session, did) == [
        "sales.deal_create", "sales.deal_delete", "sales.deal_update",
    ]  # fmt: skip


@pytest.mark.parametrize(
    ("patch", "field"),
    [({"deal_value": 0}, "deal_value"), ({"expected_close_date": "2020-01-01"}, "x"),
     ({"client_id": str(uuid.uuid4())}, "client_id")],
)  # fmt: skip
async def test_deal_create_validation(api: ApiClient, patch: dict[str, str], field: str) -> None:
    c = await make_client(api)
    r = await api.call("POST", "/sales/deals", "VP_SALES", json={**deal_body(c["id"]), **patch})
    assert r.status_code == 422 and r.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


async def test_deal_list_filters(api: ApiClient) -> None:
    c = await make_client(api)
    owner = str(uuid.uuid4())
    d1 = await make_deal(api, c["id"], owner_id=owner, expected_close_date="2099-01-10")
    await make_deal(api, c["id"], owner_id=owner, expected_close_date="2099-03-10")
    await make_deal(api, c["id"])
    r = await api.call(
        "GET", "/sales/deals", "VP_SALES",
        params={"owner_id": owner, "client_id": c["id"], "stage": "lead",
                "expected_close_from": "2099-01-01", "expected_close_to": "2099-01-31",
                "sort_by": "deal_value"},
    )  # fmt: skip
    assert [x["id"] for x in r.json()["data"]] == [d1["id"]]
    assert (await api.call("GET", "/sales/deals", "CFO")).status_code == 403
    bad = await api.call("GET", "/sales/deals", "VP_SALES", params={"sort_by": "name"})
    assert bad.status_code == 400


async def test_manager_department_scope(api: ApiClient) -> None:
    mine, other = uuid.uuid4(), uuid.uuid4()
    c = await make_client(api)
    own = await make_deal(api, c["id"], "MANAGER", department_id=mine)
    assert own["department_id"] == str(mine)
    deny = await api.call(
        "POST", "/sales/deals", "MANAGER", department_id=mine,
        json=deal_body(c["id"], department_id=str(other)),
    )  # fmt: skip
    assert deny.status_code == 403 and deny.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    foreign = await make_deal(api, c["id"], department_id=str(other))
    lst = await api.call("GET", "/sales/deals", "MANAGER", department_id=mine)
    ids = {x["id"] for x in lst.json()["data"]}
    assert own["id"] in ids and foreign["id"] not in ids
    get_f = await api.call("GET", f"/sales/deals/{foreign['id']}", "MANAGER", department_id=mine)
    assert get_f.status_code == 403
    move = await api.call(
        "PATCH", f"/sales/deals/{own['id']}", "MANAGER", department_id=mine,
        json={"department_id": str(other), "version": 1},
    )  # fmt: skip
    assert move.status_code == 403
    ceo = await api.call("POST", "/sales/deals", "CEO", json=deal_body(c["id"]))
    assert ceo.status_code == 403


# ---------- stage transitions + events ----------
async def test_stage_won_records_history_and_event(
    api: ApiClient, db_session: AsyncSession
) -> None:
    c = await make_client(api)
    product = str(uuid.uuid4())
    d = await make_deal(api, c["id"], product_id=product)
    for to in ("qualified", "negotiation"):
        r = await stage(api, d["id"], to)
        assert r.status_code == 200, r.text
    back = await stage(api, d["id"], "proposal")
    assert back.status_code == 409 and back.json()["error"]["details"]["reason"] == "not_forward"
    won = await stage(api, d["id"], "closed_won")
    w = won.json()["data"]
    assert w["stage"] == "closed_won" and w["probability_pct"] == 100 and w["closed_at"]
    assert w["weighted_value"] == w["deal_value"]
    again = await stage(api, d["id"], "closed_lost", lost_reason="x")
    assert again.status_code == 409 and again.json()["error"]["details"]["reason"] == "closed"
    prob = await api.call(
        "PATCH", f"/sales/deals/{d['id']}", "VP_SALES", json={"probability_pct": 5, "version": 4}
    )
    assert prob.status_code == 409

    events = await outbox_for(db_session, d["id"])
    assert [e[0] for e in events] == ["sales.deal_closed_won"]
    payload = events[0][1]
    assert payload["deal_id"] == d["id"] and payload["deal_value"] == 800_000_000
    assert payload["product_id"] == product and "name" not in payload

    hist = await api.call("GET", f"/sales/deals/{d['id']}/stage-history", "VP_SALES")
    rows = hist.json()["data"]
    assert [(r["from_stage"], r["to_stage"]) for r in rows] == [
        ("negotiation", "closed_won"), ("qualified", "negotiation"),
        ("lead", "qualified"), (None, "lead"),
    ]  # fmt: skip
    asc = await api.call(
        "GET", f"/sales/deals/{d['id']}/stage-history", "VP_SALES",
        params={"order": "asc", "limit": 1, "offset": 1},
    )  # fmt: skip
    assert asc.json()["data"][0]["to_stage"] == "qualified"
    assert asc.json()["meta"]["pagination"]["total"] == 4
    assert "sales.deal_stage_change" in await audit_actions(db_session, d["id"])


async def test_stage_lost_requires_reason_and_publishes(
    api: ApiClient, db_session: AsyncSession
) -> None:
    c = await make_client(api)
    d = await make_deal(api, c["id"])
    no_reason = await stage(api, d["id"], "closed_lost")
    assert no_reason.status_code == 422
    lost = await stage(api, d["id"], "closed_lost", lost_reason="Giá cao, gọi 0901234567")
    assert lost.status_code == 200
    data = lost.json()["data"]
    assert data["probability_pct"] == 0 and data["weighted_value"] == 0
    events = await outbox_for(db_session, d["id"])
    assert [e[0] for e in events] == ["sales.deal_closed_lost"]
    assert "0901234567" not in events[0][1]["lost_reason"]
    same = await stage(api, d["id"], "lead")
    assert same.status_code == 409


async def test_stage_permissions_and_idempotency(api: ApiClient) -> None:
    c = await make_client(api)
    d = await make_deal(api, c["id"])
    assert (await stage(api, d["id"], "qualified", "CEO")).status_code == 403
    assert (await stage(api, d["id"], "qualified", "CFO")).status_code == 403
    h = api.headers("VP_SALES", idem=True)
    url = f"/api/v1/sales/deals/{d['id']}/stage"
    r1 = await api.http.post(url, json={"to_stage": "proposal"}, headers=h)
    r2 = await api.http.post(url, json={"to_stage": "proposal"}, headers=h)
    assert r1.status_code == r2.status_code == 200
    assert r2.json()["data"]["version"] == r1.json()["data"]["version"]
    missing = await stage(api, str(uuid.uuid4()), "qualified")
    assert missing.status_code == 404
    hist = await api.call("GET", f"/sales/deals/{uuid.uuid4()}/stage-history", "VP_SALES")
    assert hist.status_code == 404

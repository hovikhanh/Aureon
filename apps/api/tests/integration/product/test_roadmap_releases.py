"""T-201 — EP-93 roadmap items, EP-94 releases + `product.product_launched` (TC-PRD-001)."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.product.models import Product
from tests.conftest import ApiClient
from tests.integration.product.helpers import audit_actions, make, make_product, outbox_for

pytestmark = pytest.mark.integration


async def test_roadmap_crud(api: ApiClient, db_session: AsyncSession) -> None:
    p = await make_product(api)
    body = {"product_id": p["id"], "title": "Thanh toán QR", "quarter": "2037-Q1",
            "target_date": "2037-03-15"}  # fmt: skip
    item = await make(api, "roadmap-items", body)
    assert item["target_date"] == "2037-03-15" and item["completed_at"] is None
    bad_q = await api.call("POST", "/product/roadmap-items", "CPO", json={**body, "quarter": "Q1"})
    assert bad_q.status_code == 422
    no_p = await api.call(
        "POST", "/product/roadmap-items", "CPO", json={**body, "product_id": str(uuid.uuid4())}
    )
    assert no_p.status_code == 422 and no_p.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    done = await make(api, "roadmap-items", {**body, "status": "done"})
    assert done["completed_at"] is not None
    up = await api.call(
        "PATCH", f"/product/roadmap-items/{item['id']}", "CPO",
        json={"status": "done", "target_date": "2037-03-20", "version": 1},
    )  # fmt: skip
    assert up.status_code == 200
    data = up.json()["data"]
    assert data["completed_at"] is not None and data["target_date"] == "2037-03-20"
    back = await api.call(
        "PATCH", f"/product/roadmap-items/{item['id']}", "CPO",
        json={"status": "in_progress", "version": 2},
    )  # fmt: skip
    assert back.json()["data"]["completed_at"] is None
    null = await api.call(
        "PATCH", f"/product/roadmap-items/{item['id']}", "CPO", json={"title": None, "version": 3}
    )
    assert null.status_code == 422
    lst = await api.call(
        "GET", "/product/roadmap-items", "CEO",
        params={"product_id": p["id"], "quarter": "2037-Q1", "sort_by": "target_date"},
    )  # fmt: skip
    assert lst.json()["meta"]["pagination"]["total"] == 2
    assert (await api.call("GET", f"/product/roadmap-items/{item['id']}", "CPO")).status_code == 200
    mgr = await api.call(
        "DELETE", f"/product/roadmap-items/{item['id']}", "MANAGER", department_id=uuid.uuid4()
    )
    assert mgr.status_code == 403
    assert (
        await api.call("DELETE", f"/product/roadmap-items/{item['id']}", "CPO")
    ).status_code == 204
    assert (await api.call("GET", f"/product/roadmap-items/{item['id']}", "CPO")).status_code == 404
    assert await audit_actions(db_session, item["id"]) == [
        "product.roadmap_item_create", "product.roadmap_item_delete",
        "product.roadmap_item_update", "product.roadmap_item_update",
    ]  # fmt: skip


async def test_release_and_first_launch_event(api: ApiClient, db_session: AsyncSession) -> None:
    p = await make_product(api, lifecycle_stage="development")
    r1 = await make(api, "releases", {"product_id": p["id"], "release_version": "1.0.0"})
    assert r1["status"] == "planned" and await outbox_for(db_session, p["id"]) == []
    dup = await api.call(
        "POST", "/product/releases", "CPO", json={"product_id": p["id"], "release_version": "1.0.0"}
    )
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    other = await make_product(api)
    same_v = await make(api, "releases", {"product_id": other["id"], "release_version": "1.0.0"})
    assert same_v["release_version"] == "1.0.0"
    no_p = await api.call(
        "POST", "/product/releases", "CPO",
        json={"product_id": str(uuid.uuid4()), "release_version": "9"},
    )  # fmt: skip
    assert no_p.status_code == 422
    rel = await api.call(
        "PATCH", f"/product/releases/{r1['id']}", "CPO", json={"status": "released", "version": 1}
    )
    assert rel.status_code == 200 and rel.json()["data"]["released_at"] is not None
    prod = (await api.call("GET", f"/product/products/{p['id']}", "CPO")).json()["data"]
    assert prod["lifecycle_stage"] == "launched" and prod["launched_at"] is not None
    events = await outbox_for(db_session, p["id"])
    assert events == [
        ("product.product_launched", {"product_id": p["id"], "launched_at": prod["launched_at"]})
    ]
    r2 = await make(
        api, "releases",
        {"product_id": p["id"], "release_version": "1.1.0", "status": "released",
         "released_at": "2037-02-01T00:00:00Z"},
    )  # fmt: skip
    assert r2["released_at"].startswith("2037-02-01")
    assert len(await outbox_for(db_session, p["id"])) == 1  # only the first release launches
    clash = await api.call(
        "PATCH", f"/product/releases/{r2['id']}", "CPO",
        json={"release_version": "1.0.0", "version": 1},
    )  # fmt: skip
    assert clash.status_code == 409
    null = await api.call(
        "PATCH", f"/product/releases/{r2['id']}", "CPO", json={"status": None, "version": 1}
    )
    assert null.status_code == 422
    lst = await api.call("GET", "/product/releases", "CEO", params={"product_id": p["id"]})
    assert lst.json()["meta"]["pagination"]["total"] == 2
    assert (await api.call("GET", f"/product/releases/{r1['id']}", "CPO")).status_code == 200
    missing = await api.call("GET", f"/product/releases/{uuid.uuid4()}", "CPO")
    assert missing.status_code == 404
    gone = await api.call("DELETE", f"/product/releases/{r1['id']}", "CPO")
    assert gone.status_code == 405
    assert "product.product_launch" in await audit_actions(db_session, p["id"])


async def test_direct_released_create_launches(api: ApiClient, db_session: AsyncSession) -> None:
    p = await make_product(api, lifecycle_stage="growth")
    await make(
        api, "releases", {"product_id": p["id"], "release_version": "2.0", "status": "released"}
    )
    prod = (await api.call("GET", f"/product/products/{p['id']}", "CPO")).json()["data"]
    assert prod["lifecycle_stage"] == "growth" and prod["launched_at"] is not None
    assert [e for e, _ in await outbox_for(db_session, p["id"])] == ["product.product_launched"]
    feature = await make(api, "features", {"product_id": p["id"], "name": "x"})
    rid = await api.call("GET", "/product/releases", "CPO", params={"product_id": p["id"]})
    release_id = rid.json()["data"][0]["id"]
    linked = await api.call(
        "PATCH", f"/product/features/{feature['id']}", "CPO",
        json={"release_id": release_id, "status": "released", "version": 1},
    )  # fmt: skip
    assert linked.status_code == 200
    payload = (await outbox_for(db_session, feature["id"]))[0][1]
    assert payload["release_id"] == release_id
    # launched product: delete → soft delete with lifecycle `sunset`
    assert (await api.call("DELETE", f"/product/products/{p['id']}", "CPO")).status_code == 204
    row = await db_session.get(Product, uuid.UUID(p["id"]))
    assert row is not None and row.lifecycle_stage == "sunset" and row.status == "retired"

"""T-201 — EP-91 products, EP-92 features (TC-PRD-001)."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import ApiClient
from tests.integration.product.helpers import audit_actions, code, make, make_product, outbox_for

pytestmark = pytest.mark.integration


async def test_product_crud(api: ApiClient, db_session: AsyncSession) -> None:
    p = await make_product(api, lifecycle_stage="development", target_launch_date="2037-03-01")
    assert p["status"] == "active" and p["version"] == 1 and p["launched_at"] is None
    dup = await api.call(
        "POST",
        "/product/products",
        "CPO",
        json={"code": p["code"], "name": "x", "owner_id": str(uuid.uuid4())},
    )
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    bad = await api.call("POST", "/product/products", "CPO", json={"code": "a b", "name": "x"})
    assert bad.status_code == 422
    got = await api.call("GET", f"/product/products/{p['id']}", "CEO")
    assert got.status_code == 200 and got.json()["data"]["code"] == p["code"]
    lst = await api.call(
        "GET",
        "/product/products",
        "CPO",
        params={"lifecycle_stage": "development", "sort_by": "code", "limit": 100},
    )
    assert p["id"] in [x["id"] for x in lst.json()["data"]]
    assert lst.json()["meta"]["pagination"]["total"] >= 1
    up = await api.call(
        "PATCH", f"/product/products/{p['id']}", "CPO", json={"name": "Đổi tên", "version": 1}
    )
    assert up.status_code == 200 and up.json()["data"]["version"] == 2
    stale = await api.call(
        "PATCH", f"/product/products/{p['id']}", "CPO", json={"name": "x", "version": 1}
    )
    assert stale.status_code == 409
    null = await api.call(
        "PATCH", f"/product/products/{p['id']}", "CPO", json={"name": None, "version": 2}
    )
    assert null.status_code == 422
    other = await make_product(api)
    clash = await api.call(
        "PATCH", f"/product/products/{p['id']}", "CPO", json={"code": other["code"], "version": 2}
    )
    assert clash.status_code == 409
    same = await api.call(
        "PATCH", f"/product/products/{p['id']}", "CPO", json={"code": p["code"], "version": 2}
    )
    assert same.status_code == 200
    assert (await api.call("DELETE", f"/product/products/{p['id']}", "CPO")).status_code == 204
    assert (await api.call("GET", f"/product/products/{p['id']}", "CPO")).status_code == 404
    assert await audit_actions(db_session, p["id"]) == [
        "product.product_create",
        "product.product_delete",
        "product.product_update",
        "product.product_update",
    ]


async def test_product_rbac_and_scope(api: ApiClient) -> None:
    body = {"code": code(), "name": "x", "owner_id": str(uuid.uuid4())}
    for role in ("CEO", "CFO", "VP_SALES", "EMPLOYEE", "ADMIN"):
        r = await api.call("POST", "/product/products", role, json=body)
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_ROLE", role
    mgr = await api.call(
        "POST", "/product/products", "MANAGER", json=body, department_id=uuid.uuid4()
    )
    assert mgr.status_code == 403 and mgr.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    p = await make_product(api)
    assert (
        await api.call("GET", f"/product/products/{p['id']}", "MANAGER", department_id=uuid.uuid4())
    ).status_code == 200
    rev = await api.call("GET", "/product/products", "REVIEWER")
    assert rev.status_code == 403 and rev.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    assert (await api.call("GET", "/product/products", "CFO")).status_code == 403
    missing = await api.call("GET", f"/product/products/{uuid.uuid4()}", "CPO")
    assert missing.status_code == 404


async def test_feature_crud_and_released_event(api: ApiClient, db_session: AsyncSession) -> None:
    p = await make_product(api)
    f = await make(api, "features", {"product_id": p["id"], "name": "Báo giá"})
    assert f["status"] == "planned"
    assert await outbox_for(db_session, f["id"]) == []
    bad = await api.call(
        "POST", "/product/features", "CPO", json={"product_id": str(uuid.uuid4()), "name": "x"}
    )
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    for field in ("release_id", "roadmap_item_id"):
        r = await api.call(
            "POST",
            "/product/features",
            "CPO",
            json={"product_id": p["id"], "name": "x", field: str(uuid.uuid4())},
        )
        assert r.status_code == 422, field
    up = await api.call(
        "PATCH", f"/product/features/{f['id']}", "CPO", json={"status": "released", "version": 1}
    )
    assert up.status_code == 200
    again = await api.call(
        "PATCH", f"/product/features/{f['id']}", "CPO", json={"name": "Báo giá 2", "version": 2}
    )
    assert again.status_code == 200
    events = await outbox_for(db_session, f["id"])
    assert events == [
        (
            "product.feature_released",
            {"feature_id": f["id"], "product_id": p["id"], "release_id": None},
        )
    ]
    null = await api.call(
        "PATCH", f"/product/features/{f['id']}", "CPO", json={"status": None, "version": 3}
    )
    assert null.status_code == 422
    direct = await make(
        api, "features", {"product_id": p["id"], "name": "Ngay", "status": "released"}
    )
    assert [e for e, _ in await outbox_for(db_session, direct["id"])] == [
        "product.feature_released"
    ]
    lst = await api.call("GET", "/product/features", "CEO", params={"product_id": p["id"]})
    assert lst.json()["meta"]["pagination"]["total"] == 2
    assert (await api.call("GET", f"/product/features/{f['id']}", "CPO")).status_code == 200
    assert (await api.call("DELETE", f"/product/features/{f['id']}", "CPO")).status_code == 204
    assert (await api.call("GET", f"/product/features/{f['id']}", "CPO")).status_code == 404
    assert "product.feature_delete" in await audit_actions(db_session, f["id"])


async def test_product_delete_blocked_by_open_work(api: ApiClient) -> None:
    p = await make_product(api)
    f = await make(api, "features", {"product_id": p["id"], "name": "x", "status": "in_progress"})
    r = await api.call("DELETE", f"/product/products/{p['id']}", "CPO")
    assert r.status_code == 422 and r.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    await api.call(
        "PATCH", f"/product/features/{f['id']}", "CPO", json={"status": "deprecated", "version": 1}
    )
    assert (await api.call("DELETE", f"/product/products/{p['id']}", "CPO")).status_code == 204

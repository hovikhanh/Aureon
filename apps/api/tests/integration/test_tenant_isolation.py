"""TC-M11-02..04 (T-603, R-DEC-21, 05 §2.3) — tenant isolation, fail closed.

TC-M11-02: tenant B cannot read / list / update / delete tenant A's data (HTTP + repository).
TC-M11-03: no tenant context → repository + session guard raise (no implicit default tenant).
TC-M11-04: outbox row + envelope carry `tenant_id`; consumer runs as the event's tenant; an event
           without `tenant_id` → DLQ without calling the handler.
"""

import uuid

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.tenant import (
    TenantContextMissingError,
    TenantMismatchError,
    current_tenant,
    reset_tenant,
    set_tenant,
    tenant_scope,
)
from app.modules.sales.models import Client
from app.modules.sales.repositories import ClientRepository
from tests.conftest import ApiClient
from tests.integration.sales.helpers import make_client

pytestmark = pytest.mark.integration

TENANT_B = uuid.UUID("00000000-0000-0000-0000-0000000000b2")


# ---------- TC-M11-02: HTTP ----------
async def test_tenant_b_cannot_read_or_list_tenant_a_client(api: ApiClient) -> None:
    cid = (await make_client(api))["id"]
    assert (await api.call("GET", f"/sales/clients/{cid}", "CEO")).status_code == 200
    r = await api.call("GET", f"/sales/clients/{cid}", "CEO", tenant_id=TENANT_B)
    assert r.status_code == 404, r.text  # existence not leaked across tenants
    listed = await api.call("GET", "/sales/clients", "CEO", tenant_id=TENANT_B)
    assert listed.status_code == 200
    assert cid not in {c["id"] for c in listed.json()["data"]}
    assert current_tenant() == DEFAULT_TENANT_ID  # request context did not leak into the test


async def test_tenant_b_cannot_update_or_delete_tenant_a_client(api: ApiClient) -> None:
    cid = (await make_client(api))["id"]
    p = await api.call(
        "PATCH", f"/sales/clients/{cid}", "VP_SALES", json={"version": 1}, tenant_id=TENANT_B
    )
    assert p.status_code == 404, p.text
    d = await api.call("DELETE", f"/sales/clients/{cid}", "CEO", tenant_id=TENANT_B)
    assert d.status_code in (403, 404), d.text
    assert (await api.call("GET", f"/sales/clients/{cid}", "CEO")).status_code == 200


async def test_tenant_b_writes_land_in_tenant_b(api: ApiClient, db_session: AsyncSession) -> None:
    r = await api.call(
        "POST", "/sales/clients", "VP_SALES", json={"name": f"B-{uuid.uuid4().hex[:8]}"},
        tenant_id=TENANT_B,
    )  # fmt: skip
    assert r.status_code == 201, r.text
    cid = uuid.UUID(r.json()["data"]["id"])
    with tenant_scope(TENANT_B):
        row = await ClientRepository(db_session).get(cid)
    assert row is not None and row.tenant_id == TENANT_B
    assert await ClientRepository(db_session).get(cid) is None  # invisible to tenant A


async def test_token_without_tenant_claim_is_rejected(api: ApiClient) -> None:
    from app.core.security import sign_access_token

    token, _ = sign_access_token(
        user_id=uuid.uuid4(), email="x@abc.test", role="CEO", role_id="CEO",
        permissions=["sales:read"], department_id=None,
    )  # fmt: skip
    r = await api.http.get("/api/v1/sales/clients", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"


# ---------- TC-M11-02: layer 2 (session guard) catches raw ORM statements ----------
async def test_session_guard_filters_orm_select_and_bulk_update(
    api: ApiClient, db_session: AsyncSession
) -> None:
    cid = uuid.UUID((await make_client(api))["id"])
    with tenant_scope(TENANT_B):
        n = await db_session.execute(select(func.count(Client.id)).where(Client.id == cid))
        assert n.scalar_one() == 0  # no repository involved: the guard added the criteria
        res = await db_session.execute(
            update(Client).where(Client.id == cid).values(industry="hijacked")
        )
        assert res.rowcount == 0  # type: ignore[attr-defined]
    row = await ClientRepository(db_session).get(cid)
    assert row is not None and row.industry != "hijacked"


# ---------- TC-M11-03: fail closed ----------
async def test_no_tenant_context_fails_closed(db_session: AsyncSession) -> None:
    token = set_tenant(None)
    try:
        with pytest.raises(TenantContextMissingError):
            await ClientRepository(db_session).list()
        with pytest.raises(TenantContextMissingError):
            await db_session.execute(select(Client.id))  # layer 2 alone
        with pytest.raises(TenantContextMissingError):
            await ClientRepository(db_session).create(
                name="x", normalized_name="x", status="prospect", source="MANUAL"
            )
    finally:
        reset_tenant(token)
    await db_session.rollback()


async def test_cross_tenant_write_is_refused(db_session: AsyncSession) -> None:
    repo = ClientRepository(db_session)
    with pytest.raises(TenantMismatchError):
        await repo.create(
            name="x", normalized_name="x", status="prospect", source="MANUAL", tenant_id=TENANT_B
        )
    c = await repo.create(name="ok", normalized_name="ok", status="prospect", source="MANUAL")
    assert c.tenant_id == DEFAULT_TENANT_ID
    with pytest.raises(TenantMismatchError):
        await repo.update(c, tenant_id=TENANT_B)
    db_session.add(
        Client(
            name="y", normalized_name="y", status="prospect", source="MANUAL", tenant_id=TENANT_B
        )
    )
    with pytest.raises(TenantMismatchError):
        await db_session.flush()  # layer 2 on flush
    await db_session.rollback()

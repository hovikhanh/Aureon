"""TC-SYS-007 — immutable `platform.audit_logs`: trigger, ORM guard, DB role, `@auditable`.

Runs in the rolled-back `db_session`; trigger checks use savepoints so the outer tx survives.
"""

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from pydantic import BaseModel
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import MASK, Actor, auditable, current_actor, record_audit, set_actor
from app.core.deps import get_db
from app.core.security import hash_password
from app.main import create_app
from app.modules.auth.models import Role, User
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.platform.models import AuditLog, AuditLogImmutableError
from app.modules.platform.repositories import AuditRepository

pytestmark = pytest.mark.integration


async def _one(db: AsyncSession, audit_id: uuid.UUID) -> AuditLog:
    return (await db.execute(select(AuditLog).where(AuditLog.id == audit_id))).scalar_one()


async def test_insert_and_list(db_session: AsyncSession) -> None:
    repo = AuditRepository(db_session)
    tid = uuid.uuid4()
    row = await repo.create(
        action="finance.invoice_pay",
        target_schema="finance",
        target_table="invoices",
        target_id=tid,
        before={"status": "OPEN"},
        after={"status": "PAID", "amount_paid": 27_500_000},
        why="test",
        actor=Actor(type="USER", user_id=uuid.uuid4(), role="CFO"),
    )
    assert row.actor_type == "USER"
    assert row.actor_role == "CFO"
    assert row.occurred_at is not None
    items, total = await repo.list(target_id=tid)
    assert total == 1
    assert items[0].after == {"status": "PAID", "amount_paid": 27_500_000}
    items, total = await repo.list(action="finance.invoice_pay", target_table="invoices", limit=5)
    assert total >= 1
    assert not hasattr(repo, "update")
    assert not hasattr(repo, "delete")


async def test_pii_masked(db_session: AsyncSession) -> None:
    audit_id = await record_audit(
        db_session,
        action="hr.salary_update",
        before={"salary": 30_000_000, "employee_id": "EMP-0001"},
        after={"salary": 35_000_000, "items": [{"bank_account": "0123"}]},
    )
    row = await _one(db_session, audit_id)
    assert row.before == {"salary": MASK, "employee_id": "EMP-0001"}
    assert row.after == {"salary": MASK, "items": [{"bank_account": MASK}]}
    assert row.actor_type == "SYSTEM"  # no request principal → SYSTEM


@pytest.mark.parametrize("sql", ["UPDATE platform.audit_logs SET why = 'x' WHERE id = :id",
                                 "DELETE FROM platform.audit_logs WHERE id = :id"])  # fmt: skip
async def test_trigger_blocks_raw_sql(db_session: AsyncSession, sql: str) -> None:
    audit_id = await record_audit(db_session, action="platform.test")
    sp = await db_session.begin_nested()
    with pytest.raises(DBAPIError, match="append-only"):
        await db_session.execute(text(sql), {"id": audit_id})
    await sp.rollback()
    assert (await _one(db_session, audit_id)).why is None


async def test_orm_guard_blocks_update_and_delete(db_session: AsyncSession) -> None:
    audit_id = await record_audit(db_session, action="platform.test")
    sp = await db_session.begin_nested()
    row = await _one(db_session, audit_id)
    row.why = "tamper"
    with pytest.raises(AuditLogImmutableError, match="UPDATE"):
        await db_session.flush()
    await sp.rollback()
    db_session.expunge_all()
    sp = await db_session.begin_nested()
    await db_session.delete(await _one(db_session, audit_id))
    with pytest.raises(AuditLogImmutableError, match="DELETE"):
        await db_session.flush()
    await sp.rollback()
    db_session.expunge_all()
    with pytest.raises(AuditLogImmutableError, match="bulk"):
        await db_session.execute(update(AuditLog).values(why="x"))
    with pytest.raises(AuditLogImmutableError, match="bulk"):
        await db_session.execute(delete(AuditLog))


async def test_audit_writer_role_grants(db_session: AsyncSession) -> None:
    rows = await db_session.execute(
        text(
            "SELECT privilege_type FROM information_schema.role_table_grants "
            "WHERE grantee = 'app_audit_writer' AND table_schema = 'platform' "
            "AND table_name = 'audit_logs' ORDER BY 1"
        )
    )
    assert [r[0] for r in rows] == ["INSERT", "SELECT"]
    # Acting as the role: INSERT works, UPDATE is refused by privileges (before the trigger).
    sp = await db_session.begin_nested()
    await db_session.execute(text("SET LOCAL ROLE app_audit_writer"))
    await db_session.execute(
        text(
            "INSERT INTO platform.audit_logs (id, actor_type, action) "
            "VALUES (gen_random_uuid(), 'SYSTEM', 'platform.role_test')"
        )
    )
    with pytest.raises(DBAPIError, match="permission denied"):
        await db_session.execute(text("UPDATE platform.audit_logs SET why = 'x'"))
    await sp.rollback()


class InvoiceOut(BaseModel):
    id: uuid.UUID
    status: str
    bank_account: str


class FakeInvoiceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @auditable("finance.invoice_pay", "finance.invoices")
    async def pay(self, invoice_id: uuid.UUID, *, fail: bool = False) -> InvoiceOut:
        if fail:
            raise ValueError("BR violated")
        return InvoiceOut(id=invoice_id, status="PAID", bank_account="0123456789")


async def test_decorator_writes_in_same_tx(db_session: AsyncSession) -> None:
    set_actor(Actor(type="USER", user_id=uuid.uuid4(), role="CFO"))
    try:
        inv = uuid.uuid4()
        await FakeInvoiceService(db_session).pay(inv)
        items, total = await AuditRepository(db_session).list(target_id=inv)
    finally:
        set_actor(Actor())
    assert total == 1
    row = items[0]
    assert (row.action, row.target_schema, row.target_table) == (
        "finance.invoice_pay", "finance", "invoices",
    )  # fmt: skip
    assert row.actor_role == "CFO"
    assert row.after == {"id": str(inv), "status": "PAID", "bank_account": MASK}
    assert "request_id" in row.metadata_


async def test_decorator_no_row_on_error(db_session: AsyncSession) -> None:
    inv = uuid.uuid4()
    with pytest.raises(ValueError):
        await FakeInvoiceService(db_session).pay(inv, fail=True)
    assert (await AuditRepository(db_session).list(target_id=inv))[1] == 0


async def test_rollback_removes_audit_row(db_session: AsyncSession) -> None:
    inv = uuid.uuid4()
    sp = await db_session.begin_nested()  # the "service transaction"
    await FakeInvoiceService(db_session).pay(inv)
    assert (await AuditRepository(db_session).list(target_id=inv))[1] == 1
    await sp.rollback()
    assert (await AuditRepository(db_session).list(target_id=inv))[1] == 0


def test_decorator_validates_names() -> None:
    with pytest.raises(ValueError, match=r"<module>\.<verb>"):
        auditable("pay", "finance.invoices")
    with pytest.raises(ValueError, match=r"<schema>\.<table>"):
        auditable("finance.invoice_pay", "invoices")
    assert current_actor().type == "SYSTEM"


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test/api/v1"
    ) as c:
        yield c


async def test_login_logout_reuse_are_audited(
    db_session: AsyncSession, client: httpx.AsyncClient
) -> None:
    role = Role(
        code="CFO",
        role_ref="ROLE-02",
        name_vi="GĐ tài chính",
        name_en="CFO",
        permissions=list(ROLE_PERMISSIONS["CFO"]),
        scope_rules={},
        pillars=["F", "S"],
    )
    db_session.add(role)
    await db_session.flush()
    user = User(
        email=f"cfo-{uuid.uuid4().hex[:6]}@abc.test",
        password_hash=hash_password("pw-123456"),
        full_name="CFO",
        role_id=role.id,
    )
    db_session.add(user)
    await db_session.flush()

    data = (
        await client.post("/auth/login", json={"email": user.email, "password": "pw-123456"})
    ).json()["data"]
    rotated = (
        await client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]})
    ).json()["data"]
    await client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]})  # reuse
    login2 = (
        await client.post("/auth/login", json={"email": user.email, "password": "pw-123456"})
    ).json()["data"]
    r = await client.post(
        "/auth/logout",
        json={"refresh_token": login2["refresh_token"]},
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
    )
    assert r.status_code == 204
    items, _ = await AuditRepository(db_session).list(target_id=user.id, limit=10)
    actions = sorted(i.action for i in items)
    assert actions == ["auth.login", "auth.login", "auth.logout", "auth.refresh_reuse"]
    login_row = next(i for i in items if i.action == "auth.login")
    assert (login_row.actor_type, login_row.actor_role) == ("USER", "CFO")
    assert all("token" not in str(i.metadata_) for i in items)

"""TC-SYS-004 (integration) — `BaseRepository.list_page` returns `(items, total)` on real PG."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_repository import BaseRepository
from app.core.security import hash_password
from app.modules.auth.models import Role, User

pytestmark = pytest.mark.integration


@pytest.fixture
async def users(db_session: AsyncSession) -> tuple[Role, list[User]]:
    role = Role(
        code="EMPLOYEE",
        role_ref="ROLE-09",
        name_vi="Nhân viên",
        name_en="Employee",
        permissions=["execution:read"],
        scope_rules={},
        pillars=[],
    )
    db_session.add(role)
    await db_session.flush()
    tag = uuid.uuid4().hex[:6]
    pw = hash_password("x")
    rows = [
        User(
            email=f"u{i:02d}-{tag}@abc.test",
            password_hash=pw,
            full_name=f"User {i:02d}",
            role_id=role.id,
            is_active=i % 3 != 0,
        )
        for i in range(25)
    ]
    db_session.add_all(rows)
    await db_session.flush()
    return role, rows


async def test_list_page_total_and_slice(
    db_session: AsyncSession, users: tuple[Role, list[User]]
) -> None:
    role, _ = users
    repo = BaseRepository(db_session, User)
    items, total = await repo.list_page(
        limit=10, offset=20, sort_by="full_name", order="asc", filters={"role_id": role.id}
    )
    assert total == 25
    assert [u.full_name for u in items] == [f"User {i:02d}" for i in range(20, 25)]


async def test_list_page_filters_and_soft_delete(
    db_session: AsyncSession, users: tuple[Role, list[User]]
) -> None:
    role, rows = users
    repo = BaseRepository(db_session, User)
    await repo.soft_delete(rows[1])
    items, total = await repo.list_page(filters={"role_id": role.id, "is_active": True})
    assert total == 15  # 16 active (i % 3 != 0) minus 1 soft-deleted
    assert len(items) == 15
    assert rows[1] not in items


async def test_list_page_rejects_unknown_columns(db_session: AsyncSession) -> None:
    repo = BaseRepository(db_session, User)
    with pytest.raises(ValueError, match="no column"):
        await repo.list_page(filters={"nope": 1})
    with pytest.raises(ValueError, match="no column"):
        await repo.list_page(sort_by="nope")

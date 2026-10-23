"""T-018 — C19 optimistic locking: `PATCH` with `If-Match` / body `version` → `409 CONFLICT_STATE`.

No business PATCH endpoint exists yet (domain modules start in S1), so the HTTP contract is
exercised through a test-only router mounted on a fresh app with the real error handlers.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

import httpx
import pytest
from fastapi import APIRouter, Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.base_repository import BaseRepository
from app.core.concurrency import IfMatch, expected_version, parse_if_match
from app.core.config import get_config
from app.core.deps import get_db
from app.core.errors import ConflictStateError, NotFoundError, ValidationError
from app.core.handlers import install_error_handlers
from app.core.security import hash_password
from app.modules.auth.models import Role, User

pytestmark = pytest.mark.integration


class UserPatch(BaseModel):
    full_name: str
    version: int | None = None


class UserPatched(BaseModel):
    id: uuid.UUID
    full_name: str
    version: int


def _app() -> FastAPI:
    router = APIRouter()

    @router.patch("/users/{user_id}", response_model=UserPatched)
    async def patch_user(
        user_id: uuid.UUID,
        body: UserPatch,
        db: Annotated[AsyncSession, Depends(get_db)],
        if_match: IfMatch = None,
    ) -> Any:
        repo = BaseRepository(db, User)
        obj = await repo.get(user_id)
        if obj is None:
            raise NotFoundError
        exp = expected_version(if_match, body.version)
        await repo.update(obj, expected_version=exp, full_name=body.full_name)
        return obj

    app = FastAPI()
    install_error_handlers(app)
    app.include_router(router)
    return app


async def _user(db: AsyncSession, role: Role) -> User:
    u = User(
        email=f"lock-{uuid.uuid4().hex[:8]}@abc.test",
        password_hash=hash_password("x"),
        full_name="Trước",
        role_id=role.id,
    )
    db.add(u)
    await db.flush()
    await db.refresh(u)
    return u


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    app = _app()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_patch_with_matching_if_match_bumps_version(
    client: httpx.AsyncClient, db_session: AsyncSession, roles: dict[str, Role]
) -> None:
    u = await _user(db_session, roles["EMP"])
    assert u.version == 1
    r = await client.patch(f"/users/{u.id}", json={"full_name": "Sau"}, headers={"If-Match": "1"})
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2 and r.json()["full_name"] == "Sau"
    r = await client.patch(f"/users/{u.id}", json={"full_name": "Lần 3", "version": 2})
    assert (r.status_code, r.json()["version"]) == (200, 3)  # body `version` (10 §1.1)


async def test_patch_with_stale_version_is_409(
    client: httpx.AsyncClient, db_session: AsyncSession, roles: dict[str, Role]
) -> None:
    u = await _user(db_session, roles["EMP"])
    ok = await client.patch(f"/users/{u.id}", json={"full_name": "A"}, headers={"If-Match": '"1"'})
    assert ok.status_code == 200
    r = await client.patch(f"/users/{u.id}", json={"full_name": "B"}, headers={"If-Match": "1"})
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "CONFLICT_STATE"
    assert err["details"] == {"current_version": 2, "expected_version": 1}
    await db_session.refresh(u)
    assert (u.full_name, u.version) == ("A", 2)  # loser changed nothing


@pytest.mark.parametrize(
    ("headers", "body_version"),
    [({}, None), ({"If-Match": "abc"}, None), ({"If-Match": "1"}, 2)],
)
async def test_patch_version_missing_or_inconsistent_is_422(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    roles: dict[str, Role],
    headers: dict[str, str],
    body_version: int | None,
) -> None:
    u = await _user(db_session, roles["EMP"])
    body: dict[str, Any] = {"full_name": "X", "version": body_version}
    r = await client.patch(f"/users/{u.id}", json=body, headers=headers)
    assert (r.status_code, r.json()["error"]["code"]) == (422, "VALIDATION_ERROR")
    await db_session.refresh(u)
    assert u.version == 1


async def test_concurrent_patches_same_version_exactly_one_wins(roles: dict[str, Role]) -> None:
    """Two real connections, both read v1: row lock serialises them → one 200, one 409."""
    engine = create_async_engine(get_config().database_url.get_secret_value(), poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        role = await s.get(Role, roles["EMP"].id)
        if role is None:  # roles fixture runs in a rolled-back tx; seeded row must exist
            pytest.fail("EMPLOYEE role not seeded — run `uv run python -m app.seed`")
        u = await _user(s, role)
        await s.commit()
    try:

        async def attempt(name: str) -> str:
            async with maker() as s:
                obj = await s.get(User, u.id)
                assert obj is not None and obj.version == 1
                await asyncio.sleep(0.05)  # both have read v1 before either writes
                try:
                    await BaseRepository(s, User).update(obj, expected_version=1, full_name=name)
                    await asyncio.sleep(0.1)  # hold the row lock while the other waits
                    await s.commit()
                    return "ok"
                except ConflictStateError:
                    await s.rollback()
                    return "conflict"

        results = await asyncio.gather(attempt("A"), attempt("B"))
        assert sorted(results) == ["conflict", "ok"]
        async with maker() as s:
            final = await s.get(User, u.id)
            assert final is not None and final.version == 2
    finally:
        async with maker() as s:
            await s.execute(delete(User).where(User.id == u.id))
            await s.commit()
        await engine.dispose()


async def test_update_without_expected_version_still_bumps(
    db_session: AsyncSession, roles: dict[str, Role]
) -> None:
    u = await _user(db_session, roles["EMP"])
    await BaseRepository(db_session, User).update(u, full_name="Y")
    assert u.version == 2


def test_parse_if_match_forms() -> None:
    assert parse_if_match(None) is None
    assert parse_if_match("  ") is None
    assert parse_if_match("7") == 7
    assert parse_if_match('"7"') == 7
    assert parse_if_match('W/"7"') == 7
    with pytest.raises(ValidationError):
        parse_if_match("*")
    assert expected_version(None, 4) == 4
    assert expected_version("4", 4) == 4

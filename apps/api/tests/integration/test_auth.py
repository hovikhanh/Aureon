"""TC-AUTH-* (integration) — EP-02 login, EP-03 me, EP-06 refresh rotation, EP-07 logout.

Runs against the compose Postgres inside one rolled-back transaction (`db_session`).
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import hash_password, sign_access_token
from app.main import create_app
from app.modules.auth.models import RefreshToken, Role, User
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

pytestmark = pytest.mark.integration

PASSWORD = "Demo!Pass123"


@pytest.fixture
async def ceo(db_session: AsyncSession, roles: dict[str, Role]) -> User:
    role = roles["CEO"]
    user = User(
        email=f"ceo-{uuid.uuid4().hex[:8]}@abc.test",
        password_hash=hash_password(PASSWORD),
        full_name="Nguyễn Văn CEO",
        role_id=role.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api/v1") as c:
        yield c


async def _login(client: httpx.AsyncClient, email: str, password: str = PASSWORD) -> httpx.Response:
    return await client.post("/auth/login", json={"email": email, "password": password})


async def test_login_ok_returns_envelope_and_valid_token(
    client: httpx.AsyncClient, ceo: User
) -> None:
    r = await _login(client, ceo.email.upper())  # email is case-insensitive (citext)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert set(r.json()) == {"data", "meta"}
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 900
    assert data["user"]["role_code"] == "CEO"
    assert "password_hash" not in data["user"]
    assert sorted(data["user"]["permissions"]) == sorted(ROLE_PERMISSIONS["CEO"])

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200
    assert me.json()["data"]["id"] == str(ceo.id)
    assert me.json()["data"]["last_login_at"] is not None


async def test_login_wrong_password_401(client: httpx.AsyncClient, ceo: User) -> None:
    r = await _login(client, ceo.email, "wrong-password")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_unknown_email_same_401(client: httpx.AsyncClient) -> None:
    r = await _login(client, "nobody@abc.test")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_validation_422(client: httpx.AsyncClient) -> None:
    r = await client.post("/auth/login", json={"email": "not-an-email", "password": "x"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    r = await client.post("/auth/login", json={"email": "a@b.vn", "password": "x", "role": "CEO"})
    assert r.status_code == 422  # extra=forbid: role is never taken from the body


async def test_inactive_user_401(
    client: httpx.AsyncClient, ceo: User, db_session: AsyncSession
) -> None:
    ceo.is_active = False
    await db_session.flush()
    assert (await _login(client, ceo.email)).status_code == 401


async def test_lockout_after_5_failures(client: httpx.AsyncClient, ceo: User) -> None:
    for _ in range(5):
        assert (await _login(client, ceo.email, "bad")).status_code == 401
    assert ceo.locked_until is not None
    # Correct password is still refused while locked.
    assert (await _login(client, ceo.email)).status_code == 401


async def test_success_resets_failed_count(client: httpx.AsyncClient, ceo: User) -> None:
    await _login(client, ceo.email, "bad")
    assert ceo.failed_login_count == 1
    assert (await _login(client, ceo.email)).status_code == 200
    assert ceo.failed_login_count == 0


async def test_me_requires_token(client: httpx.AsyncClient) -> None:
    r = await client.get("/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_me_expired_token_401(client: httpx.AsyncClient, ceo: User) -> None:
    token, _ = sign_access_token(
        user_id=ceo.id,
        email=ceo.email,
        role="CEO",
        role_id=str(ceo.role_id),
        permissions=[],
        department_id=None,
        now=datetime.now(UTC) - timedelta(hours=1),
        ttl_seconds=60,
    )
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


async def test_me_tampered_token_401(client: httpx.AsyncClient, ceo: User) -> None:
    token = (await _login(client, ceo.email)).json()["data"]["access_token"]
    head, payload, sig = token.split(".")
    bad = f"{head}.{payload}.{sig[:-4]}AAAA"
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {bad}"})
    assert r.status_code == 401


async def test_refresh_rotates_and_reuse_revokes_family(
    client: httpx.AsyncClient, ceo: User, db_session: AsyncSession
) -> None:
    first = (await _login(client, ceo.email)).json()["data"]["refresh_token"]

    r = await client.post("/auth/refresh", json={"refresh_token": first})
    assert r.status_code == 200, r.text
    second = r.json()["data"]["refresh_token"]
    assert second != first
    assert r.json()["data"]["access_token"]

    # Re-using the rotated token → 401 and the whole chain (incl. `second`) is revoked.
    r = await client.post("/auth/refresh", json={"refresh_token": first})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "REFRESH_TOKEN_INVALID"
    r = await client.post("/auth/refresh", json={"refresh_token": second})
    assert r.status_code == 401

    rows = (
        (await db_session.execute(select(RefreshToken).where(RefreshToken.user_id == ceo.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 2
    assert len({t.family_id for t in rows}) == 1
    assert all(t.revoked_at is not None for t in rows)
    assert all(len(t.token_hash) == 64 for t in rows)  # only the sha256 is stored


async def test_refresh_unknown_and_expired(
    client: httpx.AsyncClient, ceo: User, db_session: AsyncSession
) -> None:
    r = await client.post("/auth/refresh", json={"refresh_token": "x" * 40})
    assert r.status_code == 401
    raw = (await _login(client, ceo.email)).json()["data"]["refresh_token"]
    token = (await db_session.execute(select(RefreshToken))).scalars().first()
    assert token is not None
    token.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.flush()
    assert (await client.post("/auth/refresh", json={"refresh_token": raw})).status_code == 401


async def test_refresh_inactive_user(
    client: httpx.AsyncClient, ceo: User, db_session: AsyncSession
) -> None:
    raw = (await _login(client, ceo.email)).json()["data"]["refresh_token"]
    ceo.is_active = False
    await db_session.flush()
    assert (await client.post("/auth/refresh", json={"refresh_token": raw})).status_code == 401


async def test_logout_revokes_refresh_token(client: httpx.AsyncClient, ceo: User) -> None:
    data = (await _login(client, ceo.email)).json()["data"]
    auth = {"Authorization": f"Bearer {data['access_token']}"}
    r = await client.post(
        "/auth/logout", json={"refresh_token": data["refresh_token"]}, headers=auth
    )
    assert r.status_code == 204
    assert r.content == b""
    r = await client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r.status_code == 401
    # Idempotent: second logout is still 204.
    r = await client.post(
        "/auth/logout", json={"refresh_token": data["refresh_token"]}, headers=auth
    )
    assert r.status_code == 204


async def test_logout_requires_token(client: httpx.AsyncClient) -> None:
    r = await client.post("/auth/logout", json={"refresh_token": "x" * 40})
    assert r.status_code == 401


async def test_no_register_endpoint(client: httpx.AsyncClient) -> None:
    r = await client.post("/auth/register", json={})
    assert r.status_code == 404  # DEC-137
    assert r.json()["error"]["code"] == "NOT_FOUND"

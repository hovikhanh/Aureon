"""Shared test fixtures.

- RS256 keys: a throwaway 2048-bit pair generated in memory and injected through
  `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` (PEM env path of `core.security`) — tests never touch
  `./secrets` or `./keys`.
- `db_session`: an AsyncSession bound to one connection inside an outer transaction with
  `join_transaction_mode="create_savepoint"` — service-level `commit()` only releases a
  savepoint, and everything is rolled back after the test.
"""

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool


def _pem_pair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public = (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    return private, public


TEST_PRIVATE_PEM, TEST_PUBLIC_PEM = _pem_pair()
os.environ["JWT_PRIVATE_KEY"] = TEST_PRIVATE_PEM
os.environ["JWT_PUBLIC_KEY"] = TEST_PUBLIC_PEM


@pytest.fixture(autouse=True)
def _fresh_keys() -> Iterator[None]:
    from app.core.config import get_config
    from app.core.security import reset_key_cache

    get_config.cache_clear()
    reset_key_cache()
    yield
    get_config.cache_clear()
    reset_key_cache()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    from app.core.config import get_config

    engine = create_async_engine(get_config().database_url.get_secret_value(), poolclass=NullPool)
    async with engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            autoflush=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()
    await engine.dispose()


@pytest.fixture
async def roles(db_session: AsyncSession) -> dict[str, Any]:
    """The 10 seeded roles (T-008) — upserted inside the rolled-back test transaction."""
    from app.seed.auth_seed import SeedReport, seed_roles

    return await seed_roles(db_session, SeedReport())


class ApiClient:
    """httpx client on the real app, DB = the rolled-back `db_session`; tokens per role."""

    def __init__(self, http: Any, app: Any = None) -> None:
        self.http = http
        self.app = app

    @staticmethod
    def headers(
        role: str, *, department_id: Any = None, user_id: Any = None, idem: bool = False
    ) -> dict[str, str]:
        import uuid

        from app.core.security import sign_access_token
        from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

        token, _ = sign_access_token(
            user_id=user_id or uuid.uuid4(), email=f"{role.lower()}@abc.test", role=role,
            role_id=role, permissions=list(ROLE_PERMISSIONS[role]), department_id=department_id,
        )  # fmt: skip
        h = {"Authorization": f"Bearer {token}"}
        if idem:
            h["Idempotency-Key"] = str(uuid.uuid4())
        return h

    async def call(
        self, method: str, url: str, role: str = "CFO", *, json: Any = None,
        headers: dict[str, str] | None = None, department_id: Any = None,
        params: Any = None,
    ) -> Any:  # fmt: skip
        h = self.headers(role, department_id=department_id, idem=method == "POST")
        h.update(headers or {})
        return await self.http.request(method, f"/api/v1{url}", json=json, headers=h, params=params)


@pytest.fixture
async def api(db_session: AsyncSession) -> AsyncIterator[ApiClient]:
    import httpx

    from app.core.deps import get_db
    from app.main import create_app

    app = create_app()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield ApiClient(http, app)

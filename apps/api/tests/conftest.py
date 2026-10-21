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

"""Async engine + session factory (SQLAlchemy 2.0 async, psycopg 3 — CLAUDE.md §2.2).

One session per request, never shared; `expire_on_commit=False` avoids MissingGreenlet.
Engine is created lazily so importing the app never connects.
"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_config


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_config().database_url.get_secret_value(), pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False, autoflush=False)

"""Shared integration fixtures for DB-backed tests (T-101, T-102).

The dev Postgres (localhost:5432) is expected at Alembic ``head``. ``db_session`` runs each test
inside an outer transaction that is **rolled back** at the end (connection-bound session), so no
test writes ever survive — the shared DB is left exactly as it was. To make the integration
tests order-independent, ``db_session`` also seeds the 5 demo roles/users *inside that
rolled-back transaction* when the table is empty, so a test that needs seed data always has it
whether or not a previous test (e.g. a reset) wiped the committed rows.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_config
from app.db.session import build_engine
from app.modules.auth.models import Role
from app.seed import seed_all


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    eng = build_engine(get_config().database_url.get_secret_value())
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    """A session whose writes are always rolled back (outer-transaction isolation).

    The session is bound to a single connection with an open outer transaction; ``commit`` on the
    session only commits an inner SAVEPOINT, and the outer transaction is rolled back in teardown,
    so nothing persists to the shared DB.
    """
    connection: Connection = engine.connect()
    outer = connection.begin()
    maker = sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)
    session = maker(join_transaction_mode="create_savepoint")
    try:
        # Seed inside the rolled-back transaction if the DB is empty, so tests are self-sufficient.
        if session.scalar(select(Role).where(Role.code == "ROLE-01")) is None:
            seed_all(session)
            session.flush()
        yield session
    finally:
        session.close()
        if outer.is_active:
            outer.rollback()
        connection.close()

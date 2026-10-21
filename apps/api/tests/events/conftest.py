"""Event-bus fixtures (real PG, real commits — consumers open their own sessions).

Every row a test creates is keyed by an event type / id it owns and deleted on teardown, so
the shared dev DB is left as found. `InMemoryTransport` stands in for Celery/Redis.
"""

import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_config
from app.core.events.bus import ConsumerRegistry
from app.core.events.envelope import OUTBOX, PROCESSED
from app.core.events.relay import RELAY_PAUSE_LOCK


@dataclass
class InMemoryTransport:
    sent: list[tuple[str, dict[str, Any], int]] = field(default_factory=list)
    fail: bool = False

    def send(self, consumer_name: str, message: dict[str, Any], countdown: int = 0) -> None:
        if self.fail:
            raise ConnectionError("broker down")
        self.sent.append((consumer_name, message, countdown))


@pytest.fixture(scope="session", autouse=True)
def pause_live_relay() -> Iterator[None]:
    """Pause the compose celery-beat relay while the suite runs (exclusive advisory lock).

    Otherwise the live relay can publish a test's PENDING rows between `publish` and the
    test's own `relay_once` — a flaky race (seen once in the T-008 gate run).
    """
    engine = create_engine(get_config().database_url.get_secret_value(), poolclass=NullPool)
    with engine.connect() as conn:
        conn.execute(select(func.pg_advisory_lock(RELAY_PAUSE_LOCK)))
        try:
            yield
        finally:
            conn.execute(select(func.pg_advisory_unlock(RELAY_PAUSE_LOCK)))
    engine.dispose()


@pytest.fixture
async def factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(get_config().database_url.get_secret_value(), poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    created: list[uuid.UUID] = []
    maker.created = created  # type: ignore[attr-defined]
    yield maker
    async with maker() as s:
        # Clean up everything this test's outbox rows produced.
        ids = list(
            (await s.execute(select(OUTBOX.c.id).where(OUTBOX.c.aggregate_table == "test_events")))
            .scalars()
            .all()
        )
        ids += created
        if ids:
            await s.execute(delete(PROCESSED).where(PROCESSED.c.event_id.in_(ids)))
            await s.execute(delete(OUTBOX).where(OUTBOX.c.id.in_(ids)))
        await s.commit()
    await engine.dispose()


@pytest.fixture
def transport() -> InMemoryTransport:
    return InMemoryTransport()


@pytest.fixture
def registry() -> ConsumerRegistry:
    return ConsumerRegistry()

"""Celery side of the event bus: beat `relay_outbox_events` + worker `app.events.consume`.

Each task call runs its own event loop (`asyncio.run`) with a NullPool engine, so no
connection or loop is shared between Celery's prefork children.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from celery import Task
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_config
from app.core.events.bus import CONSUME_TASK, CeleryTransport
from app.core.events.consumer import Outcome, consume
from app.core.events.relay import RelayResult, relay_once
from app.worker import celery_app
from app.workers.consumers import load_consumers

load_consumers()

RELAY_TASK = "app.events.relay_outbox_events"


@asynccontextmanager
async def _engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(get_config().database_url.get_secret_value(), poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _relay(honor_pause: bool = True) -> RelayResult:
    async with _engine() as engine, AsyncSession(engine, expire_on_commit=False) as session:
        result = await relay_once(session, CeleryTransport(), honor_pause=honor_pause)
        await session.commit()
        return result


async def _consume(name: str, message: dict[str, Any], attempt: int) -> tuple[str, int | None]:
    async with _engine() as engine:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        result = await consume(factory, name, message, attempt)
        return result.outcome.value, result.retry_in


@celery_app.task(name=RELAY_TASK, time_limit=30, soft_time_limit=25)  # type: ignore[untyped-decorator]
def relay_outbox_events(honor_pause: bool = True) -> dict[str, int]:
    r = asyncio.run(_relay(honor_pause))
    return {"published": r.published, "failed": r.failed, "messages": r.messages}


@celery_app.task(  # type: ignore[untyped-decorator]
    name=CONSUME_TASK, bind=True, acks_late=True, reject_on_worker_lost=True,
    time_limit=60, soft_time_limit=50,
)  # fmt: skip
def consume_event(self: Task, name: str, message: dict[str, Any], attempt: int = 1) -> str:
    outcome, retry_in = asyncio.run(_consume(name, message, attempt))
    if outcome == Outcome.RETRY.value:
        # Re-enqueue with the next attempt number (5 s / 30 s / 120 s); the DLQ decision is
        # made by `consume` from `attempt`, so this never loops forever.
        self.apply_async(args=[name, message, attempt + 1], countdown=retry_in, queue="events")
    return outcome

"""Idempotent consumer wrapper (E3/E4, 10 §8.2).

`consume(session_factory, name, message, attempt)`:
1. Same transaction: `processed_events (event_id, consumer)` exists → skip (duplicate).
2. Run the handler, then insert `processed_events(DONE)` — both commit together, so a crash
   between "handled" and "recorded" is impossible.
3. No `tenant_id` in the envelope → straight to DLQ, no retry (fail closed, R-DEC-21);
   otherwise the handler runs inside `tenant_scope(envelope.tenant_id)`.
4. Handler error → rollback, return `RETRY` with the next backoff (5 s / 30 s / 120 s); after the
   3rd retry fails, record `processed_events(DLQ, attempts, last_error)` → EP-56 replays it.

`BaseConsumer` is the class form of the same contract for modules that prefer it.
"""

import enum
import logging
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.bus import REGISTRY, ConsumerRegistry
from app.core.events.envelope import PROCESSED, EventEnvelope
from app.core.tenant import tenant_scope

log = logging.getLogger("app.events.consumer")

RETRY_BACKOFF_SECONDS: tuple[int, ...] = (5, 30, 120)  # E4: 3 retries then DLQ
MAX_ATTEMPTS = len(RETRY_BACKOFF_SECONDS) + 1

SessionFactory = Callable[[], AsyncSession]


class Outcome(enum.StrEnum):
    DONE = "DONE"
    DUPLICATE = "DUPLICATE"
    RETRY = "RETRY"
    DLQ = "DLQ"


@dataclass(frozen=True)
class ConsumeResult:
    outcome: Outcome
    retry_in: int | None = None


async def _already(session: AsyncSession, event_id: uuid.UUID, name: str) -> bool:
    row = await session.execute(
        select(PROCESSED.c.status).where(
            PROCESSED.c.event_id == event_id, PROCESSED.c.consumer == name
        )
    )
    return row.first() is not None


@asynccontextmanager
async def _scope(tenant_id: uuid.UUID) -> AsyncIterator[None]:
    """Whole consumer transaction (handler + flush + commit) runs as the event's tenant."""
    with tenant_scope(tenant_id):
        yield


async def _to_dlq(
    session_factory: SessionFactory, event_id: uuid.UUID, name: str, attempt: int, error: str
) -> None:
    async with session_factory() as session:
        if not await _already(session, event_id, name):
            await session.execute(
                insert(PROCESSED).values(
                    id=uuid.uuid4(),
                    event_id=event_id,
                    consumer=name,
                    status="DLQ",
                    attempts=attempt,
                    last_error=error,
                )
            )
            await session.commit()


async def consume(
    session_factory: SessionFactory,
    name: str,
    message: dict[str, Any],
    attempt: int = 1,
    *,
    registry: ConsumerRegistry = REGISTRY,
) -> ConsumeResult:
    env = EventEnvelope.model_validate(message)
    handler = registry.get(name)
    if env.tenant_id is None:
        log.error("event %s has no tenant_id → DLQ for %s", env.event_id, name)
        await _to_dlq(session_factory, env.event_id, name, attempt, "TenantMissing: no tenant_id")
        return ConsumeResult(Outcome.DLQ)
    async with session_factory() as session, _scope(env.tenant_id):
        try:
            if await _already(session, env.event_id, name):
                await session.rollback()
                return ConsumeResult(Outcome.DUPLICATE)
            await handler(session, env)
            await session.execute(
                insert(PROCESSED).values(
                    id=uuid.uuid4(),
                    event_id=env.event_id,
                    consumer=name,
                    status="DONE",
                    attempts=attempt,
                )
            )
            await session.commit()
            return ConsumeResult(Outcome.DONE)
        except Exception as exc:
            await session.rollback()
            error = f"{type(exc).__name__}: {exc}"[:500]
            log.warning("consumer %s failed on %s (attempt %d)", name, env.event_id, attempt)

    if attempt < MAX_ATTEMPTS:
        return ConsumeResult(Outcome.RETRY, retry_in=RETRY_BACKOFF_SECONDS[attempt - 1])
    await _to_dlq(session_factory, env.event_id, name, attempt, error)
    log.error("event %s → DLQ for %s", env.event_id, name)  # alert ADMIN via EP-57 dlq_count
    return ConsumeResult(Outcome.DLQ)


async def release_dlq(session: AsyncSession, event_id: uuid.UUID, name: str) -> bool:
    """Drop the DLQ marker so a replay can process the event again (EP-56)."""
    result = await session.execute(
        delete(PROCESSED)
        .where(
            PROCESSED.c.event_id == event_id,
            PROCESSED.c.consumer == name,
            PROCESSED.c.status == "DLQ",
        )
        .returning(PROCESSED.c.id)
    )
    return result.first() is not None


class BaseConsumer:
    """Class form: subclass, set `name` + `event_types`, implement `handle`, call `register()`."""

    name: str
    event_types: tuple[str, ...]

    async def handle(self, session: AsyncSession, event: EventEnvelope) -> None:
        raise NotImplementedError

    @classmethod
    def register(cls, registry: ConsumerRegistry = REGISTRY) -> "BaseConsumer":
        inst = cls()
        registry.register(cls.name, cls.event_types, inst.handle)
        return inst

"""Outbox relay (E2, 10 §8.2): `PENDING` rows → broker → `PUBLISHED`.

Runs from Celery beat (exactly one instance). `FOR UPDATE SKIP LOCKED` makes a second relay
(or an overlapping tick) skip rows already being relayed instead of blocking — no deadlock and
no double publish. A broker failure leaves the row `PENDING` with `attempts += 1` and
`last_error`; after `MAX_RELAY_ATTEMPTS` it becomes `FAILED` (shown on EP-57).
Rows with no registered consumer are marked `PUBLISHED` (nothing to deliver).

Pause: every relay takes the *shared* advisory lock `RELAY_PAUSE_LOCK` (xact-scoped, so
relays never block each other). Holding it *exclusively* pauses relaying cluster-wide —
`SELECT pg_advisory_lock(<RELAY_PAUSE_LOCK>)` for maintenance / migrations, or the test
suite, whose own relays pass `honor_pause=False`.
"""

import logging
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.bus import REGISTRY, ConsumerRegistry, Transport
from app.core.events.envelope import OUTBOX, EventEnvelope, utcnow

log = logging.getLogger("app.events.relay")

BATCH_SIZE = 100
MAX_RELAY_ATTEMPTS = 5
RELAY_PAUSE_LOCK = 0x41555245_4F4E0001  # 'AUREON' + 1 — bigint advisory key


@dataclass(frozen=True)
class RelayResult:
    published: int = 0
    failed: int = 0
    messages: int = 0


def _envelope(row: object) -> EventEnvelope:
    return EventEnvelope(
        event_id=row.id,  # type: ignore[attr-defined]
        event_type=row.event_type,  # type: ignore[attr-defined]
        occurred_at=row.occurred_at,  # type: ignore[attr-defined]
        version=row.version,  # type: ignore[attr-defined]
        tenant_id=row.tenant_id,  # type: ignore[attr-defined]  # R-DEC-21, 10 §9.1
        producer=row.aggregate_schema,  # type: ignore[attr-defined]
        payload=row.payload,  # type: ignore[attr-defined]
    )


async def relay_once(
    session: AsyncSession,
    transport: Transport,
    *,
    registry: ConsumerRegistry = REGISTRY,
    batch_size: int = BATCH_SIZE,
    honor_pause: bool = True,
) -> RelayResult:
    """Relay one batch inside the caller's transaction; the caller commits."""
    if honor_pause:
        lock = func.pg_try_advisory_xact_lock_shared(RELAY_PAUSE_LOCK)
        if not (await session.execute(select(lock))).scalar_one():
            log.info("relay paused (advisory lock %s held)", RELAY_PAUSE_LOCK)
            return RelayResult()
    rows = (
        await session.execute(
            select(OUTBOX)
            .where(OUTBOX.c.status == "PENDING")
            .order_by(OUTBOX.c.occurred_at)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
    ).all()
    published = failed = messages = 0
    for row in rows:
        env = _envelope(row)
        targets = registry.consumers_for(env.event_type)
        try:
            for name in targets:
                transport.send(name, env.to_message())
                messages += 1
        except Exception as exc:  # broker down etc. — keep the row, retry next tick
            attempts = row.attempts + 1
            status = "FAILED" if attempts >= MAX_RELAY_ATTEMPTS else "PENDING"
            log.warning("relay failed for %s: %s", env.event_id, type(exc).__name__)
            await session.execute(
                update(OUTBOX)
                .where(OUTBOX.c.id == row.id)
                .values(attempts=attempts, status=status, last_error=str(exc)[:500])
            )
            failed += 1
            continue
        await session.execute(
            update(OUTBOX)
            .where(OUTBOX.c.id == row.id)
            .values(status="PUBLISHED", published_at=utcnow(), attempts=row.attempts + 1)
        )
        published += 1
    return RelayResult(published=published, failed=failed, messages=messages)

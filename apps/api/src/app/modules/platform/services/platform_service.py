"""Public service interface of `platform` — the only entry point for other modules."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import Page
from app.core.errors import NotFoundError
from app.core.events.bus import CeleryTransport, Transport
from app.core.events.consumer import release_dlq
from app.core.events.envelope import EventEnvelope
from app.modules.platform.repositories import DeadLetterRepository
from app.modules.platform.schemas import DeadLetterOut, ReplayOut


class PlatformService:
    def __init__(self, db: AsyncSession, transport: Transport | None = None) -> None:
        self.db = db
        self.transport: Transport = transport or CeleryTransport()
        self.dead_letters = DeadLetterRepository(db)

    async def list_dead_letters(
        self,
        *,
        limit: int,
        offset: int,
        consumer: str | None = None,
        event_type: str | None = None,
    ) -> Page[DeadLetterOut]:
        rows, total = await self.dead_letters.list(
            limit=limit, offset=offset, consumer=consumer, event_type=event_type
        )
        items = [
            DeadLetterOut(
                id=p.id,
                event_id=p.event_id,
                event_type=o.event_type,
                consumer=p.consumer,
                attempts=p.attempts,
                last_error=p.last_error,
            )
            for p, o in rows
        ]
        return Page(items=items, total=total, limit=limit, offset=offset)

    async def replay_dead_letter(self, id_: uuid.UUID) -> ReplayOut:
        """EP-56 replay: clear the DLQ marker, re-send to that one consumer (attempt 1).

        Idempotent per `(event_id, consumer)`: a second replay after success finds no DLQ row
        (404), and a re-delivered message is deduped by `processed_events`.
        """
        row = await self.dead_letters.get(id_)
        if row is None:
            raise NotFoundError("dead letter not found")
        processed, outbox = row
        await release_dlq(self.db, processed.event_id, processed.consumer)
        env = EventEnvelope(
            event_id=outbox.id,
            event_type=outbox.event_type,
            occurred_at=outbox.occurred_at,
            version=outbox.version,
            producer=outbox.aggregate_schema,
            payload=outbox.payload,
        )
        await self.db.commit()  # marker gone before the message can be consumed
        self.transport.send(processed.consumer, env.to_message())
        return ReplayOut(
            id=processed.id, event_id=env.event_id, consumer=processed.consumer, status="QUEUED"
        )

    async def dlq_count(self) -> int:
        return await self.dead_letters.dlq_count()

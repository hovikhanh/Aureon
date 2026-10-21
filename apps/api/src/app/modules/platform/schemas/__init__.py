"""Pydantic v2 schemas of `platform` (10 §4)."""

import uuid

from pydantic import BaseModel


class DeadLetterOut(BaseModel):
    """EP-56 row (10 §4.x): `{ event_id, event_type, consumer, attempts, last_error }`.

    `id` (= `processed_events.id`) is the `{id}` of `POST /platform/dead-letters/{id}/replay`:
    `event_id` alone is not unique across consumers. Proposed DEC to list it in 10.
    """

    id: uuid.UUID
    event_id: uuid.UUID
    event_type: str
    consumer: str
    attempts: int
    last_error: str | None


class ReplayOut(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    consumer: str
    status: str  # `QUEUED`

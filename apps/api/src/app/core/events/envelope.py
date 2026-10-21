"""Event envelope (10 §8.1) + the SQLAlchemy Core view of the two platform tables.

`core/` must not import `modules/` (CLAUDE.md §4.3), so the outbox / processed-events tables
are described here with `sqlalchemy.table()` (columns only — the DDL owner stays the
`platform` ORM models / migration 0001). A test asserts both descriptions agree.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import column, table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import TableClause

from app.core.enums import OUTBOX_STATUS, PROCESSING_STATUS


class EventEnvelope(BaseModel):
    """`{event_id, event_type, occurred_at, version, correlation_id, producer, payload}`."""

    event_id: uuid.UUID
    event_type: str
    occurred_at: datetime
    version: int = Field(default=1, ge=1)
    correlation_id: str | None = None
    producer: str
    payload: dict[str, Any]

    def to_message(self) -> dict[str, Any]:
        """JSON-safe dict for the broker (Celery JSON serializer)."""
        return self.model_dump(mode="json")


def utcnow() -> datetime:
    return datetime.now(UTC)


OUTBOX: TableClause = table(
    "outbox_events",
    column("id"),
    column("event_type"),
    column("version"),
    column("aggregate_schema"),
    column("aggregate_table"),
    column("aggregate_id"),
    column("occurred_at"),
    column("payload", JSONB),
    column("status", OUTBOX_STATUS),
    column("attempts"),
    column("published_at"),
    column("last_error"),
    column("created_at"),
    schema="platform",
)

PROCESSED: TableClause = table(
    "processed_events",
    column("id"),
    column("event_id"),
    column("consumer"),
    column("processed_at"),
    column("status", PROCESSING_STATUS),
    column("attempts"),
    column("last_error"),
    schema="platform",
)

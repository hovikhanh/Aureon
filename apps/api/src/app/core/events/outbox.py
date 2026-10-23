"""`publish_in_tx` — the ONLY way to emit a domain event (E1, 10 §8.2; CLAUDE.md §5.4).

Writes one `platform.outbox_events` row in the caller's transaction and returns the envelope.
Nothing reaches Redis until the relay picks the row up after commit, so a rollback drops the
event together with the business change.
"""

import uuid
from typing import Any

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.envelope import OUTBOX, EventEnvelope, utcnow
from app.core.events.registry import is_registered
from app.core.pii import PIIHit, scan_payload
from app.core.request_context import current_request_id
from app.core.tenant import require_tenant

# 10 §8.1: payload carries ids + aggregates only — never level 3–4 data (02 §6.3).
# Key names below + content patterns in `core.pii` (DEC-176).
FORBIDDEN_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "salary", "base_salary", "gross_salary", "net_salary", "salary_amount",
        "date_of_birth", "dob", "address", "national_id", "cccd", "bank_account",
        "bank_account_number", "emergency_contact", "password", "password_hash",
        "email", "phone", "full_name",
    }
)  # fmt: skip


class EventContractError(ValueError):
    """Programming error: unknown event type or a payload that breaks 10 §8.1."""


class PIIDetectedError(EventContractError):
    """Payload carries PII by field name or content (DEC-176). Message never holds the value."""

    def __init__(self, hits: list[PIIHit]) -> None:
        self.hits = hits
        where = ", ".join(f"{h.path} ({h.type})" for h in hits[:5])
        super().__init__(f"payload contains PII at {where}: PII / level 3-4 data not allowed")


def _check_payload(payload: Any) -> None:
    hits = scan_payload(payload, forbidden_keys=FORBIDDEN_PAYLOAD_KEYS)
    if hits:
        raise PIIDetectedError(hits)


async def publish_in_tx(
    session: AsyncSession,
    *,
    event_type: str,
    producer: str,
    aggregate_schema: str,
    aggregate_table: str,
    aggregate_id: uuid.UUID,
    payload: dict[str, Any],
    version: int = 1,
) -> EventEnvelope:
    if not is_registered(event_type):
        raise EventContractError(f"event type {event_type!r} not in 00 §4.5 registry")
    _check_payload(payload)
    tenant_id = require_tenant()  # R-DEC-21: an event always belongs to the caller's tenant
    envelope = EventEnvelope(
        event_id=uuid.uuid4(),
        event_type=event_type,
        occurred_at=utcnow(),
        version=version,
        correlation_id=current_request_id(),
        tenant_id=tenant_id,
        producer=producer,
        payload=payload,
    )
    await session.execute(
        insert(OUTBOX).values(
            id=envelope.event_id,
            event_type=event_type,
            version=version,
            aggregate_schema=aggregate_schema,
            aggregate_table=aggregate_table,
            aggregate_id=aggregate_id,
            occurred_at=envelope.occurred_at,
            payload=payload,
            tenant_id=tenant_id,
        )
    )
    return envelope

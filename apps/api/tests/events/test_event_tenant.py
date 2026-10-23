"""TC-M11-04 (T-603, R-DEC-21, 10 §9.1) — events carry and enforce the tenant.

- `publish_in_tx` writes `outbox_events.tenant_id` = current tenant; no context → raise.
- The relay copies it into the envelope; the consumer runs the handler as that tenant.
- An envelope without `tenant_id` goes straight to the DLQ, handler never called.
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.events.bus import ConsumerRegistry
from app.core.events.consumer import Outcome, consume
from app.core.events.envelope import OUTBOX, PROCESSED, EventEnvelope
from app.core.events.outbox import publish_in_tx
from app.core.events.relay import relay_once
from app.core.tenant import (
    TenantContextMissingError,
    current_tenant,
    reset_tenant,
    set_tenant,
    tenant_scope,
)
from tests.events.conftest import InMemoryTransport

pytestmark = pytest.mark.integration

EVT = "hr.hiring_plan_delayed"
NAME = "platform.on_hiring_plan_delayed"
TENANT_B = uuid.UUID("00000000-0000-0000-0000-0000000000b4")


async def _publish(factory: async_sessionmaker[AsyncSession]) -> uuid.UUID:
    async with factory() as s:
        env = await publish_in_tx(
            s, event_type=EVT, producer="hr", aggregate_schema="hr",
            aggregate_table="test_events", aggregate_id=uuid.uuid4(),
            payload={"hiring_plan_id": str(uuid.uuid4()), "days_late": 1},
        )  # fmt: skip
        await s.commit()
    return env.event_id


async def test_outbox_and_relay_carry_tenant(
    factory: async_sessionmaker[AsyncSession],
    transport: InMemoryTransport,
    registry: ConsumerRegistry,
) -> None:
    seen: list[uuid.UUID | None] = []

    async def handler(_s: AsyncSession, _e: EventEnvelope) -> None:
        seen.append(current_tenant())

    registry.register(NAME, (EVT,), handler)
    with tenant_scope(TENANT_B):
        eid = await _publish(factory)
    async with factory() as s:
        row = (await s.execute(select(OUTBOX).where(OUTBOX.c.id == eid))).one()
        assert row.tenant_id == TENANT_B
        await relay_once(s, transport, registry=registry, honor_pause=False)
        await s.commit()
    (_, msg, _) = next(x for x in transport.sent if x[1]["event_id"] == str(eid))
    assert msg["tenant_id"] == str(TENANT_B)
    assert (await consume(factory, NAME, msg, registry=registry)).outcome is Outcome.DONE
    assert seen == [TENANT_B]  # handler ran as the event's tenant, not the caller's


async def test_publish_without_tenant_fails_closed(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    token = set_tenant(None)
    try:
        with pytest.raises(TenantContextMissingError):
            await _publish(factory)
    finally:
        reset_tenant(token)


async def test_event_without_tenant_goes_to_dlq(
    factory: async_sessionmaker[AsyncSession], registry: ConsumerRegistry
) -> None:
    calls: list[uuid.UUID] = []

    async def handler(_s: AsyncSession, e: EventEnvelope) -> None:
        calls.append(e.event_id)

    registry.register(NAME, (EVT,), handler)
    eid = await _publish(factory)
    msg = EventEnvelope(
        event_id=eid, event_type=EVT, occurred_at="2026-10-20T00:00:00Z", producer="hr",
        payload={},
    ).to_message()  # fmt: skip
    assert msg["tenant_id"] is None
    assert (await consume(factory, NAME, msg, registry=registry)).outcome is Outcome.DLQ
    assert calls == []
    async with factory() as s:
        q = select(PROCESSED).where(PROCESSED.c.event_id == eid, PROCESSED.c.consumer == NAME)
        (row,) = (await s.execute(q)).all()
    assert row.status == "DLQ" and row.last_error.startswith("TenantMissing")

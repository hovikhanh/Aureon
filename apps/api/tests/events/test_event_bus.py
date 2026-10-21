"""TC-EVT-002 — relay fan-out + `SKIP LOCKED` (no double send, no deadlock); consumer dedupe."""

import asyncio
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.events import relay as relay_mod
from app.core.events.bus import ConsumerRegistry, consumer
from app.core.events.consumer import BaseConsumer, Outcome, consume
from app.core.events.envelope import OUTBOX, PROCESSED, EventEnvelope
from app.core.events.outbox import publish_in_tx
from app.core.events.relay import relay_once
from tests.events.conftest import InMemoryTransport

pytestmark = pytest.mark.integration

EVT = "hr.hiring_plan_delayed"


async def _publish(factory: async_sessionmaker[AsyncSession], n: int = 1) -> list[uuid.UUID]:
    ids = []
    async with factory() as s:
        for _ in range(n):
            env = await publish_in_tx(
                s,
                event_type=EVT,
                producer="hr",
                aggregate_schema="hr",
                aggregate_table="test_events",
                aggregate_id=uuid.uuid4(),
                payload={"hiring_plan_id": str(uuid.uuid4()), "days_late": 3},
            )
            ids.append(env.event_id)
        await s.commit()
    return ids


async def _relay(
    factory: async_sessionmaker[AsyncSession],
    transport: InMemoryTransport,
    registry: ConsumerRegistry,
) -> relay_mod.RelayResult:
    async with factory() as s:
        r = await relay_once(s, transport, registry=registry)
        await s.commit()
        return r


async def _status(factory: async_sessionmaker[AsyncSession], eid: uuid.UUID) -> tuple[str, object]:
    async with factory() as s:
        row = (await s.execute(select(OUTBOX).where(OUTBOX.c.id == eid))).one()
        return row.status, row.published_at


def _ours(transport: InMemoryTransport, ids: list[uuid.UUID]) -> list[tuple[str, str]]:
    wanted = {str(i) for i in ids}
    return [(n, m["event_id"]) for n, m, _ in transport.sent if m["event_id"] in wanted]


async def test_relay_fans_out_and_marks_published(
    factory: async_sessionmaker[AsyncSession],
    transport: InMemoryTransport,
    registry: ConsumerRegistry,
) -> None:
    async def noop(_s: AsyncSession, _e: EventEnvelope) -> None:
        return None

    registry.register("risk.on_hiring_plan_delayed", (EVT,), noop)
    registry.register("finance.on_hiring_plan_delayed", (EVT,), noop)
    (eid,) = await _publish(factory)
    await _relay(factory, transport, registry)
    sent = _ours(transport, [eid])
    assert sorted(n for n, _ in sent) == [
        "finance.on_hiring_plan_delayed",
        "risk.on_hiring_plan_delayed",
    ]
    status, published_at = await _status(factory, eid)
    assert status == "PUBLISHED"
    assert published_at is not None
    transport.sent.clear()
    await _relay(factory, transport, registry)
    assert _ours(transport, [eid]) == []  # not relayed twice


async def test_relay_without_consumers_still_publishes(
    factory: async_sessionmaker[AsyncSession],
    transport: InMemoryTransport,
    registry: ConsumerRegistry,
) -> None:
    (eid,) = await _publish(factory)
    await _relay(factory, transport, registry)
    assert (await _status(factory, eid))[0] == "PUBLISHED"


async def test_broker_failure_keeps_pending_then_failed(
    factory: async_sessionmaker[AsyncSession],
    registry: ConsumerRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def noop(_s: AsyncSession, _e: EventEnvelope) -> None:
        return None

    registry.register("risk.on_hiring_plan_delayed", (EVT,), noop)
    monkeypatch.setattr(relay_mod, "MAX_RELAY_ATTEMPTS", 2)
    down = InMemoryTransport(fail=True)
    (eid,) = await _publish(factory)
    await _relay(factory, down, registry)
    assert (await _status(factory, eid))[0] == "PENDING"
    await _relay(factory, down, registry)
    async with factory() as s:
        row = (await s.execute(select(OUTBOX).where(OUTBOX.c.id == eid))).one()
    assert (row.status, row.attempts) == ("FAILED", 2)
    assert "broker down" in row.last_error


async def test_concurrent_relays_skip_locked_no_double_send(
    factory: async_sessionmaker[AsyncSession], registry: ConsumerRegistry
) -> None:
    """Two relays at once: SKIP LOCKED splits rows — every event sent exactly once, no deadlock."""

    async def noop(_s: AsyncSession, _e: EventEnvelope) -> None:
        return None

    registry.register("risk.on_hiring_plan_delayed", (EVT,), noop)
    ids = await _publish(factory, n=30)
    a, b = InMemoryTransport(), InMemoryTransport()
    await asyncio.wait_for(
        asyncio.gather(_relay(factory, a, registry), _relay(factory, b, registry)), timeout=20
    )
    sent = _ours(a, ids) + _ours(b, ids)
    assert sorted(e for _, e in sent) == sorted(str(i) for i in ids)


async def test_consumer_idempotent(
    factory: async_sessionmaker[AsyncSession], registry: ConsumerRegistry
) -> None:
    calls: list[uuid.UUID] = []

    async def handle(_s: AsyncSession, e: EventEnvelope) -> None:
        calls.append(e.event_id)

    registry.register("risk.on_hiring_plan_delayed", (EVT,), handle)
    (eid,) = await _publish(factory)
    t = InMemoryTransport()
    await _relay(factory, t, registry)
    (_, msg, _) = next(x for x in t.sent if x[1]["event_id"] == str(eid))
    first = await consume(factory, "risk.on_hiring_plan_delayed", msg, registry=registry)
    again = await consume(factory, "risk.on_hiring_plan_delayed", msg, registry=registry)
    assert (first.outcome, again.outcome) == (Outcome.DONE, Outcome.DUPLICATE)
    assert calls == [eid]
    async with factory() as s:
        rows = (await s.execute(select(PROCESSED).where(PROCESSED.c.event_id == eid))).all()
    assert [(r.status, r.consumer) for r in rows] == [("DONE", "risk.on_hiring_plan_delayed")]


async def test_handler_writes_commit_with_processed_marker(
    factory: async_sessionmaker[AsyncSession], registry: ConsumerRegistry
) -> None:
    """The handler's own writes and the DONE marker share one transaction."""

    class Writer(BaseConsumer):
        name = "platform.on_hiring_plan_delayed"
        event_types = (EVT,)

        async def handle(self, session: AsyncSession, event: EventEnvelope) -> None:
            await publish_in_tx(  # a side-write in the same session
                session,
                event_type="risk.risk_proposed",
                producer="risk",
                aggregate_schema="risk",
                aggregate_table="test_events",
                aggregate_id=uuid.uuid4(),
                payload={"from_event": str(event.event_id)},
            )

    Writer.register(registry)
    (eid,) = await _publish(factory)
    msg = EventEnvelope(
        event_id=eid, event_type=EVT, occurred_at="2026-10-20T00:00:00Z", producer="hr", payload={}
    ).to_message()
    assert (await consume(factory, Writer.name, msg, registry=registry)).outcome == Outcome.DONE
    async with factory() as s:
        side = (await s.execute(select(OUTBOX).where(OUTBOX.c.event_type == "risk.risk_proposed",
                OUTBOX.c.aggregate_table == "test_events"))).all()  # fmt: skip
    assert any(r.payload == {"from_event": str(eid)} for r in side)


def test_registry_validation() -> None:
    reg = ConsumerRegistry()

    async def h(_s: AsyncSession, _e: EventEnvelope) -> None:
        return None

    with pytest.raises(ValueError, match="on_"):
        reg.register("risk.handle", (EVT,), h)
    with pytest.raises(ValueError, match="registry"):
        reg.register("risk.on_x", ("nope.nope",), h)
    reg.register("risk.on_x", (EVT,), h)
    with pytest.raises(ValueError, match="twice"):
        reg.register("risk.on_x", (EVT,), h)
    with pytest.raises(LookupError):
        reg.get("risk.on_missing")
    assert reg.consumers_for("finance.invoice_paid") == []


def test_decorator_registers_on_global_registry() -> None:
    from app.core.events.bus import REGISTRY

    name = f"ai.on_test_{uuid.uuid4().hex[:6]}"

    @consumer(name, EVT)
    async def h(_s: AsyncSession, _e: EventEnvelope) -> None:
        return None

    try:
        assert REGISTRY.get(name) is h
    finally:
        REGISTRY.handlers.pop(name)
        REGISTRY.routes[EVT].remove(name)


async def test_base_consumer_abstract() -> None:
    with pytest.raises(NotImplementedError):
        await BaseConsumer().handle(None, None)  # type: ignore[arg-type]

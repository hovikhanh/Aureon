"""TC-EVT-001 (worker side) — beat schedule + Celery task wrappers around relay / consume."""

import uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.events import bus
from app.core.events.consumer import Outcome
from app.core.events.envelope import OUTBOX, PROCESSED, EventEnvelope
from app.core.events.outbox import publish_in_tx
from app.worker import celery_app
from app.workers import events as worker_events

pytestmark = pytest.mark.integration

EVT = "finance.budget_exceeded"
NAME = "hr.on_budget_exceeded"


def test_beat_schedule_and_routing() -> None:
    sched = celery_app.conf.beat_schedule["relay-outbox-events"]
    assert sched["task"] == worker_events.RELAY_TASK
    assert sched["schedule"] == 2.0  # 07 §3: relay every 2 s
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.result_expires == 3600
    task = celery_app.tasks[bus.CONSUME_TASK]
    assert task.acks_late is True


def test_celery_transport_targets_events_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        celery_app, "send_task", lambda name, **kw: calls.append({"name": name, **kw})
    )
    bus.CeleryTransport().send(NAME, {"x": 1}, countdown=5)
    assert calls == [
        {"name": bus.CONSUME_TASK, "args": [NAME, {"x": 1}], "queue": "events", "countdown": 5}
    ]


async def _publish(factory: async_sessionmaker[AsyncSession]) -> uuid.UUID:
    async with factory() as s:
        env = await publish_in_tx(
            s,
            event_type=EVT,
            producer="finance",
            aggregate_schema="finance",
            aggregate_table="test_events",
            aggregate_id=uuid.uuid4(),
            payload={"budget_id": str(uuid.uuid4()), "variance_pct": 12.5},
        )
        await s.commit()
    return env.event_id


def test_tasks_end_to_end(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    """relay task → CeleryTransport.send → consume task: fail once (re-enqueue +5 s), then DONE."""
    import asyncio

    sent: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        bus.CeleryTransport, "send", lambda self, n, m, countdown=0: sent.append((n, m))
    )
    calls = {"n": 0}

    async def handler(_s: AsyncSession, _e: EventEnvelope) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")

    bus.REGISTRY.register(NAME, (EVT,), handler)
    try:
        eid = asyncio.run(_publish(factory))
        summary = worker_events.relay_outbox_events.run(honor_pause=False)
        assert summary["published"] >= 1
        (name, msg) = next(x for x in sent if x[1]["event_id"] == str(eid) and x[0] == NAME)

        requeued: list[dict[str, Any]] = []
        monkeypatch.setattr(
            worker_events.consume_event, "apply_async", lambda **kw: requeued.append(kw)
        )
        assert worker_events.consume_event.run(name, msg) == Outcome.RETRY.value
        assert requeued == [{"args": [name, msg, 2], "countdown": 5, "queue": "events"}]
        assert worker_events.consume_event.run(name, msg, 2) == Outcome.DONE.value
        assert worker_events.consume_event.run(name, msg, 1) == Outcome.DUPLICATE.value
    finally:
        bus.REGISTRY.handlers.pop(NAME)
        bus.REGISTRY.routes[EVT].remove(NAME)

    async def _check() -> tuple[str, list[str]]:
        async with factory() as s:
            st = (await s.execute(select(OUTBOX.c.status).where(OUTBOX.c.id == eid))).scalar_one()
            rows = (
                await s.execute(select(PROCESSED.c.status).where(PROCESSED.c.event_id == eid))
            ).scalars()
            return st, list(rows)

    assert asyncio.run(_check()) == ("PUBLISHED", ["DONE"])

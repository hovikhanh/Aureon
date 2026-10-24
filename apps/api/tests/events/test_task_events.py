"""TC-M13-04 (T-621, 10 §9.2, R-DEC-47) — task events through the outbox, same tx.

`task_created` / `task_completed` (extension registry), `task_overdue.days_late`, beat 08:30
Asia/Ho_Chi_Minh, consumer `platform.on_execution_event` routing + dedupe on `event_id`.
"""

import uuid
from datetime import date
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.events.bus import REGISTRY, ConsumerRegistry
from app.core.events.consumer import Outcome, consume
from app.core.events.envelope import OUTBOX, PROCESSED
from app.core.events.outbox import publish_in_tx
from app.core.events.registry import EXTENSION_EVENT_TYPES, is_registered
from app.core.events.relay import relay_once
from app.modules.execution.services.task_service import detect_overdue_tasks
from app.modules.platform.events import consumers as platform_consumers
from app.worker import celery_app
from tests.conftest import ApiClient
from tests.events.conftest import InMemoryTransport
from tests.integration.execution.helpers import make_task, outbox_for, patch

pytestmark = pytest.mark.integration

NEW = ("execution.task_created", "execution.task_completed")


def test_registry_affects_and_beat() -> None:
    assert set(NEW) <= EXTENSION_EVENT_TYPES and all(is_registered(e) for e in NEW)
    for e in (*NEW, "execution.task_overdue"):
        assert platform_consumers.AFFECTS[e] == {"execution"}
        assert "platform.on_execution_event" in REGISTRY.consumers_for(e)
    beat = celery_app.conf.beat_schedule["detect-overdue-tasks"]["schedule"]
    assert (beat.minute, beat.hour) == ({30}, {8})
    assert celery_app.conf.timezone == "Asia/Ho_Chi_Minh"


def _types(rows: list[tuple[str, dict[str, Any]]]) -> list[str]:
    return [t for t, _ in rows]


async def test_created_and_completed_in_tx(api: ApiClient, db_session: AsyncSession) -> None:
    dept = uuid.uuid4()
    t = await make_task(api, department_id=str(dept), due_date="2099-01-01",
                        assignee_id=str(uuid.uuid4()), title="Bí mật")  # fmt: skip
    rows = await outbox_for(db_session, t["id"])
    assert _types(rows) == ["execution.task_created"]
    payload = rows[0][1]
    assert payload == {
        "task_id": t["id"], "assignee_id": t["assignee_id"], "department_id": str(dept),
        "project_id": None, "due_date": "2099-01-01", "parent_task_id": None,
        "task_source": "manual", "source_ref_kind": None,
    }  # fmt: skip
    assert "title" not in payload and "Bí mật" not in str(payload)

    assert (await patch(api, f"/work/tasks/{t['id']}", 1, title="x")).status_code == 200
    assert (await patch(api, f"/work/tasks/{t['id']}", 2, status="done")).status_code == 200
    rows = await outbox_for(db_session, t["id"])
    assert sorted(_types(rows)) == ["execution.task_completed", "execution.task_created"]
    done = next(p for e, p in rows if e == "execution.task_completed")
    assert done["on_time"] is True and done["done_at"]
    # reopen → no event; re-done → a second completed event
    assert (await patch(api, f"/work/tasks/{t['id']}", 3, status="in_progress")).status_code == 200
    assert len(await outbox_for(db_session, t["id"])) == 2
    assert (await patch(api, f"/work/tasks/{t['id']}", 4, status="done")).status_code == 200
    assert _types(await outbox_for(db_session, t["id"])).count("execution.task_completed") == 2

    late = await make_task(api, due_date="2020-01-01")
    await patch(api, f"/work/tasks/{late['id']}", 1, status="done")
    p = next(p for e, p in await outbox_for(db_session, late["id"])
             if e == "execution.task_completed")  # fmt: skip
    assert p["on_time"] is False


async def test_rollback_leaves_no_event(api: ApiClient, db_session: AsyncSession) -> None:
    q = (
        select(func.count())
        .select_from(OUTBOX)
        .where(OUTBOX.c.event_type == "execution.task_created")
    )
    parent = await make_task(api)
    child = await make_task(api, parent_task_id=parent["id"])
    before = (await db_session.execute(q)).scalar_one()
    # R-DEC-42: a sub-task cannot be a parent → 422 after the row was flushed → no event left
    bad = await api.call("POST", "/work/tasks", "CEO",
                         json={"title": "x", "parent_task_id": child["id"]})  # fmt: skip
    assert bad.status_code == 422
    assert (await db_session.execute(q)).scalar_one() == before


async def test_overdue_days_late_once(api: ApiClient, db_session: AsyncSession) -> None:
    t = await make_task(api, due_date="2037-03-01", assignee_id=str(uuid.uuid4()))
    await detect_overdue_tasks(db_session, date(2037, 3, 11))
    await detect_overdue_tasks(db_session, date(2037, 3, 11))  # same day rerun
    over = [p for e, p in await outbox_for(db_session, t["id"]) if e == "execution.task_overdue"]
    assert len(over) == 1 and over[0]["days_late"] == 10


async def test_consumer_dedupe_on_event_id(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    async def fake_recompute(_s: AsyncSession, event: Any) -> None:
        calls.append(event.event_type)

    monkeypatch.setattr(platform_consumers, "recompute_for", fake_recompute)
    reg = ConsumerRegistry()
    reg.register("platform.on_execution_event", NEW,
                 REGISTRY.get("platform.on_execution_event"))  # fmt: skip
    async with factory() as s:
        env = await publish_in_tx(
            s, event_type="execution.task_created", producer="execution",
            aggregate_schema="execution", aggregate_table="test_events",
            aggregate_id=uuid.uuid4(), payload={"task_id": str(uuid.uuid4())},
        )  # fmt: skip
        await s.commit()
    t = InMemoryTransport()
    async with factory() as s:
        await relay_once(s, t, registry=reg, honor_pause=False)
        await s.commit()
    (_, msg, _) = next(x for x in t.sent if x[1]["event_id"] == str(env.event_id))
    first = await consume(factory, "platform.on_execution_event", msg, registry=reg)
    again = await consume(factory, "platform.on_execution_event", msg, registry=reg)
    assert (first.outcome, again.outcome) == (Outcome.DONE, Outcome.DUPLICATE)
    assert calls == ["execution.task_created"]
    async with factory() as s:
        rows = await s.execute(select(PROCESSED).where(PROCESSED.c.event_id == env.event_id))
        assert len(rows.all()) == 1

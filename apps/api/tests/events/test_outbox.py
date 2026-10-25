"""TC-EVT-001 / TC-EVT-004 — `publish_in_tx` writes in the caller's tx; envelope per 10 §8.1."""

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.events.envelope import OUTBOX, PROCESSED, EventEnvelope
from app.core.events.outbox import EventContractError, publish_in_tx
from app.core.events.registry import EVENT_TYPES, EXTENSION_EVENT_TYPES, is_registered
from app.modules.platform.models import OutboxEvent, ProcessedEvent

pytestmark = pytest.mark.integration

EVT = "finance.invoice_paid"


async def _publish(s: AsyncSession, **kw: object) -> EventEnvelope:
    args: dict[str, object] = {
        "event_type": EVT,
        "producer": "finance",
        "aggregate_schema": "finance",
        "aggregate_table": "test_events",
        "aggregate_id": uuid.uuid4(),
        "payload": {"invoice_id": str(uuid.uuid4()), "amount_paid": 27_500_000, "currency": "VND"},
    }
    args.update(kw)
    return await publish_in_tx(s, **args)  # type: ignore[arg-type]


async def _count(s: AsyncSession, event_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(OUTBOX).where(OUTBOX.c.id == event_id)
    return int((await s.execute(stmt)).scalar_one())


def test_registry_has_28_events() -> None:
    assert len(EVENT_TYPES) == 28
    assert all("." in e and not e.startswith("EVT-") for e in EVENT_TYPES)
    # M1.2 (R-DEC-35): extension set lives beside the 28 base types, never inside them.
    assert EXTENSION_EVENT_TYPES == {
        "hr.org_structure_changed", "auth.user_access_changed",
        "execution.task_created", "execution.task_completed",  # M1.3 R-DEC-47
        "execution.kpi_below_threshold", "execution.okr_checked_in",  # M1.4 R-DEC-56
        "execution.okr_at_risk",
        "ai.policy_changed", "platform.onboarding_completed",  # M1.6 R-DEC-77
    }  # fmt: skip
    assert not EVENT_TYPES & EXTENSION_EVENT_TYPES
    assert all(is_registered(e) for e in EXTENSION_EVENT_TYPES)


def test_core_tables_match_orm() -> None:
    """`core.events` describes the tables without importing modules — must not drift."""
    assert set(OUTBOX.c.keys()) <= set(OutboxEvent.__table__.c.keys())
    assert set(PROCESSED.c.keys()) <= set(ProcessedEvent.__table__.c.keys())
    assert OUTBOX.schema == OutboxEvent.__table__.schema == "platform"


async def test_commit_persists_pending_row(factory: async_sessionmaker[AsyncSession]) -> None:
    async with factory() as s:
        env = await _publish(s)
        await s.commit()
    async with factory() as s:
        row = (await s.execute(select(OUTBOX).where(OUTBOX.c.id == env.event_id))).one()
    assert row.status == "PENDING"
    assert row.published_at is None
    assert row.attempts == 0
    assert row.event_type == EVT
    assert row.payload["amount_paid"] == 27_500_000


async def test_rollback_drops_event(factory: async_sessionmaker[AsyncSession]) -> None:
    async with factory() as s:
        env = await _publish(s)
        assert await _count(s, env.event_id) == 1  # visible inside the tx
        await s.rollback()
    async with factory() as s:
        assert await _count(s, env.event_id) == 0


async def test_envelope_shape(factory: async_sessionmaker[AsyncSession]) -> None:
    async with factory() as s:
        env = await _publish(s)
        await s.rollback()
    msg = env.to_message()
    assert set(msg) == {
        "event_id", "event_type", "occurred_at", "version", "correlation_id", "tenant_id",
        "producer", "payload",
    }  # fmt: skip
    assert msg["tenant_id"] == str(DEFAULT_TENANT_ID)  # R-DEC-21, 10 §9.1
    assert msg["version"] == 1
    assert msg["occurred_at"].endswith("Z") or msg["occurred_at"].endswith("+00:00")
    assert EventEnvelope.model_validate(msg) == env


async def test_unknown_event_type_rejected(factory: async_sessionmaker[AsyncSession]) -> None:
    async with factory() as s:
        with pytest.raises(EventContractError, match="registry"):
            await _publish(s, event_type="finance.made_up")


@pytest.mark.parametrize(
    "payload",
    [
        {"employee_id": "x", "salary": 1},
        {"items": [{"id": 1, "bank_account": "123"}]},
        {"meta": {"date_of_birth": "1990-01-01"}},
    ],
)
async def test_pii_payload_rejected(
    factory: async_sessionmaker[AsyncSession], payload: dict[str, object]
) -> None:
    async with factory() as s:
        with pytest.raises(EventContractError, match="PII"):
            await _publish(s, payload=payload)

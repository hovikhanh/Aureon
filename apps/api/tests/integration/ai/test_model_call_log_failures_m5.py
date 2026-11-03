"""TC-M5-05/06 (R-DEC-154) — a failed model call stays on SCR-65 even when its turn rolls back.

Before M5 every `ai.model_call_logs` row was written in the request transaction; a turn whose
provider chain failed (OmniRoute down → `AI_PROVIDER_ERROR`) rolled back and took the row with it,
so the AI Control Center never showed the outage. A failed attempt is now committed on its own
(without `message_id`, which belongs to the rolled-back turn); a successful call still lives and
dies with its turn and keeps the link to its message.
"""

import uuid
from typing import Any

import pytest
from sqlalchemy import delete, select

from app.core.db import get_sessionmaker
from app.core.model_gateway import CallRecord
from app.modules.ai.models import ModelCallLog
from app.modules.ai.services.ai_service import ModelCallLogWriter

pytestmark = pytest.mark.integration


def _rec(status: str, request_id: str, **kw: Any) -> CallRecord:
    return CallRecord(
        caller_module="ai", task_kind="chat", provider="omniroute", model="m-test",
        status=status, tokens_in=kw.pop("tokens_in", 0), tokens_out=0,
        estimated_cost_micro_usd=0, latency_ms=kw.pop("latency_ms", 15), prompt_sha256="0" * 64,
        classification="INTERNAL", route_reason="internal: cloud chain", request_id=request_id,
        **kw,
    )  # fmt: skip


async def _rows(request_id: str) -> list[ModelCallLog]:
    async with get_sessionmaker()() as s:
        q = select(ModelCallLog).where(ModelCallLog.request_id == uuid.UUID(request_id))
        return list((await s.execute(q)).scalars())


async def _cleanup(request_id: str) -> None:
    async with get_sessionmaker()() as s:
        await s.execute(
            delete(ModelCallLog).where(ModelCallLog.request_id == uuid.UUID(request_id))
        )
        await s.commit()


async def test_failed_call_survives_the_turn_rollback(db_session: Any) -> None:
    rid = str(uuid.uuid4())
    try:
        writer = ModelCallLogWriter(db_session)
        timeout = _rec(
            "timeout", rid, error_code="AI_PROVIDER_TIMEOUT", latency_ms=90_000,
            message_id=uuid.uuid4(),
        )  # fmt: skip
        await writer.record(timeout)
        await writer.record(_rec("error", rid, error_code="AI_PROVIDER_ERROR"))
        await db_session.rollback()  # the turn fails → its transaction is gone

        rows = await _rows(rid)
        assert sorted(r.status for r in rows) == ["error", "timeout"]
        assert all(r.message_id is None for r in rows)  # FK target belonged to the dead turn
        assert {r.error_code for r in rows} == {"AI_PROVIDER_TIMEOUT", "AI_PROVIDER_ERROR"}
        assert next(r for r in rows if r.status == "timeout").latency_ms == 90_000
    finally:
        await _cleanup(rid)


async def test_successful_call_stays_in_the_turn_transaction(db_session: Any) -> None:
    rid = str(uuid.uuid4())
    try:
        writer = ModelCallLogWriter(db_session)
        await writer.record(_rec("ok", rid, tokens_in=120))
        await db_session.flush()
        in_tx = (
            (
                await db_session.execute(
                    select(ModelCallLog).where(ModelCallLog.request_id == uuid.UUID(rid))
                )
            )
            .scalars()
            .all()
        )
        assert [r.tokens_in for r in in_tx] == [120]
        assert await _rows(rid) == []  # not visible outside the turn until it commits
    finally:
        await _cleanup(rid)


async def test_a_broken_log_write_never_masks_the_provider_error(db_session: Any) -> None:
    class Boom:
        def __call__(self) -> Any:
            raise RuntimeError("db down")

    writer = ModelCallLogWriter(db_session, independent=Boom())
    await writer.record(_rec("error", str(uuid.uuid4())))  # must not raise

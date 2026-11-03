"""TC-M5-07 (R-DEC-155) — EP-AI-15 tells "unknown cost" apart from "free".

With `MODEL_PRICING_JSON={}` every cloud call is stored at $0, and SCR-65 showed `$0.0000` as if
the AI were free. `unpriced_calls` counts the calls that used tokens on a cloud provider but
carry no price; a local (Ollama) call at $0 is genuinely free and a call without tokens (a
failed attempt) has nothing to price.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.core.base_model import DEFAULT_TENANT_ID
from app.modules.ai.models import ModelCallLog
from app.modules.ai.services.cost_service import CostService

pytestmark = pytest.mark.integration


AT = datetime(2031, 1, 15, 3, 0, tzinfo=UTC)  # a window no other row lives in


def _log(provider: str, *, tokens: int, micro: int, status: str = "ok") -> ModelCallLog:
    return ModelCallLog(
        caller_module="ai", task_kind="chat", provider=provider, model=f"{provider}-m",
        tokens_in=tokens, tokens_out=tokens // 10, estimated_cost_micro_usd=micro,
        latency_ms=100, status=status, prompt_sha256="0" * 64, tenant_id=DEFAULT_TENANT_ID,
        request_id=uuid.uuid4(), created_at=AT,
    )  # fmt: skip


async def test_unpriced_calls_counts_only_cloud_calls_with_tokens_at_zero_cost(
    db_session: Any,
) -> None:
    db_session.add_all([
        _log("omniroute", tokens=1000, micro=0),                 # unpriced
        _log("omniroute", tokens=800, micro=0),                  # unpriced
        _log("omniroute", tokens=500, micro=1_250),              # priced
        _log("omniroute", tokens=0, micro=0, status="timeout"),  # nothing to price
        _log("ollama", tokens=1400, micro=0),                    # local → free, not unpriced
    ])  # fmt: skip
    await db_session.flush()

    window = {"start": AT - timedelta(minutes=1), "end": AT + timedelta(minutes=1)}
    svc = CostService(db_session)
    rows = {r.key: r for r in (await svc.usage(group_by="provider", **window)).rows}

    assert (rows["omniroute"].calls, rows["omniroute"].unpriced_calls) == (4, 2)
    assert (rows["ollama"].calls, rows["ollama"].unpriced_calls) == (1, 0)
    by_model = {r.key: r for r in (await svc.usage(group_by="model", **window)).rows}
    assert by_model["omniroute-m"].unpriced_calls == 2
    assert by_model["omniroute-m"].cost_usd == pytest.approx(0.00125)

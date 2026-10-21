"""TC-AI-003 (integration, T-013) — gateway → `ai.model_call_logs` via `AiService`."""

import json
import uuid
from pathlib import Path

import httpx
import pytest
import respx
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ConfigService
from app.core.errors import AIError
from app.core.model_gateway import ChatRequest, Message, SecretDataBlockedError
from app.core.model_gateway.gateway import CircuitBreaker
from app.modules.ai.models import ModelCallLog
from app.modules.ai.services import ai_service

pytestmark = pytest.mark.integration


def _cfg(**kw: object) -> ConfigService:
    return ConfigService(
        model_gateway_mode="live",
        model_provider_primary="openai",
        model_provider_fallbacks="",
        openai_api_key=SecretStr("k"),
        openai_base_url="https://openai.test/v1",
        model_pricing_json=json.dumps({"openai:auto/coding": {"in": 2, "out": 8}}),
        **kw,  # type: ignore[arg-type]
    )


async def _no_sleep(_: float) -> None:
    return None


def _req(classification: str = "INTERNAL") -> ChatRequest:
    return ChatRequest(
        task="chat",
        messages=(Message("user", f"Doanh thu? {uuid.uuid4()}"),),
        caller_module="ai_core",
        classification=classification,  # type: ignore[arg-type]
        user_id=uuid.uuid4(),
    )


@respx.mock
async def test_call_is_logged_with_hash_not_prompt(db_session: AsyncSession) -> None:
    respx.post("https://openai.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "auto/coding",
                "choices": [{"message": {"content": "27,5 tỷ"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10},
            },
        )
    )
    svc = ai_service.AiService(db_session)
    r = _req()
    g = svc.gateway(cfg=_cfg(), breaker=CircuitBreaker(), sleep=_no_sleep)
    await g.chat(r)
    row = (
        await db_session.execute(
            select(ModelCallLog).where(ModelCallLog.prompt_sha256 == r.prompt_sha256())
        )
    ).scalar_one()
    assert (row.provider, row.model, row.status, row.task_kind) == (
        "openai", "auto/coding", "ok", "chat"
    )  # fmt: skip
    assert (row.tokens_in, row.tokens_out, row.estimated_cost_micro_usd) == (100, 10, 280)
    assert row.user_id == r.user_id
    assert row.latency_ms >= 0
    assert "Doanh thu" not in json.dumps([str(v) for v in row.__dict__.values()])
    writer = ai_service.ModelCallLogWriter(db_session)
    assert await writer.month_spend_micro_usd() >= 280


async def test_secret_block_is_logged(db_session: AsyncSession) -> None:
    g = ai_service.AiService(db_session).gateway(cfg=_cfg(), breaker=CircuitBreaker())
    r = _req("SECRET")
    with pytest.raises(SecretDataBlockedError):
        await g.chat(r)
    row = (
        await db_session.execute(
            select(ModelCallLog).where(ModelCallLog.prompt_sha256 == r.prompt_sha256())
        )
    ).scalar_one()
    assert (row.provider, row.status, row.error_code) == (
        "none",
        "forbidden",
        "CLASSIFICATION_SECRET",
    )


@respx.mock
async def test_budget_from_db_blocks(db_session: AsyncSession, tmp_path: Path) -> None:
    db_session.add(
        ModelCallLog(
            caller_module="ai_core", task_kind="chat", provider="openai", model="m",
            tokens_in=0, tokens_out=0, estimated_cost_micro_usd=1_000_000_000, latency_ms=1,
            status="ok",
        )
    )  # fmt: skip
    await db_session.flush()
    any_http = respx.route()
    g = ai_service.AiService(db_session).gateway(
        cfg=_cfg(ai_monthly_budget_usd=1), breaker=CircuitBreaker()
    )
    with pytest.raises(AIError) as exc:
        await g.chat(_req())
    assert exc.value.code == "AI_QUOTA_EXCEEDED"
    assert any_http.call_count == 0

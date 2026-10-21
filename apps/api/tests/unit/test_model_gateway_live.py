"""TC-AI-001 live (T-013 exit criterion "≥ 1 provider live") — opt-in only.

`RUN_LIVE_TESTS=true uv run pytest -m live apps/api/tests/unit/test_model_gateway_live.py`
Uses the real `.env` chain (OmniRoute primary) and the compose Ollama for CONFIDENTIAL.
Each provider not configured / unreachable is reported as a failure — never skipped.
"""

import os

import pytest

from app.core.config import ConfigService
from app.core.model_gateway import ChatRequest, Message, ModelGateway, NullSink

pytestmark = [pytest.mark.live]


def _cfg() -> ConfigService:
    assert os.environ.get("RUN_LIVE_TESTS") == "true", "live tests need RUN_LIVE_TESTS=true"
    return ConfigService(model_gateway_mode="live")


@pytest.mark.parametrize("classification", ["INTERNAL", "CONFIDENTIAL"])
async def test_live_chat_roundtrip(classification: str) -> None:
    sink = NullSink()
    resp = await ModelGateway(sink, cfg=_cfg()).chat(
        ChatRequest(
            task="chat",
            messages=(Message("user", "Trả lời đúng một từ: OK"),),
            caller_module="ai_core",
            classification=classification,  # type: ignore[arg-type]
            max_output_tokens=16,
        )
    )
    assert resp.content.strip()
    assert sink.records[-1].status == "ok"
    if classification == "CONFIDENTIAL":
        assert resp.provider == "ollama"

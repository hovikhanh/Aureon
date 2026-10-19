"""Live smoke against local OmniRoute (T-006).

Opt-in only: excluded from the default suite (``-m 'not live'`` in pyproject) and additionally
guarded by ``RUN_LIVE_TESTS=true`` so a stray ``-m live`` run skips cleanly instead of failing
with a 403/connection error when OmniRoute is unreachable or unauthorized. Run it with:

    RUN_LIVE_TESTS=true uv run pytest -m live

Uses the real key from ConfigService (never printed) and a tiny max_tokens.
"""

import os

import pytest

from app.core.config import get_config
from app.core.model_gateway import ModelGateway

RUN_LIVE = os.getenv("RUN_LIVE_TESTS", "").lower() == "true"


@pytest.mark.integration
@pytest.mark.live
@pytest.mark.skipif(not RUN_LIVE, reason="Live OmniRoute test; set RUN_LIVE_TESTS=true to run")
def test_live_json_completion_via_omniroute() -> None:
    gw = ModelGateway(
        get_config(),
        mode="live",
        routes={"classify": "agent-free-cheap"},
        fallbacks={},
        backoff_s=(1.0,),
        timeout_s=60.0,
    )
    try:
        data = gw.complete_json(
            "classify",
            [
                {
                    "role": "user",
                    "content": 'Reply with exactly this JSON and nothing else: {"ok": true}',
                }
            ],
            max_tokens=200,
        )
    finally:
        gw.close()
    assert data == {"ok": True}
    assert gw.records[-1].outcome == "ok"

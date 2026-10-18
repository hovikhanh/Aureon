"""Live smoke against local OmniRoute (T-006). Integration: FAILS (never skips) if unreachable.

Uses the real key from ConfigService (never printed) and a tiny max_tokens.
"""

import pytest

from app.core.config import get_config
from app.core.model_gateway import ModelGateway


@pytest.mark.integration
@pytest.mark.live
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

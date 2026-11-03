"""TC-M5-09 — the SSE chat ends with the `error` event (10 §6) when the provider chain fails.

The UI streams `/ai/chat/stream`. With OmniRoute down every turn raised `AI_PROVIDER_ERROR`
*after* the `200` and headers were sent; the generator re-raised it, Starlette logged
"Caught handled exception, but response already started" and the browser saw a dropped stream
instead of the reason. The stream now closes with `start` + `error {code}` like `AI_DISABLED` does.
"""

import json
import uuid
from typing import Any

import pytest

from app.core.errors import ai_error
from app.core.model_gateway.types import ChatRequest, ChatResponse
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration


def _down(app: Any, code: str) -> None:
    from app.modules.ai.routes.router import get_chat_gateway

    class _Down:
        async def chat(self, req: ChatRequest) -> ChatResponse:
            raise ai_error(code, "no provider could answer")

    app.dependency_overrides[get_chat_gateway] = lambda: _Down()


def _events(text: str) -> list[tuple[str, dict[str, Any]]]:
    out = []
    for block in (b for b in text.split("\n\n") if b.strip()):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        out.append((lines["event"], json.loads(lines["data"])))
    return out


@pytest.mark.parametrize("code", ["AI_PROVIDER_ERROR", "AI_PROVIDER_TIMEOUT", "AI_QUOTA_EXCEEDED"])
async def test_provider_failure_closes_the_stream_with_an_error_event(
    api: ApiClient, db_session: Any, code: str
) -> None:
    _down(api.app, code)
    h = api.headers("CEO", user_id=uuid.uuid4(), idem=True)
    r = await api.http.post(
        "/api/v1/ai/chat/stream", headers=h, json={"message": "Tạo task kiểm thử"}
    )

    assert r.status_code == 200
    events = _events(r.text)
    assert [e for e, _ in events] == ["start", "error"]
    assert events[1][1]["code"] == code

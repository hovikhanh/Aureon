"""T-509 / DEC-241 — demo replay: recorded intents answer without an LLM, grounded in live tools.

Runs over the real HTTP app (SSE EP-111) against the seeded dev DB inside the rolled-back
session. The gateway is replaced by one that fails the test if called — replay must not touch a
model. Each recorded question must stream `start → tool_call → token… → done` in < 2 s with
citation `[1]` bound to a `metric_value` source; unmatched questions go to the model.
"""

import json
import time
import uuid

import pytest

from app.core.config import get_config
from app.core.deps import Principal
from app.core.model_gateway.types import ChatRequest, ChatResponse
from app.modules.ai.routes.router import get_chat_gateway
from app.modules.ai.services.chat_service import ChatService
from app.modules.ai.services.demo_replay import load_entries, match_entry, normalise
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

pytestmark = pytest.mark.integration

QUERIES = [
    ("Doanh thu Q3?", "revenue_q3"),
    ("Cash flow tháng này?", "cash_flow"),
    ("Top 5 khách hàng?", "top_clients"),
    ("Rủi ro nghiêm trọng nhất?", "top_risk"),
    ("Pipeline coverage?", "pipeline"),
]


class _NoModel:
    calls = 0

    async def chat(self, req: ChatRequest) -> ChatResponse:
        _NoModel.calls += 1
        return ChatResponse(content="live answer", provider="fixture", model="x")


@pytest.fixture
def demo_on(monkeypatch: pytest.MonkeyPatch, api):
    cfg = get_config()
    monkeypatch.setattr(cfg, "ai_demo_replay", True)
    monkeypatch.setattr(cfg, "ai_demo_token_delay_sec", 0.0)
    _NoModel.calls = 0
    api.app.dependency_overrides[get_chat_gateway] = lambda: _NoModel()
    yield cfg
    api.app.dependency_overrides.pop(get_chat_gateway, None)


def _ceo() -> Principal:
    return Principal(
        user_id=uuid.uuid4(), role="CEO", permissions=frozenset(ROLE_PERMISSIONS["CEO"])
    )


def _events(body: str) -> list[tuple[str, dict]]:
    out = []
    for block in body.strip().split("\n\n"):
        lines = dict(ln.split(": ", 1) for ln in block.splitlines() if ": " in ln)
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_all_ten_entries_load_and_match_themselves() -> None:
    entries = load_entries()
    assert len(entries) == 10
    assert normalise("Rủi ro ĐỎ?") == "rui ro do"
    assert match_entry("Dự báo Q4?").id == "forecast_q4"  # type: ignore[union-attr]
    assert match_entry("Tại sao O pillar yellow?").id == "why_o_yellow"  # type: ignore[union-attr]
    assert match_entry("So sánh F vs S?").id == "compare_f_s"  # type: ignore[union-attr]
    assert match_entry("AI đã làm gì hôm nay?").id == "ai_today"  # type: ignore[union-attr]
    assert match_entry("Turnover rate?").id == "turnover"  # type: ignore[union-attr]
    assert match_entry("Thời tiết hôm nay thế nào?") is None


@pytest.mark.parametrize(("question", "entry_id"), QUERIES)
async def test_recorded_query_streams_fast_with_citation(api, demo_on, question, entry_id) -> None:
    started = time.monotonic()
    r = await api.call(
        "POST", "/ai/chat/stream", role="CEO",
        headers=api.headers("CEO", idem=True), json={"message": question},
    )  # fmt: skip
    elapsed = time.monotonic() - started
    assert r.status_code == 200, r.text
    assert elapsed < 2.0
    events = _events(r.text)
    kinds = [e for e, _ in events]
    assert kinds[0] == "start" and kinds[-1] == "done"
    assert "tool_call" in kinds and kinds.count("token") > 3
    done = events[-1][1]
    assert "[1]" in done["answer"]
    assert done["sources"][0]["type"] == "metric_value"
    assert done["sources"][0]["id"].startswith("METRIC-")
    assert "ai.warn.demo_replay" in done["warnings"]
    assert "".join(d["delta"] for e, d in events if e == "token") == done["answer"]
    assert _NoModel.calls == 0


async def test_numbers_come_from_tools(db_session, demo_on) -> None:
    ceo = _ceo()
    turn = await ChatService(db_session, _NoModel()).chat(ceo, "Doanh thu Q3?")
    assert turn.replayed == "revenue_q3"
    first = turn.sources[0]
    assert first.id == "METRIC-FIN-01"
    assert f"{first.value:.1f}".rstrip("0").rstrip(".").replace(".", ",") in turn.answer


async def test_unmatched_or_disabled_uses_model(db_session, demo_on, monkeypatch) -> None:
    ceo = _ceo()
    turn = await ChatService(db_session, _NoModel()).chat(ceo, "Viết email chúc mừng sinh nhật")
    assert turn.replayed is None and turn.answer == "live answer"
    monkeypatch.setattr(demo_on, "ai_demo_replay", False)
    turn = await ChatService(db_session, _NoModel()).chat(ceo, "Doanh thu Q3?")
    assert turn.replayed is None and _NoModel.calls == 2


async def test_no_permission_no_replay(db_session, demo_on) -> None:
    """HR manager lacks finance tools → replay declines → model path (P06)."""
    hr = Principal(
        user_id=uuid.uuid4(), role="DIR",
        permissions=frozenset(ROLE_PERMISSIONS["DIR"]),
        scope_pillars=frozenset({"O"}),
    )  # fmt: skip
    turn = await ChatService(db_session, _NoModel()).chat(hr, "Doanh thu Q3?")
    assert turn.replayed is None

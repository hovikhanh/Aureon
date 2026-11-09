"""D-19 — chat on a CPU-only local model: intent routing, prefetch, live grounded streaming.

TC-D19-01 routing narrows the advertised tools within the asker's permitted set (P06 first).
TC-D19-02 the obvious READ tool runs before the first model round, as the asker, logged.
TC-D19-03 a write intent never prefetches; no match → full permitted catalog.
TC-D19-04 `on_event`: `start` first, tools as they run, grounded `token` deltas — an ungrounded
          number is never sent, and the streamed text equals the stored answer.
TC-D19-05 every grounded number is linked to its source by the server (`[n]`).
"""

import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import select

from app.core.deps import Principal
from app.core.model_gateway.types import ChatChunk, ChatRequest, ChatResponse, Usage
from app.modules.ai.models import ToolCallLog
from app.modules.ai.services.chat_service import ChatService
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

pytestmark = pytest.mark.integration
INTENT_ROUTING = True  # opt out of the legacy full-catalog pin (conftest)


def principal(role: str, pillars: frozenset[str] = frozenset()) -> Principal:
    return Principal(
        user_id=uuid.uuid4(), role=role, scope_pillars=pillars,
        permissions=frozenset(ROLE_PERMISSIONS[role]), email=f"{role.lower()}@abc.test",
    )  # fmt: skip


class StreamingGateway:
    """Answers with `text`, streamed in small pieces; records every request."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.requests: list[ChatRequest] = []

    async def chat(self, req: ChatRequest) -> ChatResponse:
        self.requests.append(req)
        return ChatResponse(content=self.text, provider="fixture", model="x", usage=Usage(5, 9))

    async def stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        self.requests.append(req)
        for i in range(0, len(self.text), 7):
            yield ChatChunk(delta=self.text[i : i + 7], provider="ollama", model="m")
        yield ChatChunk(done=True, usage=Usage(5, 9), provider="ollama", model="m")


def _metric(turn: Any, code: str) -> float:
    return next(s.value for s in turn.sources if s.id == code)


async def test_revenue_question_prefetches_finance_card_and_narrows_tools(db_session) -> None:
    gw = StreamingGateway("Đã có số liệu.")
    turn = await ChatService(db_session, gw).chat(
        principal("CEO"), "Doanh thu quý này so với mục tiêu thế nào?", locale="vi"
    )
    sent = [t.name for t in gw.requests[0].tools]
    # finance is served by the prefetched card; only the goals intent ("mục tiêu") keeps tools
    assert set(sent) <= {"TOOL-get_okr_status", "TOOL-get_kpi_status"}
    # the dashboard ran before the first model round, as a tool call the model can read
    roles = [m.role for m in gw.requests[0].messages]
    assert roles[-2:] == ["assistant", "tool"]
    assert gw.requests[0].messages[-2].tool_calls[0].name == "TOOL-get_finance_dashboard"
    assert "<<<DATA" in gw.requests[0].messages[-1].content
    assert len(gw.requests) == 1  # one model round
    assert turn.function_calls[0] == {
        **turn.function_calls[0],
        "tool": "TOOL-get_finance_dashboard",
        "status": "ok",
    }
    logged = (await db_session.execute(select(ToolCallLog.tool_name).where(
        ToolCallLog.message_id == gw.requests[0].message_id))).scalars().all()  # fmt: skip
    assert "TOOL-get_finance_dashboard" in logged


async def test_routing_never_widens_permissions(db_session) -> None:
    gw = StreamingGateway("Chưa có dữ liệu.")
    emp = principal("EMP")
    await ChatService(db_session, gw).chat(emp, "Doanh thu quý này?", locale="vi")
    sent = {t.name for t in gw.requests[0].tools}
    assert "TOOL-get_finance_dashboard" not in sent
    assert all(m.role != "tool" for m in gw.requests[0].messages)  # nothing prefetched


async def test_write_intent_does_not_prefetch_and_no_match_keeps_catalog(db_session) -> None:
    gw = StreamingGateway("ok")
    await ChatService(db_session, gw).chat(
        principal("CEO"), "Giao việc cho NV-0001 gọi lại khách hàng", locale="vi"
    )
    sent = {t.name for t in gw.requests[0].tools}
    assert "TOOL-create_task" in sent and "TOOL-get_finance_dashboard" not in sent
    assert all(m.role != "tool" for m in gw.requests[0].messages)
    full = StreamingGateway("ok")
    await ChatService(db_session, full).chat(principal("CEO"), "Xin chào", locale="vi")
    assert len(full.requests[0].tools) > len(sent)
    assert "TOOL-get_finance_dashboard" in {t.name for t in full.requests[0].tools}


async def test_live_events_stream_grounded_text_and_cite_sources(db_session) -> None:
    events: list[tuple[str, dict[str, Any]]] = []

    async def sink(event: str, data: dict[str, Any]) -> None:
        events.append((event, data))

    probe = StreamingGateway("x")
    first = await ChatService(db_session, probe).chat(principal("CEO"), "Doanh thu?", locale="vi")
    value = _metric(first, "METRIC-FIN-01")
    shown = f"{value:.1f}".replace(".", ",")
    gw = StreamingGateway(f"Doanh thu đạt {shown}% kế hoạch. Lãi 987,6 tỷ đồng. Hết.")
    turn = await ChatService(db_session, gw).chat(
        principal("CEO"), "Doanh thu?", locale="vi", on_event=sink
    )
    names = [e for e, _ in events]
    assert names[0] == "start" and events[0][1]["message_id"] == str(turn.message_id)
    assert names[1:3] == ["tool_call", "tool_result"]
    streamed = "".join(d["delta"] for e, d in events if e == "token")
    assert streamed == turn.answer and turn.streamed
    assert "987,6" not in streamed  # removed by grounding before it was ever sent
    n = [s.id for s in turn.sources].index("METRIC-FIN-01") + 1
    assert f"{shown}% [{n}]" in turn.answer
    assert "ai.warn.ungrounded_number_removed" in turn.warnings

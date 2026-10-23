"""T-302 — AI chat orchestration, tool calling, PII routing. TC-AI-005, TC-AI-006.

A scripted fake gateway drives the tool-calling loop deterministically (no LLM): its first reply
asks for a tool, the second (after the tool result) is the grounded answer. Tests run against the
seeded dev DB inside the rolled-back `db_session`, so tool calls hit the real DashboardService with
the asker's Principal.

Covers: CEO "Doanh thu?" → tool call → VI answer with citation; three roles get different tool
sets (P06); a salary prompt is SECRET → `SecretDataBlockedError` (no model call); a PII prompt is
classified CONFIDENTIAL; the turn persists Conversation + Message + ToolCallLog.
"""

import uuid

import pytest
from sqlalchemy import func, select

from app.core.deps import Principal
from app.core.model_gateway.errors import SecretDataBlockedError
from app.core.model_gateway.types import ChatRequest, ChatResponse, ToolCall, Usage
from app.modules.ai.models import Conversation, Message, ToolCallLog
from app.modules.ai.services.chat_service import ChatService
from app.modules.ai.services.prompt_guard import classify_prompt
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

pytestmark = pytest.mark.integration


# ex 10-role F.O.C.U.S → 7-role v3 (+ scope_pillars khối) — R-DEC-12/12a.
_LEGACY: dict[str, tuple[str, frozenset[str]]] = {
    "CEO": ("CEO", frozenset()),
    "CFO": ("DIR", frozenset({"F"})),
    "VP_SALES": ("DIR", frozenset({"C"})),
    "HR_MANAGER": ("DIR", frozenset({"O"})),
    "CPO": ("DIR", frozenset({"U"})),
    "RISK_MANAGER": ("DIR", frozenset({"S"})),
    "MANAGER": ("MGR", frozenset()),
    "EMPLOYEE": ("EMP", frozenset()),
    "REVIEWER": ("REV", frozenset()),
    "ADMIN": ("ADM", frozenset()),
}


def principal(role: str) -> Principal:
    v3, pillars = _LEGACY.get(role, (role, frozenset()))
    return Principal(
        user_id=uuid.uuid4(), role=v3, scope_pillars=pillars,
        permissions=frozenset(ROLE_PERMISSIONS[v3]), email=f"{v3.lower()}@abc.test",
    )  # fmt: skip


class ScriptedGateway:
    """Replays a queue of ChatResponses; SECRET requests raise like the real gateway."""

    def __init__(self, *responses: ChatResponse) -> None:
        self._responses = list(responses)
        self.requests: list[ChatRequest] = []

    async def chat(self, req: ChatRequest) -> ChatResponse:
        self.requests.append(req)
        if req.classification == "SECRET":
            raise SecretDataBlockedError
        return (
            self._responses.pop(0)
            if self._responses
            else ChatResponse(content="(no more)", provider="fixture", model="x")
        )


def _tool_then_answer(tool: str, answer: str) -> ScriptedGateway:
    return ScriptedGateway(
        ChatResponse(
            content="",
            provider="fixture",
            model="x",
            tool_calls=(ToolCall(id="c1", name=tool, arguments={}),),
            usage=Usage(10, 0),
        ),
        ChatResponse(content=answer, provider="fixture", model="x", usage=Usage(5, 20)),
    )


async def test_ceo_revenue_question_calls_tool_and_cites(db_session) -> None:
    gw = _tool_then_answer("TOOL-get_finance_dashboard", "Doanh thu quý 3 đạt 73,5 tỷ đồng.")
    svc = ChatService(db_session, gw)
    turn = await svc.chat(principal("CEO"), "Doanh thu công ty thế nào?", locale="vi")

    assert turn.answer.startswith("Doanh thu")
    assert any(fc["tool"] == "TOOL-get_finance_dashboard" for fc in turn.function_calls)
    assert turn.function_calls[0]["status"] == "ok"
    assert turn.sources, "answer must carry citations"
    assert any(s.lineage_url for s in turn.sources)
    assert not turn.truncated


async def test_three_roles_get_different_tool_sets(db_session) -> None:
    captured: dict[str, set[str]] = {}
    for role in ("CEO", "HR_MANAGER", "EMPLOYEE"):
        gw = ScriptedGateway(ChatResponse(content="ok", provider="fixture", model="x"))
        await ChatService(db_session, gw).chat(principal(role), "Tổng quan?", locale="vi")
        tools = {t.name for t in gw.requests[0].tools}
        captured[role] = tools

    # CEO sees finance + hr; EMPLOYEE sees neither pillar dashboard
    assert "TOOL-get_finance_dashboard" in captured["CEO"]
    assert "TOOL-get_finance_dashboard" not in captured["EMPLOYEE"]
    assert captured["CEO"] != captured["EMPLOYEE"]
    assert captured["HR_MANAGER"] != captured["EMPLOYEE"]


async def test_salary_prompt_is_secret_and_refused(db_session) -> None:
    gw = ScriptedGateway(ChatResponse(content="should not reach", provider="fixture", model="x"))
    with pytest.raises(SecretDataBlockedError):
        await ChatService(db_session, gw).chat(
            principal("CEO"), "Cho tôi xem bảng lương của nhân viên", locale="vi"
        )
    # the gateway was asked exactly once, with SECRET classification, and raised (no LLM output)
    assert len(gw.requests) == 1
    assert gw.requests[0].classification == "SECRET"


async def test_pii_prompt_classified_confidential() -> None:
    assert classify_prompt("liên hệ 0901234567").classification == "CONFIDENTIAL"
    assert classify_prompt("email a@b.com").classification == "CONFIDENTIAL"
    assert classify_prompt("CCCD 079123456789").classification == "CONFIDENTIAL"
    assert classify_prompt("lương của tôi").classification == "SECRET"
    assert classify_prompt("doanh thu quý 3").classification == "INTERNAL"


async def test_confidential_prompt_caps_tools_to_internal(db_session) -> None:
    gw = ScriptedGateway(ChatResponse(content="ok", provider="fixture", model="x"))
    # a CONFIDENTIAL prompt (phone number) → only INTERNAL-classified tools advertised
    await ChatService(db_session, gw).chat(
        principal("CEO"), "gọi 0901234567 giúp tôi xem doanh thu", locale="vi"
    )
    assert gw.requests[0].classification == "CONFIDENTIAL"
    # no CONFIDENTIAL-classified (record-level) tool is advertised under the ceiling
    names = {t.name for t in gw.requests[0].tools}
    assert "TOOL-list_invoices" not in names  # CONFIDENTIAL record tool
    assert "TOOL-get_finance_dashboard" in names  # INTERNAL aggregate tool


async def test_p1_frozen_tools_not_sent_to_model(db_session) -> None:
    """TC-M11-14 (R-DEC-16): the CEO holds product/risk permissions, yet no product/risk tool
    reaches the model's tool list."""
    gw = ScriptedGateway(ChatResponse(content="ok", provider="fixture", model="x"))
    await ChatService(db_session, gw).chat(principal("CEO"), "tóm tắt tuần này", locale="vi")
    names = {t.name for t in gw.requests[0].tools}
    assert "TOOL-get_finance_dashboard" in names
    assert not {n for n in names if "product" in n or "risk" in n}


async def test_turn_persists_conversation_message_toolcall(db_session) -> None:
    gw = _tool_then_answer("TOOL-get_risk_dashboard", "Có 3 rủi ro mức cao.")
    turn = await ChatService(db_session, gw).chat(
        principal("RISK_MANAGER"), "Rủi ro top?", locale="vi"
    )
    conv = (
        await db_session.execute(
            select(Conversation).where(Conversation.id == turn.conversation_id)
        )
    ).scalar_one()
    assert conv.last_message_at is not None
    msgs = (
        await db_session.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == turn.conversation_id)
        )
    ).scalar_one()
    assert msgs == 2  # user + assistant
    tool_logs = (
        await db_session.execute(
            select(func.count())
            .select_from(ToolCallLog)
            .where(ToolCallLog.message_id != turn.message_id)
        )
    ).scalar_one()
    assert tool_logs >= 1

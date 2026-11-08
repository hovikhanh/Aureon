"""F-H8, F-H9, F-H11, F-C2, F-M1, F-M2 — what a chat turn may see, what the tools really do, and
how an answer says where it came from."""

import asyncio
import json
import uuid
from typing import Any

import pytest
from pydantic import SecretStr
from sqlalchemy import select, text, update

from app.core.config import get_config
from app.core.deps import Principal
from app.core.model_gateway.errors import TemplateRequired
from app.core.model_gateway.types import ChatRequest, ChatResponse, ToolCall
from app.modules.ai.models import AgentProfile
from app.modules.ai.routes.router import get_chat_gateway
from app.modules.ai.services import tool_executor
from app.modules.ai.services.action_service import ActionService
from app.modules.ai.services.chat_service import HISTORY_PAIRS, ChatService
from app.modules.ai.services.demo_replay import replay_enabled
from app.modules.ai.services.prompt_guard import scrub_payload
from app.modules.ai.services.tool_executor import ToolExecutor, model_ready
from app.modules.ai.tools import advertisable_for, all_tools, get_tool
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.execution.models import Decision
from app.modules.idp.services.actions import get_action

pytestmark = pytest.mark.integration


def ceo() -> Principal:
    return Principal(
        user_id=uuid.uuid4(), role="CEO", permissions=frozenset(ROLE_PERMISSIONS["CEO"]),
        email="ceo@abc.test",
    )  # fmt: skip


class Scripted:
    def __init__(self, *responses: ChatResponse) -> None:
        self.responses = list(responses)
        self.requests: list[ChatRequest] = []

    async def chat(self, req: ChatRequest) -> ChatResponse:
        self.requests.append(req)
        if self.responses:
            return self.responses.pop(0)
        return ChatResponse(content="Xong.", provider="fixture", model="x")


def _call(tool: str, args: dict | None = None) -> ChatResponse:
    call = ToolCall(id="c1", name=tool, arguments=args or {})
    return ChatResponse(content="", provider="fixture", model="x", tool_calls=(call,))


@pytest.fixture
def cfg(monkeypatch: pytest.MonkeyPatch) -> Any:
    c = get_config()
    monkeypatch.setattr(c, "model_gateway_mode", "live")
    monkeypatch.setattr(c, "model_provider_confidential", "ollama")
    monkeypatch.setattr(c, "model_provider_fallbacks", "")
    monkeypatch.setattr(c, "omniroute_api_key", SecretStr("test-key"))
    return c


def _classes(req: ChatRequest) -> set[str]:
    return {get_tool(t.name).data_classification for t in req.tools}  # type: ignore[union-attr]


# ------------------------------------------------------------------- F-H11
async def test_turn_on_a_cloud_chain_gets_no_confidential_tool(
    db_session, cfg, monkeypatch
) -> None:
    monkeypatch.setattr(cfg, "model_provider_primary", "omniroute")
    gw = Scripted()
    await ChatService(db_session, gw).chat(ceo(), "Doanh thu?", locale="vi")
    assert gw.requests[0].tools, "INTERNAL tools stay"
    assert _classes(gw.requests[0]) == {"INTERNAL"}


async def test_cloud_fallback_counts_as_a_cloud_chain(db_session, cfg, monkeypatch) -> None:
    monkeypatch.setattr(cfg, "model_provider_primary", "ollama")
    monkeypatch.setattr(cfg, "model_provider_fallbacks", "omniroute")
    gw = Scripted()
    await ChatService(db_session, gw).chat(ceo(), "Doanh thu?", locale="vi")
    assert _classes(gw.requests[0]) == {"INTERNAL"}


async def test_local_only_turn_may_use_confidential_tools(db_session, cfg, monkeypatch) -> None:
    monkeypatch.setattr(cfg, "model_provider_primary", "ollama")
    monkeypatch.setattr(cfg, "omniroute_api_key", None)
    gw = Scripted()
    await ChatService(db_session, gw).chat(ceo(), "Doanh thu?", locale="vi")
    assert "CONFIDENTIAL" in _classes(gw.requests[0])


async def test_pii_prompt_is_local_and_keeps_confidential_tools(
    db_session, cfg, monkeypatch
) -> None:
    monkeypatch.setattr(cfg, "model_provider_primary", "ollama")
    monkeypatch.setattr(cfg, "omniroute_api_key", None)
    gw = Scripted()
    await ChatService(db_session, gw).chat(ceo(), "Gọi số 0901234567 giúp tôi", locale="vi")
    assert gw.requests[0].classification == "CONFIDENTIAL"
    assert "CONFIDENTIAL" in _classes(gw.requests[0])


async def test_confidential_tool_result_raises_the_rest_of_the_turn(
    db_session, cfg, monkeypatch
) -> None:
    monkeypatch.setattr(cfg, "model_provider_primary", "ollama")
    monkeypatch.setattr(cfg, "omniroute_api_key", None)
    gw = Scripted(_call("TOOL-search_documents", {"query": "hợp đồng"}))
    await ChatService(db_session, gw).chat(ceo(), "Tìm hợp đồng", locale="vi")
    assert gw.requests[0].classification == "INTERNAL"
    assert gw.requests[1].classification == "CONFIDENTIAL"


# ------------------------------------------------------------------- F-M1 memory
async def test_history_reaches_the_model_in_order(db_session) -> None:
    user = ceo()
    svc = ChatService(db_session, Scripted())
    first = await svc.chat(user, "Câu hỏi thứ nhất", locale="vi")
    gw = Scripted()
    await ChatService(db_session, gw).chat(
        user, "Câu hỏi thứ hai", conversation_id=first.conversation_id, locale="vi"
    )
    roles = [(m.role, m.content) for m in gw.requests[0].messages]
    assert roles[1:] == [("user", "Câu hỏi thứ nhất"), ("assistant", "Xong."),
                         ("user", "Câu hỏi thứ hai")]  # fmt: skip


async def test_history_is_bounded(db_session) -> None:
    user = ceo()
    conv = None
    for i in range(HISTORY_PAIRS + 2):
        turn = await ChatService(db_session, Scripted()).chat(
            user, f"q{i}", conversation_id=conv, locale="vi"
        )
        conv = turn.conversation_id
    gw = Scripted()
    await ChatService(db_session, gw).chat(user, "cuối", conversation_id=conv, locale="vi")
    assert len(gw.requests[0].messages) == 1 + HISTORY_PAIRS * 2 + 1


async def test_pii_in_history_keeps_the_turn_local_and_is_scrubbed(db_session) -> None:
    user = ceo()
    first = await ChatService(db_session, Scripted()).chat(user, "CCCD 012345678901", locale="vi")
    gw = Scripted()
    await ChatService(db_session, gw).chat(
        user, "Tiếp tục", conversation_id=first.conversation_id, locale="vi"
    )
    assert gw.requests[0].classification == "CONFIDENTIAL"
    assert "012345678901" not in " ".join(m.content for m in gw.requests[0].messages)


async def test_answer_built_on_a_confidential_tool_stays_local(db_session) -> None:
    user = ceo()
    gw1 = Scripted(_call("TOOL-search_documents", {"query": "hợp đồng"}),
                   ChatResponse(content="Không thấy.", provider="fixture", model="x"))  # fmt: skip
    first = await ChatService(db_session, gw1).chat(user, "Tìm hợp đồng", locale="vi")
    gw = Scripted()
    await ChatService(db_session, gw).chat(
        user, "Rồi sao", conversation_id=first.conversation_id, locale="vi"
    )
    assert gw.requests[0].classification == "CONFIDENTIAL"


# ------------------------------------------------------------------- F-H9 tool budget
async def test_tool_over_budget_is_a_timeout_and_the_session_survives(
    db_session, monkeypatch
) -> None:
    monkeypatch.setattr(tool_executor, "TOOL_TIMEOUT_S", 0.2)
    ex = ToolExecutor(db_session, ceo())
    keep = await ChatService(db_session, Scripted()).chat(ceo(), "Trước đó", locale="vi")

    async def _slow(tool: Any, args: Any, started: float) -> Any:
        await db_session.execute(text("select pg_sleep(5)"))
        raise AssertionError("cancelled before it returns")

    monkeypatch.setattr(ex, "_dispatch", _slow)
    result = await asyncio.wait_for(ex.run("TOOL-get_finance_dashboard", {}), 3)
    assert result.status == "timeout"
    # the turn's transaction is intact: earlier writes are readable, later tools run bounded
    assert (await db_session.execute(text(
        "select count(*) from ai.messages where conversation_id = :c"),
        {"c": keep.conversation_id})).scalar_one() == 2  # fmt: skip
    assert (await db_session.execute(text("show statement_timeout"))).scalar_one() == "0"


# ------------------------------------------------------------------- F-C2 replay
def test_replay_is_off_unless_explicitly_on(monkeypatch: pytest.MonkeyPatch) -> None:
    c = get_config()
    monkeypatch.setattr(c, "demo_mode", True)
    monkeypatch.setattr(c, "ai_demo_replay", None)
    assert replay_enabled(c) is False
    monkeypatch.setattr(c, "ai_demo_replay", False)
    assert replay_enabled(c) is False
    monkeypatch.setattr(c, "ai_demo_replay", True)
    assert replay_enabled(c) is True


async def test_replay_answer_is_labelled_everywhere(api, monkeypatch) -> None:
    c = get_config()
    monkeypatch.setattr(c, "ai_demo_replay", True)
    monkeypatch.setattr(c, "ai_demo_token_delay_sec", 0.0)
    api.app.dependency_overrides[get_chat_gateway] = lambda: Scripted()
    try:
        r = await api.call("POST", "/ai/chat", role="CEO", headers=api.headers("CEO", idem=True),
                           json={"message": "Doanh thu Q3?"})  # fmt: skip
        assert r.status_code == 200, r.text
        body = r.json()["data"]
        assert body["mode"] == "replay"
        assert body["answer"].startswith("[Kịch bản demo]")
        s = await api.call("POST", "/ai/chat/stream", role="CEO",
                           headers=api.headers("CEO", idem=True),
                           json={"message": "Doanh thu Q3?"})  # fmt: skip
        assert '"mode": "replay"' in s.text
    finally:
        api.app.dependency_overrides.pop(get_chat_gateway, None)


async def test_stored_replay_message_keeps_its_label(db_session, monkeypatch) -> None:
    from app.modules.ai.services.conversation_service import ConversationService

    monkeypatch.setattr(get_config(), "ai_demo_replay", True)
    user = ceo()
    turn = await ChatService(db_session, Scripted()).chat(user, "Doanh thu Q3?", locale="vi")
    assert turn.mode == "replay"
    msgs = await ConversationService(db_session).messages(user, turn.conversation_id)
    assert [m.mode for m in msgs if m.sender == "assistant"] == ["replay"]


async def test_live_answer_is_not_labelled_replay(api) -> None:
    api.app.dependency_overrides[get_chat_gateway] = lambda: Scripted()
    try:
        r = await api.call("POST", "/ai/chat", role="CEO", headers=api.headers("CEO", idem=True),
                           json={"message": "Xin chào"})  # fmt: skip
        assert r.json()["data"]["mode"] in ("live", "fixture")
    finally:
        api.app.dependency_overrides.pop(get_chat_gateway, None)


# ------------------------------------------------------------------- F-M2
class _NoLocal:
    async def chat(self, req: ChatRequest) -> ChatResponse:
        raise TemplateRequired("CONFIDENTIAL", "no local LLM available — use template")


async def test_template_required_is_a_clear_error_not_500(api) -> None:
    api.app.dependency_overrides[get_chat_gateway] = lambda: _NoLocal()
    try:
        r = await api.call("POST", "/ai/chat", role="CEO", headers=api.headers("CEO", idem=True),
                           json={"message": "Gọi 0901234567"})  # fmt: skip
        assert r.status_code == 502, r.text
        err = r.json()["error"]
        assert err["code"] == "AI_PROVIDER_ERROR"
        assert err["details"]["reason"] == "local_model_unavailable"
        s = await api.call("POST", "/ai/chat/stream", role="CEO",
                           headers=api.headers("CEO", idem=True),
                           json={"message": "Gọi 0901234567"})  # fmt: skip
        assert s.status_code == 200 and "event: error" in s.text
        assert "local_model_unavailable" in s.text
    finally:
        api.app.dependency_overrides.pop(get_chat_gateway, None)


# ------------------------------------------------------------------- F-H8 tools
def test_every_advertised_tool_can_run() -> None:
    perms = frozenset(ROLE_PERMISSIONS["CEO"])
    ready = [t.name for t in advertisable_for(perms) if model_ready(t)]
    assert "TOOL-record_decision" in ready and "TOOL-list_invoices" in ready
    for name in ("TOOL-generate_report", "TOOL-request_approval", "TOOL-get_cash_flow_forecast",
                 "TOOL-get_runway_what_if", "TOOL-get_finance_forecast"):  # fmt: skip
        assert name not in ready
    for t in all_tools():
        if t.is_write and model_ready(t):
            assert get_action(t.action_name or "") is not None


async def test_chat_does_not_offer_a_tool_that_cannot_run(db_session) -> None:
    tools = ["TOOL-generate_report", "TOOL-get_finance_dashboard"]
    await db_session.execute(
        update(AgentProfile)
        .where(AgentProfile.code == "ceo")
        .values(allowed_tools=tools, is_enabled=True)
    )
    gw = Scripted()
    await ChatService(db_session, gw).chat(ceo(), "Báo cáo", locale="vi")
    assert [t.name for t in gw.requests[0].tools] == ["TOOL-get_finance_dashboard"]


@pytest.mark.parametrize(
    ("tool", "key"),
    [
        ("TOOL-list_invoices", "invoices"),
        ("TOOL-list_expenses", "expenses"),
        ("TOOL-list_deals", "deals"),
        ("TOOL-list_tasks", "tasks"),
        ("TOOL-list_objectives", "objectives"),
        ("TOOL-list_hiring_plans", "hiring_plans"),
        ("TOOL-get_kpi_status", "kpis"),
        ("TOOL-get_budget_status", "budgets"),
        ("TOOL-get_sales_pipeline", "stages"),
        ("TOOL-get_workload", "items"),
    ],
)
async def test_read_tool_returns_records_of_its_own_kind(db_session, tool: str, key: str) -> None:
    result = await ToolExecutor(db_session, ceo()).run(tool, {"limit": 5})
    assert result.status == "ok", result.error_code
    assert (key in result.data and "metrics" not in result.data) or key == "stages"
    assert isinstance(result.data[key], list)


async def test_list_tool_row_carries_the_record_values(db_session) -> None:
    result = await ToolExecutor(db_session, ceo()).run("TOOL-list_invoices", {"limit": 3})
    assert result.data["invoices"], "the seed has invoices"
    row = result.data["invoices"][0]
    assert isinstance(row["total_amount"], int)
    assert result.sources[0].value == row["total_amount"]


def test_amounts_survive_the_pii_scrub_strings_do_not() -> None:
    out = scrub_payload({"total_amount": 1_250_000_000, "note": "STK 0123456789012"})
    assert out["total_amount"] == 1_250_000_000
    assert "0123456789012" not in json.dumps(out)


async def test_get_source_document_refuses_a_secret_document(db_session) -> None:
    from datetime import UTC, datetime

    from app.modules.idp.models import DocumentPage, SourceDocument

    user = ceo()
    doc = SourceDocument(
        channel="C3", kind="FILE", original_filename="d.xlsx", scan_status="CLEAN", pillars=[],
        status="NEEDS_REVIEW", sensitivity_level=4, source="IDP", data_classification="SECRET",
        submitted_at=datetime.now(UTC), submitted_by=user.user_id,
    )  # fmt: skip
    db_session.add(doc)
    await db_session.flush()
    db_session.add(DocumentPage(source_document_id=doc.id, page_number=1, text_layer_exists=True,
                                ocr_used=False, text_content="Bảng lương"))  # fmt: skip
    await db_session.flush()
    ex = ToolExecutor(db_session, user)
    out = await ex.run("TOOL-get_source_document", {"document_id": str(doc.id)})
    assert out.status == "forbidden" and not out.data
    doc.sensitivity_level = 3
    await db_session.flush()
    ok = await ex.run("TOOL-get_source_document", {"document_id": str(doc.id), "page": 1})
    assert ok.status == "ok" and ok.data["pages"][0]["text"] == "Bảng lương"
    assert "url" not in ok.data


async def test_record_decision_runs_through_the_action_registry_and_undoes(db_session) -> None:
    user = ceo()
    out = await ActionService(db_session).propose(
        user, action_name="ACT-record_decision", tool_name="TOOL-record_decision",
        input_data={"title": "Mở chi nhánh Đà Nẵng", "rationale": "Nhu cầu tăng"},
        idempotency_key=f"t-{uuid.uuid4()}",
    )  # fmt: skip
    assert out.status == "executed", out
    row = (await db_session.execute(select(Decision).where(
        Decision.id == uuid.UUID(out.result_refs[0]["id"])))).scalar_one()  # fmt: skip
    assert row.content == "Mở chi nhánh Đà Nẵng" and row.rationale == "Nhu cầu tăng"
    await ActionService(db_session).undo(user, out.id, reason="nhầm")
    await db_session.refresh(row)
    assert row.status == "cancelled"


async def test_create_meeting_action_and_undo(db_session) -> None:
    user = ceo()
    out = await ActionService(db_session).propose(
        user, action_name="ACT-create_meeting", tool_name="TOOL-create_meeting",
        input_data={"title": "Họp giao ban", "starts_at": "2026-11-10T02:00:00Z"},
        idempotency_key=f"t-{uuid.uuid4()}",
    )  # fmt: skip
    assert out.status == "executed", out
    undone = await ActionService(db_session).undo(user, out.id, reason="nhầm")
    assert undone.status == "undone"


async def test_upsert_deal_changes_an_existing_deal_and_refuses_an_unknown_one(db_session) -> None:
    user = Principal(user_id=uuid.uuid4(), role="DIR", scope_pillars=frozenset({"C"}),
                     permissions=frozenset(ROLE_PERMISSIONS["DIR"]))  # fmt: skip
    data = (await ToolExecutor(db_session, user).run("TOOL-list_deals", {"limit": 50})).data
    open_deal = next(d for d in data["deals"] if not d["stage"].startswith("closed"))
    act = get_action("ACT-upsert_deal")
    assert act is not None
    from app.modules.idp.services.actions.registry import ActionContext

    bad, _ = act.parse({"name": "Không tồn tại Zqx"})
    assert await act.validate(db_session, user, bad, ActionContext())
    good, _ = act.parse({"name": open_deal["name"], "amount": open_deal["deal_value"] + 1000})
    assert await act.validate(db_session, user, good, ActionContext()) == []
    outcome = await act.run(db_session, user, good, ActionContext())
    assert outcome.snapshot == {"deal_value": open_deal["deal_value"]}
    await act.undo(db_session, user, outcome)
    after = (await ToolExecutor(db_session, user).run("TOOL-list_deals", {"limit": 50})).data
    same = next(d for d in after["deals"] if d["name"] == open_deal["name"])
    assert same["deal_value"] == open_deal["deal_value"]

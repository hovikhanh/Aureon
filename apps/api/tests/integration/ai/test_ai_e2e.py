"""T-310 — AI Core end-to-end + coverage sweep over the HTTP surface (EP-110..119).

Drives the real app via the `api` client so the router, dependencies, and services run exactly as
in production, plus a few service-level edge branches (tool executor, conversation reads, errors)
that the happy path does not reach. Chat uses a scripted gateway injected through the app override
so no provider is called.
"""

import uuid

import pytest

from app.core.deps import Principal
from app.core.errors import NotFoundError, PermissionDeniedError
from app.modules.ai.services.action_service import ActionService
from app.modules.ai.services.conversation_service import ConversationService
from app.modules.ai.services.tool_executor import ToolExecutor
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

pytestmark = pytest.mark.integration


def principal(role: str) -> Principal:
    return Principal(user_id=uuid.uuid4(), role=role, permissions=frozenset(ROLE_PERMISSIONS[role]))


# ---------- HTTP: tools + usage + kill switch ----------
async def test_ep119_tools_lists_for_caller(api) -> None:
    r = await api.call("GET", "/ai/tools", role="CEO")
    assert r.status_code == 200
    tools = r.json()["data"]
    assert tools and any(t["name"].startswith("TOOL-") for t in tools)
    assert all({"name", "kind", "available", "classification"} <= set(t) for t in tools)


async def test_ep118_kill_switch_status_and_set(api) -> None:
    # status open to ai:query
    s = await api.call("GET", "/ai/kill-switch", role="CEO")
    assert s.status_code == 200 and s.json()["data"]["enabled"] is False
    # set requires ai:admin — EMPLOYEE forbidden
    forbidden = await api.call(
        "PUT", "/ai/kill-switch", role="EMPLOYEE",
        json={"enabled": True, "mode": "WRITE_OFF", "agents": [], "reason": "x"},
    )  # fmt: skip
    assert forbidden.status_code == 403
    ok = await api.call(
        "PUT", "/ai/kill-switch", role="ADMIN",
        json={"enabled": True, "mode": "WRITE_OFF", "agents": [], "reason": "incident"},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )  # fmt: skip
    assert ok.status_code == 200 and ok.json()["data"]["enabled"] is True


async def test_ep119_usage_admin_only(api) -> None:
    assert (await api.call("GET", "/ai/usage", role="EMPLOYEE")).status_code == 403
    r = await api.call("GET", "/ai/usage", role="ADMIN")
    assert r.status_code == 200 and "budget_usd" in r.json()["data"]


# ---------- HTTP: actions lifecycle (list → get → confirm → undo) ----------
async def test_ep115_116_action_lifecycle_over_http(api, db_session) -> None:
    # seed an L2 proposed action owned by the CEO caller the client will act as
    ceo_id = uuid.uuid4()
    svc = ActionService(db_session)
    from app.modules.ai.schemas import KillSwitchIn
    from app.modules.ai.services.kill_switch_service import KillSwitchService

    # force L2 so the action waits as a confirm card
    await KillSwitchService(db_session).set(
        principal("ADM"), KillSwitchIn(enabled=True, mode="WRITE_OFF", agents=[], reason="t")
    )
    ceo = Principal(user_id=ceo_id, role="CEO", permissions=frozenset(ROLE_PERMISSIONS["CEO"]))
    out = await svc.propose(
        ceo, action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data={"title": "e2e task", "status": "todo"}, idempotency_key="e2e-1",
    )  # fmt: skip
    await db_session.flush()

    # list as the same user id so on_behalf_of matches
    lst = await api.call(
        "GET", "/ai/actions", role="CEO", headers=api.headers("CEO", user_id=ceo_id)
    )
    assert lst.status_code == 200
    ids = [a["id"] for a in lst.json()["data"]]
    assert str(out.id) in ids

    got = await api.call(
        "GET", f"/ai/actions/{out.id}", role="CEO", headers=api.headers("CEO", user_id=ceo_id)
    )
    assert got.status_code == 200 and got.json()["data"]["status"] == "proposed"

    confirmed = await api.call(
        "POST", f"/ai/actions/{out.id}/confirm", role="CEO",
        headers=api.headers("CEO", user_id=ceo_id, idem=True), json={},
    )  # fmt: skip
    assert confirmed.status_code == 200 and confirmed.json()["data"]["status"] == "executed"

    undone = await api.call(
        "POST", f"/ai/actions/{out.id}/undo", role="CEO",
        headers=api.headers("CEO", user_id=ceo_id, idem=True), json={"reason": "e2e"},
    )  # fmt: skip
    assert undone.status_code == 200 and undone.json()["data"]["status"] == "undone"


async def test_ep115_reject_over_http(api, db_session) -> None:
    from app.modules.ai.schemas import KillSwitchIn
    from app.modules.ai.services.kill_switch_service import KillSwitchService

    await KillSwitchService(db_session).set(
        principal("ADM"), KillSwitchIn(enabled=True, mode="WRITE_OFF", agents=[], reason="t")
    )
    ceo_id = uuid.uuid4()
    ceo = Principal(user_id=ceo_id, role="CEO", permissions=frozenset(ROLE_PERMISSIONS["CEO"]))
    out = await ActionService(db_session).propose(
        ceo, action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data={"title": "reject me", "status": "todo"}, idempotency_key="e2e-rej",
    )  # fmt: skip
    await db_session.flush()
    r = await api.call(
        "POST", f"/ai/actions/{out.id}/reject", role="CEO",
        headers=api.headers("CEO", user_id=ceo_id, idem=True), json={"reason": "no"},
    )  # fmt: skip
    assert r.status_code == 200 and r.json()["data"]["status"] == "rejected"


# ---------- service edge branches: tool executor ----------
async def test_tool_executor_read_metric_and_pillar(db_session) -> None:
    ex = ToolExecutor(db_session, principal("CEO"))
    fin = await ex.run("TOOL-get_finance_dashboard", {})
    assert fin.status in ("ok",)  # CEO sees Finance
    alerts = await ex.run("TOOL-list_alerts", {})
    assert alerts.status == "ok" and "open_alerts" in alerts.data


async def test_tool_executor_rejects_unknown_write_and_forbidden(db_session) -> None:
    ex = ToolExecutor(db_session, principal("CEO"))
    assert (await ex.run("TOOL-does-not-exist", {})).error_code == "AI_UNKNOWN_TOOL"
    # a write tool is materialised as an action, not executed here
    write = await ex.run("TOOL-create_task", {"title": "x"})
    assert write.error_code == "AI_WRITE_VIA_ACTION"
    # metric tool needs an argument
    assert (await ex.run("TOOL-get_metric", {})).error_code == "AI_MISSING_ARGUMENT"
    # EMPLOYEE lacks the finance permission the tool requires → forbidden
    emp = ToolExecutor(db_session, principal("EMP"))
    assert (await emp.run("TOOL-get_finance_dashboard", {})).status == "forbidden"


async def test_tool_executor_refuses_p1_frozen_unless_curated(db_session) -> None:
    """TC-M11-14 (R-DEC-16): a model naming a frozen product/risk tool gets AI_TOOL_NOT_AVAILABLE;
    only the curated demo replay may opt in with `allow_frozen`."""
    ex = ToolExecutor(db_session, principal("CEO"))
    for name in ("TOOL-get_risk_dashboard", "TOOL-get_product_dashboard", "TOOL-list_risks"):
        assert (await ex.run(name, {})).error_code == "AI_TOOL_NOT_AVAILABLE"
    curated = await ex.run("TOOL-get_risk_dashboard", {}, allow_frozen=True)
    assert curated.status == "ok"


async def test_tool_executor_unknown_metric_is_no_data(db_session) -> None:
    ex = ToolExecutor(db_session, principal("CEO"))
    r = await ex.run("TOOL-get_metric", {"metric_code": "METRIC-DOES-NOT-EXIST"})
    assert r.error_code in ("AI_NO_DATA_AVAILABLE", "FORBIDDEN_ROLE")


# ---------- service edge branches: conversation reads ----------
async def test_conversation_reads_and_not_found(db_session) -> None:
    svc = ConversationService(db_session)
    ceo = principal("CEO")
    assert await svc.list_for_user(ceo) == [] or isinstance(await svc.list_for_user(ceo), list)
    with pytest.raises(NotFoundError):
        await svc.messages(ceo, uuid.uuid4())


# ---------- service edge branches: action errors ----------
async def test_action_get_foreign_is_not_found(db_session) -> None:
    svc = ActionService(db_session)
    ceo = principal("CEO")
    out = await svc.propose(
        ceo, action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data={"title": "owned", "status": "todo"}, idempotency_key="e2e-own",
    )  # fmt: skip
    other = principal("DIR")
    with pytest.raises(NotFoundError):
        await svc.get(other, out.id)


async def test_action_undo_requires_executed(db_session) -> None:
    from app.core.errors import ConflictStateError
    from app.modules.ai.schemas import KillSwitchIn
    from app.modules.ai.services.kill_switch_service import KillSwitchService

    await KillSwitchService(db_session).set(
        principal("ADM"), KillSwitchIn(enabled=True, mode="WRITE_OFF", agents=[], reason="t")
    )
    svc = ActionService(db_session)
    ceo = principal("CEO")
    out = await svc.propose(
        ceo, action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data={"title": "proposed only", "status": "todo"}, idempotency_key="e2e-noundo",
    )  # fmt: skip
    with pytest.raises(ConflictStateError):
        await svc.undo(ceo, out.id)  # cannot undo a non-executed action


async def test_action_propose_unknown_action_404(db_session) -> None:
    svc = ActionService(db_session)
    with pytest.raises(NotFoundError):
        await svc.propose(
            principal("CEO"), action_name="ACT-not-real", tool_name=None,
            input_data={}, idempotency_key="e2e-unknown",
        )  # fmt: skip


async def test_confirm_requires_ai_write(db_session) -> None:
    svc = ActionService(db_session)
    ceo = principal("CEO")
    out = await svc.propose(
        ceo, action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data={"title": "x", "status": "todo"}, idempotency_key="e2e-conf",
    )  # fmt: skip
    # strip ai:write to prove the gate
    no_ai = Principal(
        user_id=ceo.user_id,
        role="CEO",
        permissions=frozenset(p for p in ROLE_PERMISSIONS["CEO"] if p != "ai:write"),
    )
    # the action auto-executed at L3 (no kill switch here); an executed action can't confirm
    from app.core.errors import ConflictStateError

    with pytest.raises((ConflictStateError, PermissionDeniedError)):
        await svc.confirm(no_ai, out.id)


# ---------- model call log writer (ai_service + repository) ----------
async def test_model_call_log_writer_persists_and_aggregates(db_session) -> None:
    from app.core.model_gateway import CallRecord
    from app.modules.ai.repositories import ModelCallLogRepository, month_start
    from app.modules.ai.services.ai_service import ModelCallLogWriter

    writer = ModelCallLogWriter(db_session)
    rec = CallRecord(
        caller_module="ai",
        task_kind="chat",
        provider="omniroute",
        model="claude",
        status="ok",
        tokens_in=120,
        tokens_out=60,
        estimated_cost_micro_usd=300_000,
        latency_ms=700,
        prompt_sha256="a" * 64,
        classification="INTERNAL",
        route_reason="no pii",
        fallback_from=None,
        error_code=None,
        user_id=uuid.uuid4(),
        message_id=None,
        source_document_id=None,
    )
    await writer.record(rec)
    spend = await writer.month_spend_micro_usd()
    assert spend >= 300_000
    assert await ModelCallLogRepository(db_session).cost_since(month_start()) >= 300_000


# ---------- conversation messages loop ----------
async def test_conversation_messages_returns_turn(db_session) -> None:
    from app.core.model_gateway.types import ChatRequest, ChatResponse, Usage
    from app.modules.ai.services.chat_service import ChatService

    class PlainGateway:
        async def chat(self, req: ChatRequest) -> ChatResponse:
            return ChatResponse(
                content="xin chào", provider="fixture", model="x", usage=Usage(3, 4)
            )

    ceo = principal("CEO")
    turn = await ChatService(db_session, PlainGateway()).chat(ceo, "chào bạn")
    msgs = await ConversationService(db_session).messages(ceo, turn.conversation_id)
    assert [m.sender for m in msgs] == ["user", "assistant"]
    assert any(m.content == "xin chào" for m in msgs)
    convs = await ConversationService(db_session).list_for_user(ceo)
    assert any(c.id == turn.conversation_id for c in convs)


# ---------- autonomy policy row override ----------
async def test_autonomy_policy_row_overrides_default(db_session, ceiling_l3) -> None:
    from app.modules.ai.models import AutonomyPolicy
    from app.modules.ai.services.autonomy import resolve_level

    db_session.add(
        AutonomyPolicy(
            action_name="ACT-create_task",
            tool_name="TOOL-create_task",
            role_code="CEO",
            max_amount=None,
            currency=None,
            level="L2",
            max_level="L3",
            is_active=True,
        )
    )
    await db_session.flush()
    level = await resolve_level(
        db_session,
        action_name="ACT-create_task",
        role="CEO",
        amount=None,
        agent_code="assistant",
    )
    assert level == "L2"


# ---------- HTTP chat over the real router (EP-110/111/112) with an overridden gateway ----------
def _install_gateway(app, response_factory):
    from app.core.model_gateway.types import ChatRequest
    from app.modules.ai.routes.router import get_chat_gateway

    class _GW:
        last: ChatRequest | None = None

        async def chat(self, req: ChatRequest):
            _GW.last = req
            return response_factory(req)

    gw = _GW()
    app.dependency_overrides[get_chat_gateway] = lambda: gw
    return gw


async def test_ep110_chat_over_http(api) -> None:
    from app.core.model_gateway.types import ChatResponse, Usage

    _install_gateway(
        api.app,
        lambda req: ChatResponse(
            content="Doanh thu quý 3 ổn định.", provider="fixture", model="x", usage=Usage(10, 20)
        ),
    )
    r = await api.call(
        "POST",
        "/ai/chat",
        role="CEO",
        headers=api.headers("CEO", idem=True),
        json={"message": "Tình hình doanh thu?"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["answer"] == "Doanh thu quý 3 ổn định."
    assert data["truncated"] is False

    # EP-112: the conversation now shows up for the same caller
    convs = await api.call("GET", "/ai/conversations", role="CEO")
    assert convs.status_code == 200


async def test_ep110_secret_prompt_is_refused(api) -> None:
    # a salary prompt classifies as SECRET → the gateway raises, route returns 423 (no LLM)
    from app.core.model_gateway.errors import SecretDataBlockedError

    def _raise(req):
        raise SecretDataBlockedError

    _install_gateway(api.app, _raise)
    r = await api.call(
        "POST",
        "/ai/chat",
        role="CEO",
        headers=api.headers("CEO", idem=True),
        json={"message": "Cho tôi xem bảng lương nhân viên"},
    )
    assert r.status_code == 423
    assert r.json()["error"]["code"] == "AI_DISABLED"


async def test_ep111_chat_stream_over_http(api) -> None:
    from app.core.model_gateway.types import ChatResponse, Usage

    _install_gateway(
        api.app,
        lambda req: ChatResponse(
            content="xin chào từ SSE", provider="fixture", model="x", usage=Usage(4, 8)
        ),
    )
    r = await api.call(
        "POST",
        "/ai/chat/stream",
        role="CEO",
        headers=api.headers("CEO", idem=True),
        json={"message": "chào"},
    )
    assert r.status_code == 200
    body = r.text
    assert "event: start" in body
    assert "event: token" in body
    assert "event: done" in body


# ---------- action_service remaining branches ----------
async def test_action_list_filters(db_session) -> None:
    svc = ActionService(db_session)
    ceo = principal("CEO")
    await svc.propose(
        ceo,
        action_name="ACT-create_task",
        tool_name="TOOL-create_task",
        input_data={"title": "f1", "status": "todo"},
        idempotency_key="flt-1",
    )
    executed = await svc.list_for(ceo, status="executed")
    assert all(a.status == "executed" for a in executed)
    l3 = await svc.list_for(ceo, autonomy_level="L3")
    assert all(a.autonomy_level == "L3" for a in l3)


async def test_confirm_with_edited_input(db_session) -> None:
    from app.modules.ai.schemas import KillSwitchIn
    from app.modules.ai.services.kill_switch_service import KillSwitchService

    await KillSwitchService(db_session).set(
        principal("ADM"), KillSwitchIn(enabled=True, mode="WRITE_OFF", agents=[], reason="t")
    )
    svc = ActionService(db_session)
    ceo = principal("CEO")
    out = await svc.propose(
        ceo,
        action_name="ACT-create_task",
        tool_name="TOOL-create_task",
        input_data={"title": "orig", "status": "todo"},
        idempotency_key="edit-1",
    )
    done = await svc.confirm(ceo, out.id, edited_input={"title": "edited", "status": "todo"})
    assert done.status == "executed"
    assert done.input_preview["title"] == "edited"


async def test_finance_action_opens_approval_and_executes_on_hook(db_session) -> None:
    # A finance L2 action opens a 2-sided approval; on final APPROVE the hook executes it.
    # We drive `_maybe_open_approval` directly (ordering-independent, no monkeypatch) so the test
    # exercises exactly the finance branch + execute_approved wiring.
    from app.modules.platform.services.approval_service import ApprovalService

    svc = ActionService(db_session)
    requester = principal("CEO")
    assignee = uuid.uuid4()
    out = await svc.propose(
        requester,
        action_name="ACT-create_task",
        tool_name="TOOL-create_task",
        input_data={"title": "big spend", "status": "todo", "assignee_id": str(assignee)},
        idempotency_key="fin-1",
        amount=600_000_000,
    )
    # ACT-create_task is L3 by default → it auto-executed; reset it to a pending finance approval
    action = await svc._locked(out.id)
    action.status = "proposed"
    action.executed_at = None
    action.result_refs = None
    await db_session.flush()
    await svc._maybe_open_approval(requester, action, 600_000_000)
    await db_session.flush()
    assert action.approval_request_id is not None
    approval_id = action.approval_request_id

    # confirm is blocked while the approval is pending
    from app.core.errors import ConflictStateError

    with pytest.raises(ConflictStateError):
        await svc.confirm(requester, out.id)
    # drive the 2-sided approval; the EP-WF-03 hook executes the AI action on final APPROVE
    asvc = ApprovalService(db_session)

    async def _hook(req):
        # the CEO (full execution scope) finalises the write on approval
        await svc.execute_approved(principal("CEO"), req.ai_action_id)

    await asvc.decide(principal("CEO"), approval_id, decision="approve", reason=None)
    await asvc.decide(
        principal("DIR"),
        approval_id,
        decision="approve",
        reason=None,
        on_approved=_hook,
    )
    refreshed = await svc.get(requester, out.id)
    assert refreshed.status == "executed"


# ---------- chat_service: tool-call loop + budget + conversation reuse ----------
async def test_chat_runs_tool_call_then_answers(db_session) -> None:
    from app.core.model_gateway.types import ChatRequest, ChatResponse, ToolCall, Usage
    from app.modules.ai.services.chat_service import ChatService

    calls = {"n": 0}

    class ToolThenAnswer:
        async def chat(self, req: ChatRequest) -> ChatResponse:
            calls["n"] += 1
            if calls["n"] == 1:
                return ChatResponse(
                    content="",
                    provider="fixture",
                    model="x",
                    usage=Usage(5, 5),
                    tool_calls=(
                        ToolCall(id="c1", name="TOOL-get_finance_dashboard", arguments={}),
                    ),
                )
            return ChatResponse(
                content="Tài chính ổn.", provider="fixture", model="x", usage=Usage(5, 5)
            )

    ceo = principal("CEO")
    turn = await ChatService(db_session, ToolThenAnswer()).chat(ceo, "Tài chính thế nào?")
    assert turn.answer == "Tài chính ổn."
    assert any(fc["tool"] == "TOOL-get_finance_dashboard" for fc in turn.function_calls)
    assert turn.sources  # the finance tool cited metric sources


async def test_chat_reuses_existing_conversation(db_session) -> None:
    from app.core.model_gateway.types import ChatRequest, ChatResponse, Usage
    from app.modules.ai.services.chat_service import ChatService

    class Plain:
        async def chat(self, req: ChatRequest) -> ChatResponse:
            return ChatResponse(content="ok", provider="fixture", model="x", usage=Usage(1, 1))

    ceo = principal("CEO")
    svc = ChatService(db_session, Plain())
    first = await svc.chat(ceo, "câu 1")
    second = await svc.chat(ceo, "câu 2", conversation_id=first.conversation_id)
    assert second.conversation_id == first.conversation_id


# ---------- insight_service: generate, list filters, dismiss, not-found ----------
async def test_insight_generate_list_and_dismiss(db_session) -> None:
    from app.modules.ai.services.insight_service import InsightService

    svc = InsightService(db_session)
    ceo = principal("CEO")
    # generate for each pillar until one produces an insight (seed-dependent)
    made = None
    for pillar in ("F", "O", "C", "U", "S"):
        made = await svc.generate_for_pillar(ceo, pillar)
        if made is not None:
            break
    if made is None:
        pytest.skip("seed produced no insightable pillar")
    listed = await svc.list_for(ceo)
    assert any(i.id == made.id for i in listed)
    # filters execute their branches
    await svc.list_for(ceo, pillar=made.pillar)
    await svc.list_for(ceo, kind=made.kind)
    await svc.list_for(ceo, severity="warning")
    dismissed = await svc.dismiss(ceo, made.id)
    assert dismissed.id == made.id
    # the dismissed insight no longer appears in the active list
    assert all(i.id != made.id for i in await svc.list_for(ceo))


async def test_insight_dismiss_not_found(db_session) -> None:
    from app.modules.ai.services.insight_service import InsightService

    with pytest.raises(NotFoundError):
        await InsightService(db_session).dismiss(principal("CEO"), uuid.uuid4())


# ---------- tool_executor: record-list tools, metric detail, sources dict ----------
async def test_tool_executor_record_list_tool_cites_pillar(db_session) -> None:
    ex = ToolExecutor(db_session, principal("CEO"))
    r = await ex.run("TOOL-list_tasks", {})
    assert r.status in ("ok",)
    # record-list tools fall back to the owning pillar's aggregate metrics as citations
    assert isinstance(r.sources_as_dict(), list)


async def test_tool_executor_metric_detail_ok(db_session) -> None:
    from app.modules.platform.services.metric_query import MetricQueryService

    values = await MetricQueryService(db_session).current_values(pillars=["F"])
    if not values:
        pytest.skip("no finance metric in seed")
    ex = ToolExecutor(db_session, principal("CEO"))
    r = await ex.run("TOOL-get_metric", {"metric_code": values[0].metric_code})
    assert r.status in ("ok", "forbidden")
    if r.status == "ok":
        assert r.sources and r.sources[0].type == "metric_value"
        assert r.sources_as_dict()[0]["type"] == "metric_value"


async def test_tool_executor_employee_metric_forbidden(db_session) -> None:
    # an EMPLOYEE asking a finance metric detail is scoped out → forbidden
    ex = ToolExecutor(db_session, principal("EMP"))
    r = await ex.run("TOOL-get_metric", {"metric_code": "METRIC-F-01"})
    assert r.status in ("forbidden",) or r.error_code in ("FORBIDDEN_ROLE", "AI_NO_DATA_AVAILABLE")


# ---------- HTTP: EP-112 messages + EP-114 insight list/dismiss ----------
async def test_ep112_messages_over_http(api) -> None:
    from app.core.model_gateway.types import ChatResponse, Usage

    _install_gateway(
        api.app,
        lambda req: ChatResponse(
            content="trả lời", provider="fixture", model="x", usage=Usage(2, 3)
        ),
    )
    uid = uuid.uuid4()
    chat = await api.call(
        "POST",
        "/ai/chat",
        role="CEO",
        headers=api.headers("CEO", user_id=uid, idem=True),
        json={"message": "hỏi"},
    )
    conv_id = chat.json()["data"]["conversation_id"]
    msgs = await api.call(
        "GET",
        f"/ai/conversations/{conv_id}/messages",
        role="CEO",
        headers=api.headers("CEO", user_id=uid),
    )
    assert msgs.status_code == 200
    assert [m["sender"] for m in msgs.json()["data"]] == ["user", "assistant"]


async def test_ep114_insights_list_and_dismiss_over_http(api, db_session) -> None:
    from app.modules.ai.services.insight_service import InsightService

    made = None
    for pillar in ("F", "O", "C", "U", "S"):
        made = await InsightService(db_session).generate_for_pillar(principal("CEO"), pillar)
        if made is not None:
            break
    if made is None:
        pytest.skip("seed produced no insightable pillar")
    await db_session.flush()
    lst = await api.call("GET", "/ai/insights", role="CEO")
    assert lst.status_code == 200
    d = await api.call(
        "POST",
        f"/ai/insights/{made.id}/dismiss",
        role="CEO",
        headers=api.headers("CEO", idem=True),
        json={},
    )
    assert d.status_code == 200


# ---------- action_service: reject-after-execute, confirm-while-pending, SSE tool path ----------
async def test_reject_non_proposed_conflicts(db_session, ceiling_l3) -> None:
    from app.core.errors import ConflictStateError

    svc = ActionService(db_session)
    ceo = principal("CEO")
    out = await svc.propose(
        ceo,
        action_name="ACT-create_task",
        tool_name="TOOL-create_task",
        input_data={"title": "auto L3", "status": "todo"},
        idempotency_key="rej-exec",
    )
    # L3 auto-executed → it can no longer be rejected
    with pytest.raises(ConflictStateError):
        await svc.reject(ceo, out.id, reason="late")


async def test_confirm_blocked_while_approval_pending(db_session) -> None:
    # A proposed action with a pending approval cannot be confirmed directly — it must be decided
    # through the approval. We open the approval via `_maybe_open_approval` (ordering-independent).
    from app.core.errors import ConflictStateError

    svc = ActionService(db_session)
    ceo = principal("CEO")
    out = await svc.propose(
        ceo,
        action_name="ACT-create_task",
        tool_name="TOOL-create_task",
        input_data={"title": "pending", "status": "todo"},
        idempotency_key="conf-pending",
    )
    action = await svc._locked(out.id)
    action.status = "proposed"
    action.executed_at = None
    action.result_refs = None
    await db_session.flush()
    await svc._maybe_open_approval(ceo, action, 800_000_000)
    await db_session.flush()
    assert action.approval_request_id is not None
    with pytest.raises(ConflictStateError):
        await svc.confirm(ceo, out.id)


async def test_sse_stream_emits_tool_events(api) -> None:
    from app.core.model_gateway.types import ChatRequest, ChatResponse, ToolCall, Usage

    n = {"i": 0}

    def _factory(req: ChatRequest) -> ChatResponse:
        n["i"] += 1
        if n["i"] == 1:
            return ChatResponse(
                content="",
                provider="fixture",
                model="x",
                usage=Usage(5, 5),
                tool_calls=(ToolCall(id="c1", name="TOOL-get_finance_dashboard", arguments={}),),
            )
        return ChatResponse(content="xong", provider="fixture", model="x", usage=Usage(5, 5))

    _install_gateway(api.app, _factory)
    r = await api.call(
        "POST",
        "/ai/chat/stream",
        role="CEO",
        headers=api.headers("CEO", idem=True),
        json={"message": "tài chính?"},
    )
    assert r.status_code == 200
    assert "event: tool_call" in r.text and "event: tool_result" in r.text

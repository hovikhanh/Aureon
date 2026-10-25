"""T-647 — tool/model call audit + EP-AI-22/23 + EP-AI-15 `agent`/`period` (R-DEC-74).

TC-M16-10 (audit columns, one `request_id` per turn), TC-M16-11 (scrubbed arguments),
TC-M16-09 (logs part: admin-only, tenant filter). Rolled-back `db_session`; gateway overridden.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select

from app.core.model_gateway.types import ChatRequest, ChatResponse, ToolCall, Usage
from app.modules.ai.models import AIAction, ToolCallLog
from app.modules.ai.services.tool_audit import scrub_arguments
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration


def _install(app: Any, *responses: ChatResponse) -> None:
    from app.modules.ai.routes.router import get_chat_gateway

    queue = list(responses)

    class _GW:
        async def chat(self, req: ChatRequest) -> ChatResponse:
            return queue.pop(0) if queue else ChatResponse(content="ok", provider="f", model="x")

    app.dependency_overrides[get_chat_gateway] = lambda: _GW()


def _calls(*names: str) -> ChatResponse:
    return ChatResponse(
        content="", provider="fixture", model="x", usage=Usage(5, 0),
        tool_calls=tuple(ToolCall(id=f"c{i}", name=n, arguments={"q": "x"})
                         for i, n in enumerate(names)),
    )  # fmt: skip


async def test_chat_turn_logs_share_request_id(api: ApiClient, db_session) -> None:
    _install(
        api.app,
        _calls("TOOL-get_finance_dashboard", "TOOL-get_metric", "TOOL-create_task"),
        ChatResponse(content="Xong.", provider="fixture", model="x", usage=Usage(1, 2)),
    )
    rid = str(uuid.uuid4())
    h = api.headers("CEO", idem=True) | {"X-Request-Id": rid}
    r = await api.http.post("/api/v1/ai/chat", headers=h, json={"message": "Tổng quan?"})
    assert r.status_code == 200, r.text
    assert r.headers["x-request-id"] == rid
    logs = (await db_session.execute(select(ToolCallLog).where(
        ToolCallLog.request_id == uuid.UUID(rid)))).scalars().all()  # fmt: skip
    assert len(logs) == 3
    by = {lg.tool_name: lg for lg in logs}
    assert all(lg.user_id is not None and lg.agent_profile_code == "ceo" for lg in logs)
    assert (
        by["TOOL-get_metric"].tool_kind == "READ" and by["TOOL-get_metric"].autonomy_level == "L0"
    )
    w = by["TOOL-create_task"]
    assert (w.tool_kind, w.autonomy_level) == ("WRITE", "L2")  # effective, not seed L3
    assert w.error_code is None and w.ai_action_id is not None  # T-645b: propose() → card
    assert by["TOOL-get_finance_dashboard"].result_refs
    assert all(set(ref) == {"type", "id", "label"} for ref in by["TOOL-get_finance_dashboard"]
               .result_refs)  # fmt: skip


async def test_propose_links_tool_call_to_action(db_session) -> None:
    from app.core.deps import Principal
    from app.modules.ai.services.action_service import ActionService
    from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

    ceo = Principal(user_id=uuid.uuid4(), role="CEO",
                    permissions=frozenset(ROLE_PERMISSIONS["CEO"]))  # fmt: skip
    from app.core import request_context

    rid = uuid.uuid4()
    token = request_context._request_id.set(str(rid))
    try:
        out = await ActionService(db_session).propose(
            ceo, action_name="ACT-create_task", tool_name="TOOL-create_task",
            input_data={"title": "Gọi 0912345678 về hợp đồng", "status": "todo"},
            idempotency_key="audit-1",
        )  # fmt: skip
    finally:
        request_context._request_id.reset(token)
    assert out.request_id == str(rid)
    log = (await db_session.execute(select(ToolCallLog).where(
        ToolCallLog.ai_action_id == out.id))).scalar_one()  # fmt: skip
    assert (log.tool_kind, log.autonomy_level, log.user_id) == ("WRITE", "L2", ceo.user_id)
    assert log.request_id == rid
    assert "0912345678" not in str(log.arguments)  # level-3 phone scrubbed in the log
    action = (await db_session.execute(select(AIAction).where(
        AIAction.id == out.id))).scalar_one()  # fmt: skip
    assert action.input["title"].startswith("Gọi 0912345678")  # the card keeps the real input


def test_scrub_arguments_drops_level4_and_codes_level3() -> None:
    out = scrub_arguments({"base_salary": 30_000_000, "note": "email a@b.vn",
                           "nested": [{"bank_account": "0123456789"}]})  # fmt: skip
    assert "base_salary" not in out and "a@b.vn" not in str(out) and "0123456789" not in str(out)


def _record(**kw: Any) -> Any:
    from app.core.model_gateway import CallRecord

    base: dict[str, Any] = dict(
        caller_module="ai", task_kind="chat", provider="fixture", model="x", status="ok",
        tokens_in=10, tokens_out=10, estimated_cost_micro_usd=250_000, latency_ms=5,
        prompt_sha256="0" * 64, classification="INTERNAL", route_reason="t",
    )  # fmt: skip
    return CallRecord(**(base | kw))


async def test_ep_ai_22_23_filters_and_rbac(api: ApiClient, db_session) -> None:
    from app.modules.ai.services.ai_service import ModelCallLogWriter

    _install(
        api.app,
        _calls("TOOL-get_metric"),
        ChatResponse(content="ok", provider="fixture", model="x", usage=Usage(1, 1)),
    )
    rid = str(uuid.uuid4())
    h = api.headers("CEO", idem=True) | {"X-Request-Id": rid}
    assert (await api.http.post("/api/v1/ai/chat", headers=h,
                                json={"message": "KPI?"})).status_code == 200  # fmt: skip
    await ModelCallLogWriter(db_session).record(_record(request_id=rid, agent_profile_code="ceo"))

    r = await api.call("GET", "/ai/tool-calls", "ADM", params={"request_id": rid})
    body = r.json()
    assert r.status_code == 200 and body["meta"]["pagination"]["total"] == 1
    row = body["data"][0]
    assert row["tool_name"] == "TOOL-get_metric" and row["request_id"] == rid
    r = await api.call("GET", "/ai/tool-calls", "ADM",
                       params={"tool_kind": "WRITE", "request_id": rid})  # fmt: skip
    assert r.json()["meta"]["pagination"]["total"] == 0

    r = await api.call("GET", "/ai/model-calls", "CEO",
                       params={"request_id": rid, "sort_by": "latency_ms"})  # fmt: skip
    m = r.json()["data"]
    assert r.status_code == 200 and m and m[0]["agent_profile_code"] == "ceo"
    assert "prompt" not in m[0] and set(m[0]) >= {"prompt_sha256", "cost_usd"}

    now = datetime.now(UTC)
    bad = {"from": (now + timedelta(days=1)).isoformat(), "to": now.isoformat()}
    assert (await api.call("GET", "/ai/tool-calls", "ADM", params=bad)).status_code == 400
    assert (await api.call("GET", "/ai/model-calls", "ADM",
                           params={"request_id": "nope"})).status_code == 400  # fmt: skip
    for role in ("DIR", "MGR", "EMP", "REV"):
        for url in ("/ai/tool-calls", "/ai/model-calls", "/ai/usage"):
            assert (await api.call("GET", url, role)).status_code == 403
    other = {"request_id": rid}
    r = await api.call("GET", "/ai/tool-calls", "ADM", params=other, tenant_id=uuid.uuid4())
    assert r.status_code == 200 and r.json()["meta"]["pagination"]["total"] == 0


async def test_usage_group_by_agent_and_period(api: ApiClient, db_session) -> None:
    from app.modules.ai.services.ai_service import ModelCallLogWriter

    await ModelCallLogWriter(db_session).record(_record(agent_profile_code="reporting"))
    r = await api.call("GET", "/ai/usage", "ADM", params={"group_by": "agent"})
    rows = {x["key"]: x for x in r.json()["data"]["rows"]}
    assert rows["reporting"]["cost_usd"] >= 0.25
    agents = (await api.call("GET", "/ai/agents", "ADM")).json()["data"]
    assert next(a for a in agents if a["code"] == "reporting")["month_spend_usd"] >= 0.25
    for bad in ("2026-13", "2026-1", "abc"):
        r = await api.call("GET", "/ai/usage", "ADM", params={"period": bad})
        assert r.status_code == 400, bad
    r = await api.call("GET", "/ai/usage", "ADM", params={"period": "2020-01", "group_by": "agent"})
    assert r.status_code == 200 and r.json()["data"]["rows"] == []
    assert r.json()["data"]["period"] == "2020-01-01"

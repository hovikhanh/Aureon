"""T-645b / TC-M16-18 — chat WRITE tools → `ActionService.propose()` (10 §7.2.5 EP-AI-01/02).

"Tạo task cho …" → `suggested_actions[0]` = L2 `proposed` card; an L1 policy → suggestion only
(no `ai_actions` row); kill switch `L0` → no card, `ToolCallLog forbidden/AI_DISABLED`, warning
`ai.warn.kill_switch`; `WRITE_OFF` → the L2 card is still drafted and the asker may confirm it;
another user confirming → `403 FORBIDDEN_SCOPE`. Scripted gateway; rolled-back `db_session`.
"""

import json
import uuid
from typing import Any

import pytest
from sqlalchemy import func, select

from app.core.model_gateway.types import ChatRequest, ChatResponse, ToolCall, Usage
from app.modules.ai.models import AIAction, AutonomyPolicy, ToolCallLog
from app.modules.ai.schemas import KillSwitchIn
from app.modules.ai.services.kill_switch_service import KillSwitchService
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration

ASK = "Tạo task cho NV-0001: gọi lại khách hàng trước thứ Sáu"
ARGS = {"title": "Gọi lại khách hàng", "assignee_code": "NV-0001", "due_date": "2026-10-30"}


def _install(app: Any) -> None:
    from app.modules.ai.routes.router import get_chat_gateway

    class _GW:
        async def chat(self, req: ChatRequest) -> ChatResponse:
            if any(m.role == "tool" for m in req.messages):
                return ChatResponse(content="Đã soạn thẻ.", provider="f", model="x")
            call = ToolCall(id="c1", name="TOOL-create_task", arguments=ARGS)
            return ChatResponse(content="", provider="f", model="x", usage=Usage(3, 0),
                                tool_calls=(call,))  # fmt: skip

    app.dependency_overrides[get_chat_gateway] = lambda: _GW()


async def _ask(api: ApiClient, uid: uuid.UUID, path: str = "/ai/chat") -> Any:
    h = api.headers("CEO", user_id=uid, idem=True)
    return await api.http.post(f"/api/v1{path}", headers=h, json={"message": ASK})


async def _kill(db, mode: str) -> None:
    from app.core.deps import Principal
    from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

    adm = Principal(
        user_id=uuid.uuid4(), role="ADM", permissions=frozenset(ROLE_PERMISSIONS["ADM"])
    )
    await KillSwitchService(db).set(adm, KillSwitchIn(
        enabled=True, mode=mode, agents=[], reason="test"))  # fmt: skip


async def _cards(db) -> int:
    return int((await db.execute(select(func.count()).select_from(AIAction))).scalar_one())


async def test_chat_create_task_drafts_l2_card(api: ApiClient, db_session) -> None:
    _install(api.app)
    uid = uuid.uuid4()
    r = await _ask(api, uid)
    assert r.status_code == 200, r.text
    card = r.json()["data"]["suggested_actions"][0]
    assert (card["autonomy_level"], card["status"], card["action_name"]) == (
        "L2", "proposed", "ACT-create_task")  # fmt: skip
    assert card["tool_name"] == "TOOL-create_task" and card["on_behalf_of"] == str(uid)
    assert card["input_preview"]["title"] == ARGS["title"]
    log = (await db_session.execute(select(ToolCallLog).where(
        ToolCallLog.ai_action_id == uuid.UUID(card["id"])))).scalar_one()  # fmt: skip
    assert (log.status, log.autonomy_level) == ("ok", "L2")
    # the asker confirms; somebody else may not (FORBIDDEN_SCOPE)
    other = await api.http.post(f"/api/v1/ai/actions/{card['id']}/confirm", json={},
                                headers=api.headers("CEO", idem=True))  # fmt: skip
    assert other.status_code == 403 and other.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    ok = await api.http.post(f"/api/v1/ai/actions/{card['id']}/confirm", json={},
                             headers=api.headers("CEO", user_id=uid, idem=True))  # fmt: skip
    assert ok.status_code == 200 and ok.json()["data"]["status"] == "executed"


async def test_l1_policy_suggests_without_ai_action(api: ApiClient, db_session) -> None:
    db_session.add(
        AutonomyPolicy(
            action_name="ACT-create_task",
            tool_name="TOOL-create_task",
            level="L1",
            max_level="L2",
            is_active=True,
            reason="t",
        )
    )
    await db_session.flush()
    _install(api.app)
    before = await _cards(db_session)
    r = await _ask(api, uuid.uuid4())
    sug = r.json()["data"]["suggested_actions"]
    assert sug == [{"action_name": "ACT-create_task", "tool_name": "TOOL-create_task",
                    "autonomy_level": "L1", "input_preview": ARGS}]  # fmt: skip
    assert await _cards(db_session) == before


async def test_kill_switch_l0_refuses_write_with_warning(api: ApiClient, db_session) -> None:
    await _kill(db_session, "L0")
    _install(api.app)
    before = await _cards(db_session)
    rid = str(uuid.uuid4())
    h = api.headers("CEO", idem=True) | {"X-Request-Id": rid}
    r = await api.http.post("/api/v1/ai/chat", headers=h, json={"message": ASK})
    body = r.json()["data"]
    assert body["suggested_actions"] == [] and "ai.warn.kill_switch" in body["warnings"]
    assert await _cards(db_session) == before
    log = (await db_session.execute(select(ToolCallLog).where(
        ToolCallLog.request_id == uuid.UUID(rid)))).scalar_one()  # fmt: skip
    assert (log.status, log.error_code, log.autonomy_level) == ("forbidden", "AI_DISABLED", "L0")


async def test_write_off_still_drafts_confirmable_card(api: ApiClient, db_session) -> None:
    await _kill(db_session, "WRITE_OFF")
    _install(api.app)
    uid = uuid.uuid4()
    card = (await _ask(api, uid)).json()["data"]["suggested_actions"][0]
    assert (card["autonomy_level"], card["status"]) == ("L2", "proposed")
    ok = await api.http.post(f"/api/v1/ai/actions/{card['id']}/confirm", json={},
                             headers=api.headers("CEO", user_id=uid, idem=True))  # fmt: skip
    assert ok.json()["data"]["status"] == "executed"


async def test_sse_done_carries_suggested_actions(api: ApiClient, db_session) -> None:
    _install(api.app)
    r = await _ask(api, uuid.uuid4(), "/ai/chat/stream")
    assert r.status_code == 200
    events = [b for b in r.text.split("\n\n") if b.strip()]
    done = next(b for b in events if "event: done" in b)
    data = json.loads(done.split("data: ", 1)[1])
    assert data["suggested_actions"][0]["status"] == "proposed"
    names = {line.split(": ", 1)[1] for b in events for line in b.splitlines()
             if line.startswith("event: ")}  # fmt: skip
    assert names <= {"start", "thinking", "tool_call", "tool_result", "token", "done", "error"}


async def test_only_asker_rejects_or_undoes_admin_lists_tenant(api: ApiClient, db_session) -> None:
    """EP-AI-07/09..11: confirm/reject/undo only by `on_behalf_of` (403 FORBIDDEN_SCOPE);
    `ai:admin` lists the whole tenant + `agent_profile_code` filter; audit
    `ai.action_confirm` / `ai.action_reject` (10 §7.2.5)."""
    from app.core.audit import AUDIT_LOGS

    _install(api.app)
    uid = uuid.uuid4()
    card = (await _ask(api, uid)).json()["data"]["suggested_actions"][0]
    url = f"/api/v1/ai/actions/{card['id']}"
    for role, code in (("CEO", "FORBIDDEN_SCOPE"), ("ADM", "FORBIDDEN_ROLE")):  # ADM: no ai:write
        r = await api.http.post(f"{url}/reject", json={"reason": "x"},
                                headers=api.headers(role, idem=True))  # fmt: skip
        assert r.status_code == 403 and r.json()["error"]["code"] == code
    q = {"agent_profile_code": "ceo", "status": "proposed"}
    adm = await api.http.get("/api/v1/ai/actions", headers=api.headers("ADM"), params=q)
    assert card["id"] in {a["id"] for a in adm.json()["data"]}
    none = await api.http.get("/api/v1/ai/actions", headers=api.headers("ADM"),
                              params={"agent_profile_code": "task"})  # fmt: skip
    assert card["id"] not in {a["id"] for a in none.json()["data"]}
    assert (await api.http.get(url, headers=api.headers("ADM"))).status_code == 200
    assert (await api.http.get(url, headers=api.headers("MGR"))).status_code == 404
    mine = api.headers("CEO", user_id=uid, idem=True)
    assert (await api.http.post(f"{url}/confirm", json={}, headers=mine)).status_code == 200
    other = await api.http.post(f"{url}/undo", json={}, headers=api.headers("CEO", idem=True))
    assert other.status_code == 403 and other.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    undo = await api.http.post(f"{url}/undo", json={}, headers=api.headers("CEO", user_id=uid,
                                                                           idem=True))  # fmt: skip
    assert undo.status_code == 200 and undo.json()["data"]["status"] == "undone"
    acts = set((await db_session.execute(select(AUDIT_LOGS.c.action).where(
        AUDIT_LOGS.c.target_id == uuid.UUID(card["id"])))).scalars())  # fmt: skip
    assert {"ai.action_proposed", "ai.action_confirm", "ai.action_executed",
            "ai.action_undone"} <= acts  # fmt: skip

    card2 = (await _ask(api, uid)).json()["data"]["suggested_actions"][0]
    rej = await api.http.post(f"/api/v1/ai/actions/{card2['id']}/reject", json={"reason": "no"},
                              headers=api.headers("CEO", user_id=uid, idem=True))  # fmt: skip
    assert rej.status_code == 200 and rej.json()["data"]["status"] == "rejected"
    acts2 = set((await db_session.execute(select(AUDIT_LOGS.c.action).where(
        AUDIT_LOGS.c.target_id == uuid.UUID(card2["id"])))).scalars())  # fmt: skip
    assert "ai.action_reject" in acts2

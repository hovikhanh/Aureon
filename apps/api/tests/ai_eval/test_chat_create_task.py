"""T-645b / TC-M16-18 (ai_eval) — "Tạo task cho …" through the real `ModelGateway` in fixture mode.

The gateway is built with `model_gateway_mode="fixture"` here (never the shell's mode) on
`tests/fixtures/model_gateway/chat_actions/<task>/<prompt_sha256>.json`; a prompt / tool-list
change breaks the key → `FixtureMissingError` (loud). The CEO agent's `allowed_tools` is pinned
in the rolled-back transaction so the advertised tool set (part of the key) is stable. Asserts:
the model's `TOOL-create_task` call becomes an L2 `proposed` card in `suggested_actions[0]`, no
task row is written before confirmation, and the tool message the model sees carries no id.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select, update

from app.core.config import ConfigService
from app.core.deps import Principal
from app.core.model_gateway import ChatRequest, ChatResponse, ModelGateway
from app.core.model_gateway.fixtures import FixtureStore
from app.modules.ai.models import AgentProfile, AIAction
from app.modules.ai.services import chat_service
from app.modules.ai.services.chat_service import ChatService
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "model_gateway" / "chat_actions"
ASK = "Tạo task cho NV-0001: gọi lại khách hàng ABC trước 30/10/2026"
TOOLS = ["TOOL-create_task", "TOOL-list_tasks"]


class SpyGateway:
    def __init__(self) -> None:
        cfg = ConfigService(model_gateway_mode="fixture", ai_monthly_budget_usd=0)
        self.inner = ModelGateway(cfg=cfg, fixtures=FixtureStore(FIXTURES))
        self.requests: list[ChatRequest] = []

    async def chat(self, req: ChatRequest) -> ChatResponse:
        self.requests.append(req)
        return await self.inner.chat(req)


async def test_create_task_prompt_drafts_l2_card(db_session, monkeypatch) -> None:
    monkeypatch.setattr(chat_service, "replay_enabled", lambda _cfg: False)
    await db_session.execute(update(AgentProfile).where(AgentProfile.code == "ceo")
                             .values(allowed_tools=TOOLS, is_enabled=True))  # fmt: skip
    ceo = Principal(user_id=uuid.uuid4(), role="CEO",
                    permissions=frozenset(ROLE_PERMISSIONS["CEO"]))  # fmt: skip
    gw = SpyGateway()
    turn = await ChatService(db_session, gw).chat(ceo, ASK)

    card = turn.suggested_actions[0]
    assert (card["autonomy_level"], card["status"], card["action_name"]) == (
        "L2", "proposed", "ACT-create_task")  # fmt: skip
    assert card["input_preview"]["assignee_code"] == "NV-0001"
    assert turn.answer and turn.warnings == []
    row = (await db_session.execute(select(AIAction).where(
        AIAction.id == uuid.UUID(card["id"])))).scalar_one()  # fmt: skip
    assert row.result_refs is None  # nothing written before the human confirms
    assert {t.name for t in gw.requests[0].tools} == set(TOOLS)
    tool_msg = next(m for m in gw.requests[-1].messages if m.role == "tool")
    assert card["id"] not in tool_msg.content and "<<<DATA" in tool_msg.content
    n = (await db_session.execute(select(func.count()).select_from(AIAction).where(
        AIAction.message_id == row.message_id))).scalar_one()  # fmt: skip
    assert n == 1

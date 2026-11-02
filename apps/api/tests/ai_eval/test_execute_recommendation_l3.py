"""M3.2 ai-eval AUT-* (T-816, R-DEC-126/127) — Autonomy L3: a recommendation the CEO agent acts on.

A `ScriptedGateway` drives the tool-calling loop deterministically (no provider, no fixture file —
same pattern as `test_chat_grounding_routing_m24.py`): the first reply calls
`TOOL-execute_recommendation`, the second is the model's answer. The `ceo` agent seeds at
`max_autonomy_level=L3` and the system ceiling is L3 (M3.2), so the tool call **auto-executes** the
composite `ACT-execute_recommendation` (task + internal calendar event + notification) in one
transaction with a 24h undo window — the "AI đã làm" path — instead of drafting an L2 card. Tools
run against the seeded dev DB inside the rolled-back `db_session`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.core.deps import Principal
from app.core.model_gateway.types import ChatRequest, ChatResponse, ToolCall, Usage
from app.modules.ai.models import AgentProfile, AIAction
from app.modules.ai.services.chat_service import ChatService
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.execution.models import CalendarEvent, Task

pytestmark = pytest.mark.integration


def ceo() -> Principal:
    return Principal(
        user_id=uuid.uuid4(), role="CEO", permissions=frozenset(ROLE_PERMISSIONS["CEO"]),
        email="ceo@abc.test",
    )  # fmt: skip


class ScriptedGateway:
    def __init__(self, *responses: ChatResponse) -> None:
        self._responses = list(responses)
        self.requests: list[ChatRequest] = []

    async def chat(self, req: ChatRequest) -> ChatResponse:
        self.requests.append(req)
        return (
            self._responses.pop(0)
            if self._responses
            else ChatResponse(content="(no more)", provider="fixture", model="x")
        )


def _tool_then(tool: str, answer: str, args: dict | None = None) -> ScriptedGateway:
    first = ChatResponse(
        content="", provider="fixture", model="x",
        tool_calls=(ToolCall(id="c1", name=tool, arguments=args or {}),), usage=Usage(10, 0),
    )  # fmt: skip
    return ScriptedGateway(
        first, ChatResponse(content=answer, provider="fixture", model="x", usage=Usage(5, 20))
    )


async def _enable(db) -> None:
    await db.execute(
        update(AgentProfile).where(AgentProfile.code == "ceo")
        .values(allowed_tools=["TOOL-execute_recommendation"], is_enabled=True,
                max_autonomy_level="L3")
    )  # fmt: skip


async def test_aut01_recommendation_auto_executes_at_l3_with_undo(db_session) -> None:
    await _enable(db_session)
    due = "2026-11-10"
    gw = _tool_then(
        "TOOL-execute_recommendation",
        'Đã tạo việc "Gọi lại khách hàng ABC" và đặt lịch — có thể hoàn tác.',
        args={"title": "Gọi lại khách hàng ABC", "assignee_code": "NV-0001", "due_date": due},
    )
    turn = await ChatService(db_session, gw).chat(
        ceo(), "Làm theo khuyến nghị: giao NV-0001 gọi lại khách ABC trước 10/11/2026", locale="vi"
    )

    card = turn.suggested_actions[0]
    assert (card["autonomy_level"], card["status"], card["action_name"]) == (
        "L3", "executed", "ACT-execute_recommendation")  # fmt: skip
    row = (await db_session.execute(
        select(AIAction).where(AIAction.id == uuid.UUID(card["id"])))).scalar_one()  # fmt: skip
    # three effects written in one transaction, task + calendar refs exposed
    tables = {r["table"] for r in (row.result_refs or [])}
    assert {"execution.tasks", "execution.calendar_events", "platform.notifications"} <= tables
    assert row.undo_deadline and row.undo_deadline - datetime.now(UTC) > timedelta(hours=23)
    # the real task + internal calendar event exist and are linked
    task_ref = next(r for r in row.result_refs if r["table"] == "execution.tasks")
    task = (await db_session.execute(
        select(Task).where(Task.id == uuid.UUID(task_ref["id"])))).scalar_one()  # fmt: skip
    assert task.task_source == "ai"
    # Two internal events are linked to the task, each with a distinct owner (M3.1 + M3.2):
    #   · the composite's own event for the caller (`event_ref` below, undone by the action), and
    #   · the M3.1 `_sync_deadline_event` deadline mirror owned by the assignee (R-DEC-122).
    events = (await db_session.execute(select(CalendarEvent)
              .where(CalendarEvent.task_id == task.id))).scalars().all()  # fmt: skip
    event_ref = next(r for r in row.result_refs if r["table"] == "execution.calendar_events")
    caller_event = next(e for e in events if e.id == uuid.UUID(event_ref["id"]))
    mirror = next(e for e in events if e.id != caller_event.id)
    assert caller_event.owner_id == row.on_behalf_of  # the CEO who acted
    assert mirror.owner_id == task.assignee_id and mirror.title.startswith("Hạn:")  # NV-0001


async def test_aut02_recommendation_is_undoable_within_window(db_session) -> None:
    await _enable(db_session)
    gw = _tool_then(
        "TOOL-execute_recommendation",
        "Đã làm.",
        args={"title": "Chuẩn bị báo cáo quý", "due_date": "2026-11-12"},
    )
    user = ceo()  # same principal must ask and undo — only the asker decides the card (TC-M16-18)
    turn = await ChatService(db_session, gw).chat(user, "Làm giúp việc này", locale="vi")
    card = turn.suggested_actions[0]
    from app.modules.ai.services.action_service import ActionService

    out = await ActionService(db_session).undo(user, uuid.UUID(card["id"]))
    assert out.status == "undone"
    task_ref = next(r for r in card["result_refs"] if r["table"] == "execution.tasks")
    task = (await db_session.execute(
        select(Task).where(Task.id == uuid.UUID(task_ref["id"])))).scalar_one()  # fmt: skip
    assert task.deleted_at is not None  # undo soft-deleted the task

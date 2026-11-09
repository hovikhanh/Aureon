"""HTTP routes for `ai` — EP-110 chat, EP-111 SSE stream, EP-112 conversations, EP-119 tools.

Chat uses the asker's JWT for every tool call (P06). A SECRET-classified prompt (salary term)
makes the gateway raise `SecretDataBlockedError` → the turn is refused with `423 AI_DISABLED`
(no LLM is ever called — T-309). When the local model cannot answer a CONFIDENTIAL turn the gateway
raises `TemplateRequired`, answered as `AI_PROVIDER_ERROR` with `reason=local_model_unavailable`,
never as an unhandled 500 (F-M2).

The SSE endpoint emits the canonical event order
`start → (tool_call → tool_result)* → token* → done | error` (10 §6) with `X-Accel-Buffering: no`.
D-19: on a live turn the events are sent as they happen — `start` first, each tool as it runs,
then the answer text sentence by sentence, each sentence grounded before it is sent (never a
number the final grounding would remove). `done.answer` is the authoritative grounded text. A
replay turn or a gateway without `stream` is still delivered after the turn has finished.
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from collections.abc import AsyncIterator
from datetime import date
from typing import Annotated, Any, Literal

from fastapi import Depends, Response
from fastapi.responses import StreamingResponse

from app.core.config import get_config
from app.core.deps import DbSession, Principal, require_permission
from app.core.errors import AppError, ai_error
from app.core.idempotency import Idem
from app.core.model_gateway.errors import SecretDataBlockedError, TemplateRequired
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.ai.routes.acceptance import router as acceptance_router
from app.modules.ai.routes.admin import router as admin_router
from app.modules.ai.schemas import (
    AIActionOut,
    AIEvaluationOut,
    BriefingOut,
    ChatAnswerOut,
    ChatRequestIn,
    ConfirmActionIn,
    ConversationOut,
    CostSummaryOut,
    InsightOut,
    KillSwitchIn,
    KillSwitchOut,
    MessageOut,
    RejectActionIn,
    ToolOut,
    UndoActionIn,
)
from app.modules.ai.services import tool_catalog
from app.modules.ai.services.action_service import ActionService
from app.modules.ai.services.ai_service import AiService
from app.modules.ai.services.briefing_service import BriefingService
from app.modules.ai.services.chat_service import ChatService, ChatTurnResult
from app.modules.ai.services.conversation_service import ConversationService
from app.modules.ai.services.cost_service import CostService, period_window
from app.modules.ai.services.evaluation_service import EvaluationService
from app.modules.ai.services.insight_service import InsightService
from app.modules.ai.services.kill_switch_service import KillSwitchService

router = EnvelopeRouter(prefix="/ai", tags=["ai"])
_warmups: set[asyncio.Task[Any]] = set()


async def _warm_local_model() -> None:
    """D-19: load the local chat model in the background when the API starts (`keep_alive`
    then keeps it in RAM). Never blocks or fails startup; a no-op in fixture mode."""
    if not get_config().ai_warmup_on_start:
        return
    from app.core.model_gateway import ModelGateway

    task = asyncio.ensure_future(ModelGateway().warm("chat"))
    _warmups.add(task)
    task.add_done_callback(_warmups.discard)


router.add_event_handler("startup", _warm_local_model)

AiUser = Annotated[Principal, Depends(require_permission("ai", "query"))]
AiWriter = Annotated[Principal, Depends(require_permission("ai", "write"))]
AiAdmin = Annotated[Principal, Depends(require_permission("ai", "admin"))]


def get_chat_gateway(db: DbSession) -> Any:
    """The ModelGateway for a chat turn, bound to this session's call log. Overridable in tests
    (`app.dependency_overrides[get_chat_gateway]`) so the HTTP path runs without a provider."""
    return AiService(db).gateway()


ChatGateway = Annotated[Any, Depends(get_chat_gateway)]


def _no_local_model(exc: TemplateRequired) -> AppError:
    return ai_error(
        "AI_PROVIDER_ERROR", "Mô hình nội bộ chưa sẵn sàng; dữ liệu mật không được gửi ra ngoài.",
        reason="local_model_unavailable", classification=exc.classification,
    )  # fmt: skip


def _turn_payload(turn: ChatTurnResult) -> dict[str, Any]:
    return {
        "conversation_id": str(turn.conversation_id),
        "message_id": str(turn.message_id),
        "answer": turn.answer,
        "sources": [s.as_dict() for s in turn.sources],
        "function_calls": turn.function_calls,
        "suggested_actions": turn.suggested_actions,
        "truncated": turn.truncated,
        "warnings": turn.warnings,
        "mode": turn.mode,
    }


@router.post("/chat", response_model=ChatAnswerOut, summary="EP-AI-01 AI chat (sync)")
async def chat(
    body: ChatRequestIn, user: AiUser, db: DbSession, gateway: ChatGateway, idem: Idem
) -> ChatAnswerOut:
    svc = ChatService(db, gateway)
    try:
        turn = await svc.chat(
            user, body.message, conversation_id=body.conversation_id, locale=body.locale
        )
    except SecretDataBlockedError as exc:
        raise ai_error(
            "AI_DISABLED", "Yêu cầu chứa dữ liệu nhạy cảm (lương) — trợ lý AI không xử lý."
        ) from exc
    except TemplateRequired as exc:
        raise _no_local_model(exc) from exc
    await db.commit()
    return ChatAnswerOut.model_validate(_turn_payload(turn))


@router.post("/chat/stream", summary="EP-AI-02 AI chat (SSE)", response_class=Response)
async def chat_stream(
    body: ChatRequestIn, user: AiUser, db: DbSession, gateway: ChatGateway, idem: Idem
) -> StreamingResponse:
    svc = ChatService(db, gateway)

    async def gen() -> AsyncIterator[bytes]:
        eid = 0
        started = False

        def ev(event: str, data: dict[str, Any]) -> bytes:
            nonlocal eid, started
            eid += 1
            started = started or event == "start"
            return (
                f"id: {eid}\nevent: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            ).encode()

        def fail(code: str, message: str, details: Any = None) -> list[bytes]:
            out = [] if started else [ev("start", {"conversation_id": None, "message_id": None})]
            data: dict[str, Any] = {"code": code, "message": message}
            if details is not None:
                data["details"] = details
            return [*out, ev("error", data)]

        # D-19: the turn runs as a task and reports `start`, each tool and the grounded answer
        # text as they happen — the UI shows progress while a CPU-bound local model works.
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()

        async def on_event(event: str, data: dict[str, Any]) -> None:
            await queue.put((event, data))

        task = asyncio.ensure_future(svc.chat(
            user, body.message, conversation_id=body.conversation_id, locale=body.locale,
            on_event=on_event,
        ))  # fmt: skip
        try:
            while not task.done() or not queue.empty():
                getter = asyncio.ensure_future(queue.get())
                await asyncio.wait({getter, task}, return_when=asyncio.FIRST_COMPLETED)
                if getter.done():
                    yield ev(*getter.result())
                else:
                    getter.cancel()
            turn = task.result()
        except SecretDataBlockedError:
            for b in fail("AI_DISABLED", "Yêu cầu chứa dữ liệu nhạy cảm (lương) — không xử lý."):
                yield b
            return
        except TemplateRequired as exc:
            await db.rollback()
            err = _no_local_model(exc)
            for b in fail(err.code, str(err), err.details):
                yield b
            return
        except AppError as exc:
            # The 200 + headers are already on the wire, so an error raised by the turn (provider
            # chain down → AI_PROVIDER_ERROR, quota, timeout…) must end the stream as the `error`
            # event of 10 §6 — re-raising here cut the stream mid-flight ("response already
            # started") and the client saw a dropped connection instead of the reason.
            await db.rollback()
            for b in fail(exc.code, str(exc)):
                yield b
            return
        finally:
            if not task.done():  # client went away: stop the turn (no half-written answer)
                task.cancel()
        await db.commit()
        if not turn.streamed:  # replay / a gateway without `stream`: deliver the finished turn
            yield ev("start", {
                "conversation_id": str(turn.conversation_id),
                "message_id": str(turn.message_id),
                "model_route": {"task": "chat"},
                "mode": turn.mode,
            })  # fmt: skip
            for fc in turn.function_calls:
                yield ev("tool_call", {"call_id": fc["tool"], "tool": fc["tool"]})
                yield ev("tool_result", {
                    "call_id": fc["tool"], "tool": fc["tool"],
                    "status": fc["status"], "latency_ms": fc["latency_ms"],
                    "sources": [s.as_dict() for s in turn.sources],
                })  # fmt: skip
            if turn.replayed:
                # demo replay (DEC-241): word-sized tokens at a fixed pace; `mode: "replay"`
                delay = get_config().ai_demo_token_delay_sec
                for word in _words(turn.answer):
                    yield ev("token", {"delta": word})
                    if delay:
                        await asyncio.sleep(delay)
            else:
                for chunk in _chunks(turn.answer):
                    yield ev("token", {"delta": chunk})
        yield ev("done", {
            "message_id": str(turn.message_id),
            "answer": turn.answer,
            "sources": [s.as_dict() for s in turn.sources],
            "function_calls": turn.function_calls,
            "suggested_actions": turn.suggested_actions,
            "truncated": turn.truncated,
            "warnings": turn.warnings,
            "usage": {"tokens_in": turn.tokens_in, "tokens_out": turn.tokens_out},
            "mode": turn.mode,
        })  # fmt: skip

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations", response_model=list[ConversationOut], summary="EP-AI-03 Chats")
async def list_conversations(user: AiUser, db: DbSession) -> list[ConversationOut]:
    return await ConversationService(db).list_for_user(user)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageOut], summary="EP-AI-04 Messages",
)  # fmt: skip
async def list_messages(
    conversation_id: uuid.UUID, user: AiUser, db: DbSession
) -> list[MessageOut]:
    return await ConversationService(db).messages(user, conversation_id)


@router.get("/insights", response_model=list[InsightOut], summary="EP-AI-05 Insights")
async def list_insights(
    user: AiUser,
    db: DbSession,
    pillar: str | None = None,
    kind: str | None = None,
    severity: str | None = None,
) -> list[InsightOut]:
    return await InsightService(db).list_for(user, pillar=pillar, kind=kind, severity=severity)


@router.post(
    "/insights/{insight_id}/dismiss", response_model=InsightOut, summary="EP-AI-06 Dismiss insight"
)
async def dismiss_insight(
    insight_id: uuid.UUID, user: AiUser, db: DbSession, idem: Idem
) -> InsightOut:
    out = await InsightService(db).dismiss(user, insight_id)
    await db.commit()
    return out


@router.get("/actions", response_model=list[AIActionOut], summary="EP-AI-07 AI actions")
async def list_actions(
    user: AiUser, db: DbSession, status: str | None = None, autonomy_level: str | None = None,
    agent_profile_code: str | None = None,
) -> list[AIActionOut]:  # fmt: skip
    return await ActionService(db).list_for(
        user, status=status, autonomy_level=autonomy_level, agent_profile_code=agent_profile_code
    )


@router.get("/actions/{action_id}", response_model=AIActionOut, summary="EP-AI-08 AI action")
async def get_action_ep(action_id: uuid.UUID, user: AiUser, db: DbSession) -> AIActionOut:
    return await ActionService(db).get(user, action_id)


@router.post("/actions/{action_id}/confirm", response_model=AIActionOut, summary="EP-AI-09 Confirm")
async def confirm_action(
    action_id: uuid.UUID, body: ConfirmActionIn, user: AiWriter, db: DbSession, idem: Idem
) -> AIActionOut:
    out = await ActionService(db).confirm(user, action_id, edited_input=body.edited_input)
    await db.commit()
    return out


@router.post("/actions/{action_id}/reject", response_model=AIActionOut, summary="EP-AI-10 Reject")
async def reject_action(
    action_id: uuid.UUID, body: RejectActionIn, user: AiWriter, db: DbSession, idem: Idem
) -> AIActionOut:
    out = await ActionService(db).reject(user, action_id, reason=body.reason)
    await db.commit()
    return out


@router.post("/actions/{action_id}/undo", response_model=AIActionOut, summary="EP-AI-11 Undo")
async def undo_action(
    action_id: uuid.UUID, body: UndoActionIn, user: AiWriter, db: DbSession, idem: Idem
) -> AIActionOut:
    out = await ActionService(db).undo(user, action_id, reason=body.reason)
    await db.commit()
    return out


@router.get("/briefings/today", response_model=BriefingOut, summary="EP-AI-24 Today's briefing")
async def briefing_today(user: AiUser, db: DbSession) -> BriefingOut:
    out = await BriefingService(db).today(user)  # generate-if-missing (idempotent)
    await db.commit()
    return out


@router.get("/briefings", response_model=list[BriefingOut], summary="EP-AI-25 Briefing history")
async def list_briefings(
    user: AiUser, db: DbSession,
    page: Annotated[PageParams, Depends(page_params("briefing_date"))],
    date_from: date | None = None, date_to: date | None = None,
) -> Any:  # fmt: skip
    return await BriefingService(db).history(
        user, page, date_from=date_from, date_to=date_to
    )  # fmt: skip


@router.post("/briefings/{briefing_id}/open", response_model=BriefingOut, summary="EP-AI-26 Open")
async def open_briefing(
    briefing_id: uuid.UUID, user: AiUser, db: DbSession, idem: Idem
) -> BriefingOut:
    out = await BriefingService(db).mark_opened(user, briefing_id)  # G1 tracking
    await db.commit()
    return out


@router.get(
    "/evaluations", response_model=list[AIEvaluationOut], summary="EP-AI-27 Evaluation runs"
)
async def list_evaluations(
    admin: AiAdmin, db: DbSession,
    page: Annotated[PageParams, Depends(page_params("finished_at"))],
    suite: str | None = None, model: str | None = None, provider: str | None = None,
) -> Any:  # fmt: skip
    return await EvaluationService(db).list_runs(
        admin, suite=suite, model=model, provider=provider, limit=page.limit, offset=page.offset
    )


@router.get(
    "/evaluations/{evaluation_id}",
    response_model=AIEvaluationOut,
    summary="EP-AI-28 Evaluation run",
)
async def get_evaluation(
    evaluation_id: uuid.UUID, admin: AiAdmin, db: DbSession
) -> AIEvaluationOut:
    return await EvaluationService(db).get(admin, evaluation_id)


@router.get("/kill-switch", response_model=KillSwitchOut, summary="EP-AI-12 Kill switch status")
async def kill_switch_status(user: AiUser, db: DbSession) -> KillSwitchOut:
    return await KillSwitchService(db).status()


@router.put("/kill-switch", response_model=KillSwitchOut, summary="EP-AI-13 Set kill switch")
async def set_kill_switch(
    body: KillSwitchIn, admin: AiAdmin, db: DbSession, idem: Idem
) -> KillSwitchOut:
    out = await KillSwitchService(db).set(admin, body)
    await db.commit()
    return out


@router.get("/tools", response_model=list[ToolOut], summary="EP-AI-14 Tool Registry")
async def list_tools(
    user: AiUser,
    db: DbSession,
    kind: Literal["READ", "WRITE", "APPROVAL", "EXECUTION"] | None = None,
    domain: str | None = None,
    agent: str | None = None,
    available_only: bool = False,
) -> list[ToolOut]:
    return await tool_catalog.list_tools(
        db, user, kind=kind, domain=domain, agent=agent, available_only=available_only
    )


@router.get("/usage", response_model=CostSummaryOut, summary="EP-AI-15 AI usage & cost")
async def ai_usage(
    admin: AiAdmin,
    db: DbSession,
    group_by: Literal["provider", "model", "task_kind", "user", "agent"] = "provider",
    period: str | None = None,
) -> CostSummaryOut:
    start, end = period_window(period)
    return await CostService(db).usage(group_by=group_by, start=start, end=end)


def _words(text: str) -> list[str]:
    return re.findall(r"\S+\s*", text) or [""]


def _chunks(text: str, size: int = 48) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


# M1.6 bước C: AI Control Center EP-AI-16..23 (`routes/admin.py`, 10 §7.2.5).
module_router = EnvelopeRouter()
module_router.include_router(router)
module_router.include_router(admin_router)
module_router.include_router(acceptance_router)  # EP-RPT-08 /reporting/acceptance (M3.5)

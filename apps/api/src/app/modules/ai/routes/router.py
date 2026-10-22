"""HTTP routes for `ai` — EP-110 chat, EP-111 SSE stream, EP-112 conversations, EP-119 tools.

Chat uses the asker's JWT for every tool call (P06). A SECRET-classified prompt (salary term)
makes the gateway raise `SecretDataBlockedError` → the turn is refused with `423 AI_DISABLED`
(no LLM is ever called — T-309). The SSE endpoint streams the canonical event order
`start → (thinking | tool_call → tool_result)* → token* → done | error` (10 §6) with
`X-Accel-Buffering: no` so no proxy buffers it.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import Depends, Response
from fastapi.responses import StreamingResponse

from app.core.deps import DbSession, Principal, require_permission
from app.core.errors import ai_error
from app.core.idempotency import Idem
from app.core.model_gateway.errors import SecretDataBlockedError
from app.core.routing import EnvelopeRouter
from app.modules.ai.schemas import (
    ChatAnswerOut,
    ChatRequestIn,
    ConversationOut,
    MessageOut,
    ToolOut,
)
from app.modules.ai.services.ai_service import AiService
from app.modules.ai.services.chat_service import ChatService, ChatTurnResult
from app.modules.ai.services.conversation_service import ConversationService
from app.modules.ai.tools import advertisable_for, all_tools, available_for

router = EnvelopeRouter(prefix="/ai", tags=["ai"])

AiUser = Annotated[Principal, Depends(require_permission("ai", "query"))]


def _turn_payload(turn: ChatTurnResult) -> dict[str, Any]:
    return {
        "conversation_id": str(turn.conversation_id),
        "message_id": str(turn.message_id),
        "answer": turn.answer,
        "sources": [s.as_dict() for s in turn.sources],
        "function_calls": turn.function_calls,
        "suggested_actions": [],
        "truncated": turn.truncated,
        "warnings": turn.warnings,
    }


@router.post("/chat", response_model=ChatAnswerOut, summary="EP-110 AI chat (sync)")
async def chat(body: ChatRequestIn, user: AiUser, db: DbSession, idem: Idem) -> ChatAnswerOut:
    svc = ChatService(db, AiService(db).gateway())
    try:
        turn = await svc.chat(
            user, body.message, conversation_id=body.conversation_id, locale=body.locale
        )
    except SecretDataBlockedError as exc:
        raise ai_error(
            "AI_DISABLED", "Yêu cầu chứa dữ liệu nhạy cảm (lương) — trợ lý AI không xử lý."
        ) from exc
    await db.commit()
    return ChatAnswerOut.model_validate(_turn_payload(turn))


@router.post("/chat/stream", summary="EP-111 AI chat (SSE)", response_class=Response)
async def chat_stream(
    body: ChatRequestIn, user: AiUser, db: DbSession, idem: Idem
) -> StreamingResponse:
    svc = ChatService(db, AiService(db).gateway())

    async def gen() -> AsyncIterator[bytes]:
        eid = 0

        def ev(event: str, data: dict[str, Any]) -> bytes:
            nonlocal eid
            eid += 1
            return (
                f"id: {eid}\nevent: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            ).encode()

        try:
            turn = await svc.chat(
                user, body.message, conversation_id=body.conversation_id, locale=body.locale
            )
        except SecretDataBlockedError:
            yield ev("start", {"conversation_id": None, "message_id": None})
            yield ev("error", {
                "code": "AI_DISABLED",
                "message": "Yêu cầu chứa dữ liệu nhạy cảm (lương) — không xử lý.",
            })  # fmt: skip
            return
        await db.commit()
        yield ev("start", {
            "conversation_id": str(turn.conversation_id),
            "message_id": str(turn.message_id),
            "model_route": {"task": "chat"},
        })  # fmt: skip
        for fc in turn.function_calls:
            yield ev("tool_call", {"call_id": fc["tool"], "tool": fc["tool"]})
            yield ev("tool_result", {
                "call_id": fc["tool"], "tool": fc["tool"],
                "status": fc["status"], "latency_ms": fc["latency_ms"],
                "sources": [s.as_dict() for s in turn.sources],
            })  # fmt: skip
        for chunk in _chunks(turn.answer):
            yield ev("token", {"delta": chunk})
        yield ev("done", {
            "message_id": str(turn.message_id),
            "answer": turn.answer,
            "sources": [s.as_dict() for s in turn.sources],
            "function_calls": turn.function_calls,
            "suggested_actions": [],
            "truncated": turn.truncated,
            "warnings": turn.warnings,
            "usage": {"tokens_in": turn.tokens_in, "tokens_out": turn.tokens_out},
        })  # fmt: skip

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations", response_model=list[ConversationOut], summary="EP-112 Conversations")
async def list_conversations(user: AiUser, db: DbSession) -> list[ConversationOut]:
    return await ConversationService(db).list_for_user(user)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageOut], summary="EP-112 Messages",
)  # fmt: skip
async def list_messages(
    conversation_id: uuid.UUID, user: AiUser, db: DbSession
) -> list[MessageOut]:
    return await ConversationService(db).messages(user, conversation_id)


@router.get("/tools", response_model=list[ToolOut], summary="EP-119 Tools")
async def list_tools(user: AiUser) -> list[ToolOut]:
    advertised = {t.name for t in advertisable_for(user.permissions)}
    avail = {t.name for t in available_for(user.permissions)}
    return [
        ToolOut(
            name=t.name,
            kind=t.kind,
            autonomy_default=t.autonomy_default,
            available=t.name in avail and t.name in advertised,
            data_scope=t.data_scope,
            classification=t.classification,
            reversible=t.reversible_label,
            cost_estimate=t.cost_estimate,
        )
        for t in all_tools()
    ]


def _chunks(text: str, size: int = 48) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]

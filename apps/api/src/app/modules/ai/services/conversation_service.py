"""Conversation + message reads (EP-112). A conversation owned by another user → 404 (the row
is simply filtered by `user_id`, so it does not leak existence)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import NotFoundError
from app.modules.ai.models import Conversation, Message
from app.modules.ai.schemas import ConversationOut, MessageOut


class ConversationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_user(self, user: Principal) -> list[ConversationOut]:
        rows = (
            await self.db.execute(
                select(Conversation)
                .where(
                    Conversation.user_id == user.user_id,
                    Conversation.deleted_at.is_(None),
                )
                .order_by(Conversation.last_message_at.desc().nullslast())
            )
        ).scalars()
        return [
            ConversationOut(id=c.id, title=c.title, last_message_at=c.last_message_at) for c in rows
        ]

    async def messages(self, user: Principal, conversation_id: uuid.UUID) -> list[MessageOut]:
        conv = (
            await self.db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user.user_id,
                    Conversation.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if conv is None:
            raise NotFoundError("conversation not found")
        rows = (
            await self.db.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
            )
        ).scalars()
        return [
            MessageOut(
                id=m.id,
                sender=m.sender,
                content=m.content,
                sources=m.sources or [],
                function_calls=m.function_calls or [],
                truncated=m.truncated,
                created_at=m.created_at,
            )
            for m in rows
        ]

"""EP-AI-22/23 — tool & model call logs for the AI Control Center (T-647, R-DEC-74).

Read-only over append-only tables. Window `from`/`to` (ISO 8601 UTC) defaults to the last 7
days; `from > to` → `400`. Never exposes a raw prompt (only `prompt_sha256` is stored).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import Page
from app.core.errors import BadRequestError
from app.core.pagination import PageParams
from app.modules.ai.models import ModelCallLog, ToolCallLog
from app.modules.ai.repositories import CallLogQueryRepository
from app.modules.ai.schemas.admin import ModelCallLogOut, ToolCallLogOut

DEFAULT_WINDOW = timedelta(days=7)
_MICRO = 1_000_000


def window(start: datetime | None, end: datetime | None) -> tuple[datetime, datetime]:
    end = end or datetime.now(UTC)
    start = start or end - DEFAULT_WINDOW
    if start > end:
        raise BadRequestError("from must be <= to", details={"param": "from"})
    return start, end


def _rid(value: str | None) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise BadRequestError("request_id must be a UUID", details={"param": "request_id"}) from exc


def _s(value: uuid.UUID | None) -> str | None:
    return str(value) if value else None


class CallLogService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = CallLogQueryRepository(db)

    async def tool_calls(
        self, page: PageParams, *, start: datetime | None, end: datetime | None,
        request_id: str | None = None, **filters: Any,
    ) -> Page[ToolCallLogOut]:  # fmt: skip
        lo, hi = window(start, end)
        rows, total = await self.repo.page(
            ToolCallLog, filters=filters | {"request_id": _rid(request_id)}, start=lo, end=hi,
            sort_by=page.sort_by, order=page.order, limit=page.limit, offset=page.offset,
        )  # fmt: skip
        items = [
            ToolCallLogOut(
                id=r.id,
                created_at=r.created_at,
                request_id=_s(r.request_id),
                user_id=r.user_id,
                agent_profile_code=r.agent_profile_code,
                tool_name=r.tool_name,
                tool_kind=r.tool_kind,
                status=r.status,
                error_code=r.error_code,
                latency_ms=r.latency_ms,
                autonomy_level=r.autonomy_level,
                ai_action_id=r.ai_action_id,
                message_id=r.message_id,
                arguments=dict(r.arguments or {}),
                result_refs=list(r.result_refs or []),
            )
            for r in rows
        ]
        return Page(items=items, total=total, limit=page.limit, offset=page.offset)

    async def model_calls(
        self, page: PageParams, *, start: datetime | None, end: datetime | None,
        request_id: str | None = None, **filters: Any,
    ) -> Page[ModelCallLogOut]:  # fmt: skip
        lo, hi = window(start, end)
        rows, total = await self.repo.page(
            ModelCallLog, filters=filters | {"request_id": _rid(request_id)}, start=lo, end=hi,
            sort_by=page.sort_by, order=page.order, limit=page.limit, offset=page.offset,
        )  # fmt: skip
        items = [
            ModelCallLogOut(
                id=r.id,
                created_at=r.created_at,
                request_id=_s(r.request_id),
                caller_module=r.caller_module,
                task_kind=r.task_kind,
                provider=r.provider,
                model=r.model,
                fallback_from=r.fallback_from,
                agent_profile_code=r.agent_profile_code,
                user_id=r.user_id,
                tokens_in=r.tokens_in,
                tokens_out=r.tokens_out,
                cost_usd=r.estimated_cost_micro_usd / _MICRO,
                latency_ms=r.latency_ms,
                status=r.status,
                error_code=r.error_code,
                prompt_sha256=r.prompt_sha256,
            )
            for r in rows
        ]
        return Page(items=items, total=total, limit=page.limit, offset=page.offset)

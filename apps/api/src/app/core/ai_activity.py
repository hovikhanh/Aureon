"""Executive "AI đã làm" feed registry (M2.1, R-DEC-84).

`dashboard` reporting cần tóm tắt AI action gần đây nhưng KHÔNG được import `ai`
(`ai → dashboard` đã tồn tại, DEC-125). `ai` đăng ký provider ở package init — cùng mẫu
`core/org_scope.register_subtree_provider`. Không có provider → feed rỗng (count 0).
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class AiActionBrief:
    """Tóm tắt một AI action đã thực thi (neutral DTO, không lộ model `ai`)."""

    id: uuid.UUID
    action_name: str
    status: str
    executed_at: datetime | None = None
    result_refs: list[dict[str, Any]] = field(default_factory=list)


# (db, on_behalf_of, limit) -> (recent executed briefs, total executed count)
AiActivityProvider = Callable[
    [AsyncSession, uuid.UUID, int], Awaitable[tuple[list[AiActionBrief], int]]
]

_PROVIDER: list[AiActivityProvider] = []


def register_ai_activity_provider(provider: AiActivityProvider) -> None:
    """Install the provider (re-registration replaces it — idempotent on re-import)."""
    _PROVIDER[:] = [provider]


async def recent_ai_actions(
    db: AsyncSession, on_behalf_of: uuid.UUID, limit: int = 5
) -> tuple[list[AiActionBrief], int]:
    """Recent executed AI actions for `on_behalf_of` + total; empty when no provider."""
    if not _PROVIDER:
        return [], 0
    return await _PROVIDER[0](db, on_behalf_of, limit)

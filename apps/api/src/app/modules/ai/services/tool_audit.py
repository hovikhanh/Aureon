"""Tool-call audit (T-647, R-DEC-74, 05 §2.8 ENT-ToolCallLog) — one writer for every call site.

Chat (EP-AI-01), SSE (EP-AI-02, same `ChatService`), demo replay and `ActionService.propose`
all log through `log_tool_call`, so each row carries `tenant_id`, `request_id`
(`X-Request-Id`), `user_id` (the person served), `tool_kind`, the **effective** autonomy level,
`error_code`, compact `result_refs` and the WRITE card link `ai_action_id`.

`arguments` pass the LLM PII filter before storage (level 4 dropped, level 3 → `EMP-`/`CLI-`
codes): structured values via `strip_for_model`, every remaining string via
`scrub_for_model`. `result_refs` keep only `{type, id, label}` — never raw values.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.field_policy import strip_for_model
from app.core.request_context import current_request_id
from app.core.tenant import current_tenant
from app.modules.ai.models import ToolCallLog
from app.modules.ai.services.prompt_guard import scrub_for_model
from app.modules.ai.tools import tool_kind

_CLIENT_KEYS = ("contacts", "contact", "client", "clients", "customer", "customers")


def scrub_arguments(arguments: Any) -> Any:
    """PII-safe copy of tool arguments for the log (05 §2.8 `arguments`)."""
    return _scrub_strings(strip_for_model(arguments, client_keys=_CLIENT_KEYS))


def _scrub_strings(value: Any) -> Any:
    if isinstance(value, str):
        return scrub_for_model(value)
    if isinstance(value, dict):
        return {k: _scrub_strings(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_scrub_strings(v) for v in value]
    return value


def compact_refs(refs: Iterable[Any]) -> list[dict[str, Any]]:
    """`SourceRef[]` / result refs → `{type, id, label}` only."""
    out: list[dict[str, Any]] = []
    for r in refs:
        d = r.as_dict() if hasattr(r, "as_dict") else dict(r)
        out.append({"type": str(d.get("type") or d.get("table") or "record"),
                    "id": str(d.get("id", "")), "label": str(d.get("label", ""))})  # fmt: skip
    return out


def request_uuid() -> uuid.UUID | None:
    rid = current_request_id()
    try:
        return uuid.UUID(rid) if rid else None
    except ValueError:
        return None


async def log_tool_call(
    db: AsyncSession, *, tool_name: str, arguments: Any, status: str, latency_ms: int,
    agent_code: str, user_id: uuid.UUID | None, autonomy_level: str | None,
    message_id: uuid.UUID | None = None, error_code: str | None = None,
    result_refs: Iterable[Any] = (), ai_action_id: uuid.UUID | None = None,
    approval_request_id: uuid.UUID | None = None,
) -> ToolCallLog:  # fmt: skip
    row = ToolCallLog(
        tenant_id=current_tenant() or DEFAULT_TENANT_ID, request_id=request_uuid(),
        user_id=user_id, message_id=message_id, tool_name=tool_name,
        tool_kind=tool_kind(tool_name), arguments=scrub_arguments(arguments or {}),
        status=status, http_status=None, latency_ms=latency_ms, agent_profile_code=agent_code,
        autonomy_level=autonomy_level, error_code=error_code,
        result_refs=compact_refs(result_refs), ai_action_id=ai_action_id,
        approval_request_id=approval_request_id,
    )  # fmt: skip
    db.add(row)
    await db.flush()
    return row

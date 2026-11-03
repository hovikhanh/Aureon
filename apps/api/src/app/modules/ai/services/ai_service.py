"""Public service interface of `ai` — the only entry point for other modules."""

import logging
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.db import get_sessionmaker
from app.core.model_gateway import CallRecord, ModelGateway
from app.core.tenant import current_tenant
from app.modules.ai.models import ModelCallLog
from app.modules.ai.repositories import ModelCallLogRepository, month_start

log = logging.getLogger("app.ai")


class ModelCallLogWriter:
    """`CallLogSink` for the gateway → `ai.model_call_logs`.

    A successful call is written inside the caller's transaction, linked to its `message_id`
    (05 §2.8). A failed attempt (`error`/`timeout`/`forbidden`) is written in its **own**
    transaction (R-DEC-154): the turn that hit it usually fails too, and the request rollback
    used to take the log row with it — the provider outages an admin most needs to see on SCR-65
    left no trace. That row keeps `request_id` (the join key of SCR-65) but not `message_id`: the
    message belongs to the rolled-back (or not yet committed) turn, so the FK cannot point at it.
    Routing reason / classification go to the structured log line (07 §6.5 "không thêm cột").
    """

    def __init__(
        self, db: AsyncSession,
        independent: Callable[[], Any] | None = None,
    ) -> None:  # fmt: skip
        self.repo = ModelCallLogRepository(db)
        # an `async_sessionmaker`-like factory for the independent write (tests inject theirs)
        self._independent = independent or get_sessionmaker()

    async def record(self, rec: CallRecord) -> None:
        log.info(
            "model_call provider=%s model=%s task=%s status=%s classification=%s route=%s",
            rec.provider, rec.model, rec.task_kind, rec.status, rec.classification,
            rec.route_reason,
        )  # fmt: skip
        row = ModelCallLog(
            caller_module=rec.caller_module,
            task_kind=rec.task_kind,
            provider=rec.provider,
            model=rec.model,
            fallback_from=rec.fallback_from,
            message_id=_uuid(rec.message_id) if rec.status == "ok" else None,
            source_document_id=_uuid(rec.source_document_id),
            user_id=_uuid(rec.user_id),
            tokens_in=rec.tokens_in,
            tokens_out=rec.tokens_out,
            estimated_cost_micro_usd=rec.estimated_cost_micro_usd,
            latency_ms=rec.latency_ms,
            status=rec.status,
            error_code=rec.error_code,
            prompt_sha256=rec.prompt_sha256,
            tenant_id=current_tenant() or DEFAULT_TENANT_ID,
            request_id=_uuid(rec.request_id),
            agent_profile_code=rec.agent_profile_code,
        )
        if rec.status == "ok":
            await self.repo.add(row)
            return
        try:
            async with self._independent() as session:
                await ModelCallLogRepository(session).add(row)
                await session.commit()
        except Exception:  # telemetry must never turn a provider error into a different one
            log.exception("model_call log write failed (status=%s)", rec.status)

    async def month_spend_micro_usd(self) -> int:
        return await self.repo.cost_since(month_start())


def _uuid(value: Any) -> uuid.UUID | None:
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except ValueError:
            return None
    return value if isinstance(value, uuid.UUID) else None


class AiService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def gateway(self, **kw: Any) -> ModelGateway:
        """Gateway bound to this session's `ModelCallLog` (ai_core; `idp` via this service)."""
        return ModelGateway(ModelCallLogWriter(self.db), **kw)

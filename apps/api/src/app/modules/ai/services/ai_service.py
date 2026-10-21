"""Public service interface of `ai` — the only entry point for other modules."""

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_gateway import CallRecord, ModelGateway
from app.modules.ai.models import ModelCallLog
from app.modules.ai.repositories import ModelCallLogRepository, month_start

log = logging.getLogger("app.ai")


class ModelCallLogWriter:
    """`CallLogSink` for the gateway → `ai.model_call_logs` in the caller's session.

    Writes inside the caller's transaction. Routing reason / classification go to the
    structured log line (no extra column — 07 §6.5 "không thêm cột").
    """

    def __init__(self, db: AsyncSession) -> None:
        self.repo = ModelCallLogRepository(db)

    async def record(self, rec: CallRecord) -> None:
        log.info(
            "model_call provider=%s model=%s task=%s status=%s classification=%s route=%s",
            rec.provider, rec.model, rec.task_kind, rec.status, rec.classification,
            rec.route_reason,
        )  # fmt: skip
        await self.repo.add(
            ModelCallLog(
                caller_module=rec.caller_module,
                task_kind=rec.task_kind,
                provider=rec.provider,
                model=rec.model,
                fallback_from=rec.fallback_from,
                message_id=_uuid(rec.message_id),
                source_document_id=_uuid(rec.source_document_id),
                user_id=_uuid(rec.user_id),
                tokens_in=rec.tokens_in,
                tokens_out=rec.tokens_out,
                estimated_cost_micro_usd=rec.estimated_cost_micro_usd,
                latency_ms=rec.latency_ms,
                status=rec.status,
                error_code=rec.error_code,
                prompt_sha256=rec.prompt_sha256,
            )
        )

    async def month_spend_micro_usd(self) -> int:
        return await self.repo.cost_since(month_start())


def _uuid(value: Any) -> uuid.UUID | None:
    return value if isinstance(value, uuid.UUID) else None


class AiService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def gateway(self, **kw: Any) -> ModelGateway:
        """Gateway bound to this session's `ModelCallLog` (ai_core; `idp` via this service)."""
        return ModelGateway(ModelCallLogWriter(self.db), **kw)

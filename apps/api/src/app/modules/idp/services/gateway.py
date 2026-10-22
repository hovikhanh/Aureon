"""ModelGateway factory for the IDP pipeline (04 §7.4). Binds the gateway's call log to the
pipeline's session (every LLM call recorded in `ai.model_call_logs` via the ai service) and
applies classification routing. Kept behind this helper so the pipeline/extractor accept an
injected gateway and stay testable without a provider (DEC-233)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.services.ai_service import AiService


def pipeline_gateway(db: AsyncSession) -> Any:
    return AiService(db).gateway()

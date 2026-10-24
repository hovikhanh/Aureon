"""ModelGateway factory for the IDP pipeline (04 §7.4). Binds the gateway's call log to the
pipeline's session (every LLM call recorded in `ai.model_call_logs`) and applies classification
routing. Kept behind this helper so the pipeline/extractor accept an injected gateway and stay
testable without a provider (DEC-233).

R-DEC-60 (T-636): calls `core/model_gateway` directly — the call-log writer comes from the
`core` sink registry (registered by `ai`), so `idp` no longer imports `ai` (no `ai ↔ idp` cycle
once `ai` re-exports the Action Registry v2 from `idp`).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_gateway import ModelGateway
from app.core.model_gateway.sinks import session_sink


def pipeline_gateway(db: AsyncSession) -> ModelGateway:
    return ModelGateway(session_sink(db))

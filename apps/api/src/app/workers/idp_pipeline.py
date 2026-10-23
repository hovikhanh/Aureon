"""Celery task running the IDP pipeline out of band (04 §3, 07 §300). Each call runs in its
own event loop with a NullPool engine (like the other workers) and commits once. Idempotent:
re-running a document whose job already SUCCEEDED/FAILED is a no-op. Runs inside
`tenant_scope(tenant_id)` passed by the enqueuer (R-DEC-21); no tenant → refused (fail closed)."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import TenantContextMissingError, tenant_scope
from app.modules.idp.services.gateway import pipeline_gateway
from app.modules.idp.services.pipeline import Pipeline
from app.worker import celery_app
from app.workers.events import _engine

PIPELINE_LIMITS = {"time_limit": 300, "soft_time_limit": 240}


async def _run(document_id: str, tenant_id: str) -> str:
    with tenant_scope(uuid.UUID(tenant_id)):
        async with _engine() as engine, AsyncSession(engine, expire_on_commit=False) as session:
            pipeline = Pipeline(session, pipeline_gateway(session))
            outcome = await pipeline.run(uuid.UUID(document_id))
            await session.commit()
            return outcome.status


@celery_app.task(name="app.idp.process_document", **PIPELINE_LIMITS)  # type: ignore[untyped-decorator]
def process_document(document_id: str, tenant_id: str | None = None) -> str:
    if not tenant_id:
        raise TenantContextMissingError("process_document without tenant_id (R-DEC-21)")
    return asyncio.run(_run(document_id, tenant_id))

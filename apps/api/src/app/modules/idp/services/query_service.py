"""Read side of `idp` — document detail (EP-25) and extraction result (EP-26). Scope: a
reader sees documents they submitted or within their department; CEO/ADMIN-style `idp:read`
with no department sees all (10 §2, 02 §6). Field values at sensitivity ≥ 4 are masked for
roles without level-4 access (handled at the field layer in review, S4b)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.modules.idp.models import ExtractionJob, SourceDocument
from app.modules.idp.repositories import ExtractedFieldRepository, SourceDocumentRepository
from app.modules.idp.schemas import ExtractionResultOut, FieldResultOut


class IdpQueryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_document(self, user: Principal, document_id: uuid.UUID) -> SourceDocument | None:
        doc = await SourceDocumentRepository(self.db).by_id(document_id)
        if doc is None or not self._visible(user, doc):
            return None
        return doc

    async def get_extraction(
        self, user: Principal, document_id: uuid.UUID
    ) -> ExtractionResultOut | None:
        doc = await self.get_document(user, document_id)
        if doc is None:
            return None
        job = (
            (
                await self.db.execute(
                    select(ExtractionJob)
                    .where(ExtractionJob.source_document_id == document_id)
                    .order_by(ExtractionJob.attempt_no.desc())
                )
            )
            .scalars()
            .first()
        )
        if job is None:
            return None
        fields = await ExtractedFieldRepository(self.db).for_job(job.id, ordered=True)
        xd = job.xd_results or {}
        return ExtractionResultOut(
            job_id=job.id,
            document_id=document_id,
            status=job.status,
            document_confidence=float(job.document_confidence) if job.document_confidence else None,
            routing_decision=job.routing_decision,
            routing_reasons=list(job.routing_reasons or []),
            fields=[FieldResultOut.model_validate(f) for f in fields],
            validation_errors=list(xd.get("validation_errors", [])),
        )

    @staticmethod
    def _visible(user: Principal, doc: SourceDocument) -> bool:
        if user.has("idp:admin") or user.department_id is None:
            return True
        if doc.submitted_by == user.user_id:
            return True
        return doc.department_id is not None and doc.department_id == user.department_id

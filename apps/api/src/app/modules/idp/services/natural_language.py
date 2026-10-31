"""C2 natural-language capture — EP-DC-38 (10 §7.2.4, R-DEC-96/97, R-DEC-22).

A text (or transcribed-audio) utterance is stored as a `text/plain` object, carried through the
real IDP `Pipeline` (classify → extract → validate → route), and returned as a NOT-committed
preview: no ACT runs and nothing is written to target modules. The document simply lands in
`NEEDS_REVIEW` / `AUTO_APPROVED` exactly as any C2 capture would, and the caller sees what the
pipeline inferred (doc type, extracted fields, the planned actions) without executing it.

`context == "meeting"` is blocked up front (R-DEC-22): meeting audio is not an IDP capture.
Over-size enforcement on an `audio_ref` is not possible (no bytes) — the upload path owns size.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import BusinessRuleError
from app.core.field_policy import Masked
from app.core.storage import DEFAULT_BUCKET, ObjectStore, get_object_store
from app.modules.idp.models import ExtractionJob, SourceDocument
from app.modules.idp.repositories import ExtractedFieldRepository
from app.modules.idp.schemas.capture import (
    DocumentTypeConfidenceOut,
    ExtractedFieldPreviewOut,
    NaturalLanguageIn,
    NaturalLanguagePreviewOut,
    PredictedActionOut,
)
from app.modules.idp.services.capture_common import document_out, type_code
from app.modules.idp.services.commit_service import CommitService
from app.modules.idp.services.gateway import pipeline_gateway
from app.modules.idp.services.pipeline import Pipeline
from app.modules.idp.services.schema_registry import default_schema_id

TXT_MIME = "text/plain"
_MASKED = Masked().model_dump()


class NaturalLanguageService:
    def __init__(self, db: AsyncSession, store: ObjectStore | None = None) -> None:
        self.db = db
        self.store = store or get_object_store()

    async def submit(self, user: Principal, body: NaturalLanguageIn) -> NaturalLanguagePreviewOut:
        if body.context == "meeting":  # R-DEC-22 — before any processing
            raise BusinessRuleError(
                "meeting audio is not an IDP capture",
                details={"reason": "meeting_audio_blocked"},
            )
        gateway = pipeline_gateway(self.db)
        text = body.text
        if body.audio_ref is not None:  # R-DEC-97 STT (fixture-only at P0)
            resp = await gateway.transcribe(
                audio_ref=body.audio_ref, caller_module="idp", user_id=user.user_id
            )
            text = resp.content
        doc, job = await self._record(user, text or "")
        await Pipeline(self.db, gateway).run(doc.id)  # classify → extract → validate → route
        await self.db.refresh(doc)
        out = await self._preview(user, doc, job)
        await record_audit(
            self.db, action="idp.natural_language_submit", target_schema="idp",
            target_table="source_documents", target_id=doc.id,
            after={"channel": doc.channel, "status": doc.status,
                   "document_type": out.document_type.code},
        )  # fmt: skip
        return out

    async def _record(self, user: Principal, text: str) -> tuple[SourceDocument, ExtractionJob]:
        """Store the utterance as a `text/plain` object + a QUEUED job, mirroring UploadService."""
        data = text.encode("utf-8")
        storage_key = self.store.put_stream(iter([data]), bucket=DEFAULT_BUCKET)
        now = datetime.now(UTC)
        doc = SourceDocument(
            channel="C2", kind="FILE", mime_type=TXT_MIME, size_bytes=len(data),
            storage_key=storage_key, sha256=hashlib.sha256(data).hexdigest(),
            scan_status="PENDING", pillars=[], status="UPLOADED", sensitivity_level=2,
            source="IDP", data_classification="INTERNAL", submitted_by=user.user_id,
            submitted_at=now, department_id=user.department_id,
        )  # fmt: skip
        self.db.add(doc)
        await self.db.flush()
        job = ExtractionJob(
            source_document_id=doc.id, extraction_schema_id=await default_schema_id(self.db),
            attempt_no=1, status="QUEUED", routing_reasons=[], xd_results={},
        )  # fmt: skip
        self.db.add(job)
        await self.db.flush()
        return doc, job

    async def _preview(
        self, user: Principal, doc: SourceDocument, job: ExtractionJob
    ) -> NaturalLanguagePreviewOut:
        code = await type_code(self.db, doc.document_type_id)
        fields = await ExtractedFieldRepository(self.db).for_job(job.id)
        extracted = [
            ExtractedFieldPreviewOut(
                field=f.field_name,
                value=_MASKED if int(f.sensitivity_level or 0) >= 4 else f.value,
                confidence=float(f.confidence) if f.confidence is not None else None,
            )
            for f in fields
        ]
        steps = await CommitService(self.db).planned(user, doc)  # plan only, no write
        conf = float(doc.classification_confidence) if doc.classification_confidence else None
        predicted = [
            PredictedActionOut(
                action_name=s.act.name,
                params={k: (_MASKED if k in s.act.level4_params else v)
                        for k, v in s.params.items()},
                confidence=conf,
            )
            for s in steps
        ]  # fmt: skip
        status = "AUTO_APPROVED" if doc.status == "AUTO_APPROVED" else "NEEDS_REVIEW"
        return NaturalLanguagePreviewOut(
            document=document_out(doc, code),
            document_type=DocumentTypeConfidenceOut(code=code or "", confidence=conf or 0.0),
            status=status, predicted_actions=predicted, extracted=extracted,
        )  # fmt: skip

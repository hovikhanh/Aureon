"""IDP pipeline orchestrator (04 §3). Runs a document through scan → text/OCR → extract →
validate → routing and persists `ENT-DocumentPage[]`, `ENT-ExtractedField[]` and the
`ENT-ExtractionJob` outcome. Status machine (05 §6 `document_status`):

    UPLOADED → PREPROCESSING → (FAILED on MALWARE)
             → EXTRACTING → VALIDATING → NEEDS_REVIEW | AUTO_APPROVED

Routing (04 §7.3): STP (`AUTO_APPROVED`) requires document confidence ≥ 0.95, every required
field ≥ 0.90, no critical field, and no validation error — otherwise REVIEW (`NEEDS_REVIEW`).
Critical fields (trường trọng yếu) always force review (FR-DC-16).

`run_pipeline` is synchronous over the given `AsyncSession` so it is callable both from the
Celery task `process_document` and directly in tests. The extractor gateway is injected
(falls back to the real ModelGateway) so the pipeline is testable without a provider (DEC-233).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.errors import NotFoundError
from app.modules.idp.models import (
    DocumentPage,
    DocumentType,
    ExtractedField,
    ExtractionJob,
    ExtractionSchema,
    SourceDocument,
    ValidationRule,
)
from app.modules.idp.services.extractor import Extractor
from app.modules.idp.services.malware_scan import MalwareScanService
from app.modules.idp.services.preprocess import extract_pages
from app.modules.idp.services.schema_registry import schema_for_code
from app.modules.idp.services.validator import Validator

STP_DOC_CONFIDENCE = 0.95
STP_REQUIRED_FIELD_MIN = 0.90

# Minimal keyword classifier (04 §3 step 4). Full LLM classification + 9 doc types is T-403/
# a later sub-sprint; S4a routes to INVOICE when the text is clearly an invoice, else OTHER.
_INVOICE_HINTS = ("hoa don", "hóa đơn", "invoice", "vat", "gtgt", "mst", "tien thue")


def classify(text: str) -> tuple[str, float]:
    low = text.lower()
    hits = sum(1 for h in _INVOICE_HINTS if h in low)
    if hits >= 2:
        return "INVOICE", round(min(0.90 + 0.02 * hits, 0.99), 4)
    return "OTHER", 0.50


@dataclass
class PipelineOutcome:
    document_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    routing_decision: str | None
    document_confidence: float
    validation_errors: list[dict[str, Any]]
    routing_reasons: list[str] = field(default_factory=list)
    document_type: str | None = None


class Pipeline:
    def __init__(self, db: AsyncSession, gateway: Any) -> None:
        self.db = db
        self.gateway = gateway
        self.scanner = MalwareScanService()

    async def run(self, document_id: uuid.UUID) -> PipelineOutcome:
        doc = await self._get_doc(document_id)
        job = await self._latest_job(document_id)
        job.status = "RUNNING"
        job.started_at = datetime.now(UTC)
        await self.db.flush()

        # --- step 1: malware scan ---
        scan = self.scanner.scan(doc.storage_key or "")
        doc.scan_status = scan.status
        if scan.status == "INFECTED":
            if doc.storage_key:
                doc.storage_key = self.scanner.quarantine(doc.storage_key)
            return await self._fail(doc, job, "MALWARE", scan.signature)
        doc.status = "PREPROCESSING"
        await self.db.flush()

        # --- steps 2–3: text layer + OCR ---
        data = self.scanner.store.read(doc.storage_key or "")
        pre = extract_pages(data, doc.mime_type or "")
        doc.page_count = pre.page_count
        for p in pre.pages:
            self.db.add(
                DocumentPage(
                    source_document_id=doc.id,
                    page_number=p.page_number,
                    sheet_name=p.sheet_name,
                    text_layer_exists=p.text_layer_exists,
                    ocr_used=p.ocr_used,
                    ocr_confidence=p.ocr_confidence,
                    text_content=p.text_content,
                )
            )
        await self.db.flush()

        # --- step 4: classification (pick the doc type + its published schema) ---
        doc.status = "CLASSIFYING"
        await self.db.flush()
        type_code, class_conf = classify(pre.full_text)
        schema_id = await schema_for_code(self.db, type_code)
        dt = await self._document_type_of(schema_id)
        doc.document_type_id = dt.id
        doc.classification_confidence = class_conf
        if dt.pillars:
            doc.pillars = list(dt.pillars)
        if schema_id != job.extraction_schema_id:
            job.extraction_schema_id = schema_id
        await self.db.flush()

        # --- step 6: extraction ---
        doc.status = "EXTRACTING"
        await self.db.flush()
        schema = await self._schema(job.extraction_schema_id)
        fields_spec: list[dict[str, Any]] = list(schema.fields)
        extraction = await Extractor(self.gateway).extract(
            schema_fields=fields_spec,
            page_text=pre.full_text,
            sensitivity_level=doc.sensitivity_level,
            document_id=doc.id,
        )
        job.model_provider = extraction.provider
        job.model_name = extraction.model
        job.document_confidence = extraction.document_confidence

        # --- step 8: validation ---
        doc.status = "VALIDATING"
        await self.db.flush()
        rules = await self._rules(schema.id)
        values = {f.field_name: f.value for f in extraction.fields}
        required = {f["name"] for f in fields_spec if f.get("required")}
        validation = Validator(rules).validate(values, required=required)

        pages = await self._page_map(doc.id)
        for fr in extraction.fields:
            self.db.add(
                ExtractedField(
                    extraction_job_id=job.id,
                    document_page_id=pages.get(1),
                    field_name=fr.field_name,
                    row_index=fr.row_index,
                    value_type=fr.value_type,
                    value=fr.value,
                    raw_text=fr.raw_text,
                    confidence=fr.confidence,
                    confidence_band=fr.confidence_band,
                    is_critical=fr.is_critical,
                    sensitivity_level=fr.sensitivity_level,
                    source_location=fr.source_location,
                    validation=validation.for_field(fr.field_name),
                    source="IDP",
                    data_classification="INTERNAL",
                )
            )

        # --- step 9: routing ---
        decision, reasons = self._route(extraction, validation, fields_spec)
        job.routing_decision = decision
        job.routing_reasons = reasons
        job.status = "SUCCEEDED"
        job.finished_at = datetime.now(UTC)
        job.xd_results = {
            "validation_errors": validation.errors,
            "document_confidence": extraction.document_confidence,
        }
        doc.status = "AUTO_APPROVED" if decision == "STP" else "NEEDS_REVIEW"
        doc.routing_reason = ", ".join(reasons) if reasons else None
        await self.db.flush()

        # On entering NEEDS_REVIEW, create the initial ASSIGN (04 §8.2): due at now + SLA.
        # Department scoping picks the reviewer pool later; the row drives the queue + SLA clock.
        if doc.status == "NEEDS_REVIEW":
            await self._assign_review(doc)
        await record_audit(
            self.db,
            action="idp.extract",
            target_schema="idp",
            target_table="extraction_jobs",
            target_id=job.id,
            after={
                "status": doc.status,
                "routing": decision,
                "confidence": extraction.document_confidence,
            },
        )
        return PipelineOutcome(
            doc.id,
            job.id,
            doc.status,
            decision,
            extraction.document_confidence,
            validation.errors,
            routing_reasons=reasons,
            document_type=type_code,
        )

    # -------- review assignment --------
    async def _assign_review(self, doc: SourceDocument) -> None:
        """Create the initial ASSIGN row (04 §8.2). `due_at = now + REVIEW_SLA_HOURS`. Assigned
        to the submitter's department reviewer pool by role (`REVIEWER`); a concrete user is
        chosen by the queue / reassign later. Idempotent: skips if a current assignment exists."""
        from datetime import timedelta

        from app.core.config import get_config
        from app.modules.idp.models import ReviewAssignment

        existing = (
            await self.db.execute(
                select(ReviewAssignment).where(
                    ReviewAssignment.source_document_id == doc.id,
                    ReviewAssignment.is_current.is_(True),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return
        due_at = datetime.now(UTC) + timedelta(hours=get_config().review_sla_hours)
        self.db.add(
            ReviewAssignment(
                source_document_id=doc.id,
                kind="ASSIGN",
                to_role_code="REV",
                due_at=due_at,
                is_current=True,
            )
        )
        await self.db.flush()

    # -------- routing --------
    def _route(
        self, extraction: Any, validation: Any, fields_spec: list[dict[str, Any]]
    ) -> tuple[str, list[str]]:
        reasons: list[str] = []
        required = {f["name"] for f in fields_spec if f.get("required")}
        if any(f.is_critical for f in extraction.fields):
            reasons.append("CRITICAL_FIELD")
        if extraction.document_confidence < STP_DOC_CONFIDENCE:
            reasons.append("LOW_DOCUMENT_CONFIDENCE")
        for f in extraction.fields:
            if f.field_name in required and f.confidence < STP_REQUIRED_FIELD_MIN:
                reasons.append(f"LOW_CONFIDENCE:{f.field_name}")
        if not validation.ok:
            reasons.append("VALIDATION_FAILED")
        return ("REVIEW" if reasons else "STP"), reasons

    # -------- persistence helpers --------
    async def _get_doc(self, document_id: uuid.UUID) -> SourceDocument:
        doc = (
            await self.db.execute(select(SourceDocument).where(SourceDocument.id == document_id))
        ).scalar_one()
        return doc

    async def _latest_job(self, document_id: uuid.UUID) -> ExtractionJob:
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
            raise NotFoundError(f"no extraction job for document {document_id}")
        return job

    async def _document_type_of(self, schema_id: uuid.UUID) -> DocumentType:
        schema = await self._schema(schema_id)
        return (
            await self.db.execute(
                select(DocumentType).where(DocumentType.id == schema.document_type_id)
            )
        ).scalar_one()

    async def _schema(self, schema_id: uuid.UUID) -> ExtractionSchema:
        return (
            await self.db.execute(select(ExtractionSchema).where(ExtractionSchema.id == schema_id))
        ).scalar_one()

    async def _rules(self, schema_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = (
            (
                await self.db.execute(
                    select(ValidationRule).where(
                        ValidationRule.extraction_schema_id == schema_id,
                        ValidationRule.is_active.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
        return [
            {"code": r.code, "kind": r.kind, "expression": r.expression, "severity": r.severity}
            for r in rows
        ]

    async def _page_map(self, document_id: uuid.UUID) -> dict[int, uuid.UUID]:
        rows = (
            (
                await self.db.execute(
                    select(DocumentPage).where(DocumentPage.source_document_id == document_id)
                )
            )
            .scalars()
            .all()
        )
        return {p.page_number: p.id for p in rows}

    async def _fail(
        self, doc: SourceDocument, job: ExtractionJob, reason: str, detail: str | None
    ) -> PipelineOutcome:
        doc.status = "FAILED"
        doc.status_reason = reason
        job.status = "FAILED"
        job.error_code = reason
        job.finished_at = datetime.now(UTC)
        job.xd_results = {"error": reason, "detail": detail}
        await self.db.flush()
        await record_audit(
            self.db,
            action="idp.scan",
            target_schema="idp",
            target_table="source_documents",
            target_id=doc.id,
            after={"status": "FAILED", "reason": reason, "signature": detail},
        )
        return PipelineOutcome(doc.id, job.id, "FAILED", None, 0.0, [])


def enqueue_pipeline(document_id: uuid.UUID) -> None:
    """Hand a document to the pipeline out of band (Celery). A missing broker (tests/dev without
    a worker) is tolerated — the document stays `UPLOADED` until a worker or a direct call runs
    the pipeline."""
    try:
        from app.workers.idp_pipeline import process_document

        process_document.delay(str(document_id))
    except Exception:
        return

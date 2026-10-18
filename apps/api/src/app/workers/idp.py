"""Celery tasks for the IDP pipeline (T-206, T-211; 07 §3.1, §5.1).

Coordinates:
- Preprocessing & OCR (T-206)
- Classification & schema extraction (T-207)
- Table extraction & VN normalization (T-208)
- Internal validation & prompt injection defense (T-209)
- Cross-doc consistency (T-210)
- Confidence routing S1–S7 (T-211)
- Celery idempotent execution and safe retry without duplicating fields (TC-IDP-035, TC-IDP-030).
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.idp.enums import DocumentStatus, JobStatus
from app.modules.idp.extraction import classify_document, extract_document_fields
from app.modules.idp.models import ExtractedField, ExtractionJob, SourceDocument
from app.modules.idp.preprocessing import preprocess_document
from app.modules.idp.routing import evaluate_routing
from app.worker import QUEUE_IDP, celery_app
from app.workers.base import IdempotentTask, retry_countdown

logger = logging.getLogger(__name__)


def run_document_pipeline(
    db: Session,
    doc_id: UUID,
    job_id: UUID | None = None,
    autonomy_override: str | None = None,
    kill_switch_override: bool | None = None,
) -> dict[str, Any]:
    """Execute the full IDP pipeline for a document."""
    doc = db.get(SourceDocument, doc_id)
    if not doc:
        return {"error": "DOCUMENT_NOT_FOUND"}

    # 0. Check password protected (TC-IDP-030: IDP-E02, no retry)
    if doc.manual_payload and doc.manual_payload.get("is_password_protected"):
        doc.status = DocumentStatus.FAILED
        doc.status_reason = "Tài liệu có mật khẩu bảo vệ (IDP-E02)"
        if job_id:
            existing_job = db.get(ExtractionJob, job_id)
            if existing_job:
                existing_job.status = JobStatus.FAILED
                existing_job.error_code = "IDP-E02"
        db.commit()
        return {
            "document_id": str(doc.id),
            "status": doc.status.value,
            "error_code": "IDP-E02",
        }

    # Step 1: Preprocessing & OCR
    doc.status = DocumentStatus.PREPROCESSING
    db.flush()
    preprocess_document(db=db, doc_id=doc.id)
    if doc.status == DocumentStatus.FAILED:
        if job_id:
            job_failed = db.get(ExtractionJob, job_id)
            if job_failed:
                job_failed.status = JobStatus.FAILED
                job_failed.error_code = "IDP-E01"
        db.commit()
        return {"document_id": str(doc.id), "status": doc.status.value}

    # Step 2: Classification (if not already set)
    doc.status = DocumentStatus.CLASSIFYING
    db.flush()
    if not doc.doc_type:
        classify_document(db=db, doc_id=doc.id)

    # Step 3: Extraction (schema + tables + validation + cross-doc)
    doc.status = DocumentStatus.EXTRACTING
    db.flush()

    # Clear old draft extracted_fields for this document before extraction (TC-IDP-035)
    db.execute(
        delete(ExtractedField).where(
            ExtractedField.source_document_id == doc.id,
        )
    )
    db.flush()

    job = extract_document_fields(db=db, doc_id=doc.id)

    # Step 4: Routing Decision (S1–S7)
    doc.status = DocumentStatus.VALIDATING
    db.flush()
    decision, reason = evaluate_routing(
        db=db,
        doc_id=doc.id,
        job_id=job.id,
        autonomy_override=autonomy_override,
        kill_switch_override=kill_switch_override,
    )

    job.status = JobStatus.SUCCEEDED
    job.finished_at = datetime.now(UTC)
    db.commit()

    return {
        "document_id": str(doc.id),
        "job_id": str(job.id),
        "status": doc.status.value,
        "routing_decision": decision.value,
        "routing_reason": reason,
    }


@celery_app.task(  # type: ignore[untyped-decorator]
    base=IdempotentTask,
    bind=True,
    name="app.workers.idp.preprocess_document",
    queue=QUEUE_IDP,
)
def preprocess_document_task(
    self: Any, document_id: str, db: Any = None
) -> dict[str, Any]:
    """Execute step 1 (preprocessing & OCR) for a source document."""
    logger.info("Starting preprocess_document_task for doc %s", document_id)
    doc_uuid = UUID(document_id)
    if db is not None:
        doc = preprocess_document(db=db, doc_id=doc_uuid)
    else:
        with SessionLocal() as session:
            doc = preprocess_document(db=session, doc_id=doc_uuid)
    return {
        "document_id": str(doc.id),
        "status": doc.status.value,
        "page_count": doc.page_count,
    }


@celery_app.task(  # type: ignore[untyped-decorator]
    base=IdempotentTask,
    bind=True,
    name="app.workers.idp.process_document",
    queue=QUEUE_IDP,
    max_retries=3,
)
def process_document_task(
    self: Any,
    document_id: str,
    job_id: str | None = None,
    autonomy_override: str | None = None,
    kill_switch_override: bool | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """Execute end-to-end IDP pipeline coordinator task."""
    logger.info(
        "Starting process_document_task for doc %s (attempt %d)",
        document_id,
        self.request.retries + 1,
    )
    doc_uuid = UUID(document_id)
    job_uuid = UUID(job_id) if job_id else None

    try:
        if db is not None:
            return run_document_pipeline(
                db=db,
                doc_id=doc_uuid,
                job_id=job_uuid,
                autonomy_override=autonomy_override,
                kill_switch_override=kill_switch_override,
            )
        else:
            with SessionLocal() as session:
                return run_document_pipeline(
                    db=session,
                    doc_id=doc_uuid,
                    job_id=job_uuid,
                    autonomy_override=autonomy_override,
                    kill_switch_override=kill_switch_override,
                )
    except Exception as exc:
        logger.warning(
            "process_document_task failed on attempt %d: %s",
            self.request.retries + 1,
            exc,
        )
        if self.request.retries < self.max_retries:
            countdown = retry_countdown(self.request.retries)
            raise self.retry(exc=exc, countdown=countdown) from exc
        else:
            # Exhausted retries -> mark FAILED with IDP-E06 (TC-IDP-030)
            with SessionLocal() as session:
                doc_obj = session.get(SourceDocument, doc_uuid)
                if doc_obj:
                    doc_obj.status = DocumentStatus.FAILED
                    doc_obj.status_reason = f"Lỗi pipeline sau 3 lần retry: {exc}"
                if job_uuid:
                    job_obj = session.get(ExtractionJob, job_uuid)
                    if job_obj:
                        job_obj.status = JobStatus.FAILED
                        job_obj.error_code = "IDP-E06"
                session.commit()
            raise exc

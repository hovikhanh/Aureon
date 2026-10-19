"""UC-07 onboarding batch aggregation (EP-41; T-311, T-312).

Builds the batch progress / summary / checklist / cross-check payload from the
``source_documents`` that carry a given ``batch_id``. No ``batches`` table exists
(EP-40 stores the checklist only in audit metadata), so the batch is reconstructed
from its member documents. Cross-document checks reuse the XD-01..XD-05 engine
(``cross_doc.run_cross_document_checks``) and are de-duplicated by rule across the
whole batch (04 §12; FR-DC-14, FR-DC-23).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.idp.cross_doc import run_cross_document_checks
from app.modules.idp.enums import DocType, DocumentStatus
from app.modules.idp.models import ExtractionJob, SourceDocument

# Document status -> coarse progress step shown in UC-07 (SCR-08 step 3).
_PROGRESS_STEP: dict[DocumentStatus, str] = {
    DocumentStatus.UPLOADED: "UPLOADED",
    DocumentStatus.PREPROCESSING: "PROCESSING",
    DocumentStatus.CLASSIFYING: "PROCESSING",
    DocumentStatus.EXTRACTING: "PROCESSING",
    DocumentStatus.VALIDATING: "PROCESSING",
    DocumentStatus.NEEDS_REVIEW: "NEEDS_REVIEW",
    DocumentStatus.IN_REVIEW: "NEEDS_REVIEW",
    DocumentStatus.AUTO_APPROVED: "COMMITTED",
    DocumentStatus.APPROVED: "COMMITTED",
    DocumentStatus.COMMITTED: "COMMITTED",
    DocumentStatus.REJECTED: "OTHER",
    DocumentStatus.FAILED: "FAILED",
    DocumentStatus.DUPLICATE: "DUPLICATE",
    DocumentStatus.ROLLED_BACK: "OTHER",
}

_PROCESSING_STATUSES = {
    DocumentStatus.UPLOADED,
    DocumentStatus.PREPROCESSING,
    DocumentStatus.CLASSIFYING,
    DocumentStatus.EXTRACTING,
    DocumentStatus.VALIDATING,
}

_STP_COMMITTED = {DocumentStatus.AUTO_APPROVED, DocumentStatus.COMMITTED, DocumentStatus.APPROVED}
_NEEDS_REVIEW = {DocumentStatus.NEEDS_REVIEW, DocumentStatus.IN_REVIEW}

_CHECKLIST_DOC_TYPES: list[DocType] = [
    DocType.FINANCIAL_REPORT,
    DocType.INVOICE,
    DocType.SALES_REPORT,
    DocType.CONTRACT,
    DocType.MEETING_MINUTES,
    DocType.EMPLOYEE_LIST,
    DocType.KPI_OKR,
]

# High-confidence threshold (03/04 §5; EP-41 high_confidence_ratio).
_HIGH_CONF = 0.90


def progress_step(status: DocumentStatus) -> str:
    return _PROGRESS_STEP.get(status, "OTHER")


def batch_documents(db: Session, batch_id: UUID) -> list[SourceDocument]:
    stmt = (
        select(SourceDocument)
        .where(SourceDocument.batch_id == batch_id, SourceDocument.deleted_at.is_(None))
        .order_by(SourceDocument.uploaded_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


def build_summary(db: Session, docs: list[SourceDocument]) -> dict[str, Any]:
    total = len(docs)
    processing = sum(1 for d in docs if d.status in _PROCESSING_STATUSES)
    stp = sum(1 for d in docs if d.status in _STP_COMMITTED)
    needs_review = sum(1 for d in docs if d.status in _NEEDS_REVIEW)
    failed = sum(1 for d in docs if d.status == DocumentStatus.FAILED)
    duplicate = sum(1 for d in docs if d.status == DocumentStatus.DUPLICATE)
    other = total - processing - stp - needs_review - failed - duplicate

    # Average confidence from the latest extraction job per document.
    confidences: list[float] = []
    for d in docs:
        job = db.execute(
            select(ExtractionJob)
            .where(ExtractionJob.source_document_id == d.id)
            .order_by(ExtractionJob.attempt_no.desc())
        ).scalars().first()
        if job is not None and job.avg_confidence is not None:
            confidences.append(float(job.avg_confidence))
    avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else None
    high_ratio = (
        round(sum(1 for c in confidences if c >= _HIGH_CONF) / len(confidences), 4)
        if confidences
        else None
    )
    return {
        "total": total,
        "processing": processing,
        "stp_committed": stp,
        "needs_review": needs_review,
        "failed": failed,
        "duplicate": duplicate,
        "other": other,
        "avg_confidence": avg_conf,
        "high_confidence_ratio": high_ratio,
    }


def build_checklist(docs: list[SourceDocument]) -> list[dict[str, Any]]:
    by_type: dict[DocType, list[UUID]] = {dt: [] for dt in _CHECKLIST_DOC_TYPES}
    for d in docs:
        if d.doc_type in by_type:
            by_type[d.doc_type].append(d.id)
    return [
        {"doc_type": dt, "present": len(ids) > 0, "document_ids": ids}
        for dt, ids in by_type.items()
    ]


def build_cross_checks(db: Session, docs: list[SourceDocument]) -> list[dict[str, Any]]:
    """Run XD rules across the batch, de-duplicated by rule (keep the most severe result)."""
    severity_rank = {"blocking": 3, "warning": 2, "info": 1, None: 0}
    best: dict[str, dict[str, Any]] = {}
    for d in docs:
        for res in run_cross_document_checks(db, d.id):
            rule = res.get("rule")
            if not rule:
                continue
            sev = res.get("severity")
            doc_ids = res.get("document_ids") or [str(d.id)]
            candidate = {
                "rule": rule,
                "result": res.get("result", "NOT_COMPARABLE"),
                "severity": sev,
                "params": res.get("params"),
                "document_ids": [UUID(str(x)) for x in doc_ids],
            }
            prev = best.get(rule)
            if prev is None or severity_rank.get(sev, 0) > severity_rank.get(prev["severity"], 0):
                best[rule] = candidate
    # Stable order XD-01..XD-05.
    return [best[r] for r in sorted(best.keys())]


def is_complete(docs: list[SourceDocument]) -> bool:
    return all(d.status not in _PROCESSING_STATUSES for d in docs)

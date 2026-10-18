"""Confidence Routing Engine (FR-DC-15, US-DC-011, US-DC-015; T-211; 04 §7, §9, §11).

Evaluates conditions S1–S7 for Straight-Through Processing (STP) vs Review:
- S1: Autonomy level is L3 and AI kill switch is OFF.
- S2: classification_confidence >= 0.95.
- S3: Every required field has value != null and confidence >= 0.90.
- S4: No internal validation rule failed (VR-*); no blocking cross-doc conflict (XD-*).
- S5: Not a duplicate business record (XD-05 or duplicate_of_id).
- S6: Input channel is NOT C2 (conversational / speech input never STP in MVP).
- S7: Doc type does not contain mandatory-review sensitive data (EMPLOYEE_LIST / salary).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.modules.idp.enums import (
    DocType,
    DocumentStatus,
    InputChannel,
    RoutingDecision,
)
from app.modules.idp.models import ExtractedField, ExtractionJob, SourceDocument
from app.modules.idp.schemas_registry import EXTRACTION_SCHEMAS

# Default Autonomy configuration per 04 §9
DEFAULT_AUTONOMY: dict[DocType, str] = {
    DocType.INVOICE: "L2",  # Can be elevated to L3 for demo STP
    DocType.SALES_REPORT: "L2",
    DocType.KPI_OKR: "L2",
    DocType.MEETING_MINUTES: "L2",
    DocType.FINANCIAL_REPORT: "L2",  # Max L2
    DocType.CONTRACT: "L2",  # Max L2
    DocType.EMPLOYEE_LIST: "L2",  # Max L2
}

DOC_TYPE_MAX_AUTONOMY: dict[DocType, str] = {
    DocType.INVOICE: "L3",
    DocType.SALES_REPORT: "L3",
    DocType.KPI_OKR: "L3",
    DocType.MEETING_MINUTES: "L3",
    DocType.FINANCIAL_REPORT: "L2",
    DocType.CONTRACT: "L2",
    DocType.EMPLOYEE_LIST: "L2",
}


def get_doc_type_autonomy(doc_type: DocType | str | None) -> str:
    """Get the active autonomy level for a doc type."""
    cfg = get_config()
    if isinstance(doc_type, str):
        try:
            doc_type = DocType(doc_type)
        except ValueError:
            doc_type = None

    if doc_type == DocType.INVOICE and cfg.invoice_autonomy_level:
        return cfg.invoice_autonomy_level

    if doc_type:
        return DEFAULT_AUTONOMY.get(doc_type, "L2")
    return "L2"


def get_all_doc_type_autonomies() -> list[dict[str, str]]:
    """Return all doc type autonomy configurations for EP-51."""
    res = []
    for dt in (
        DocType.INVOICE,
        DocType.SALES_REPORT,
        DocType.KPI_OKR,
        DocType.MEETING_MINUTES,
        DocType.FINANCIAL_REPORT,
        DocType.CONTRACT,
        DocType.EMPLOYEE_LIST,
    ):
        active_lvl = get_doc_type_autonomy(dt)
        max_lvl = DOC_TYPE_MAX_AUTONOMY.get(dt, "L2")
        res.append(
            {
                "doc_type": dt.value,
                "autonomy_level": active_lvl,
                "max_autonomy_level": max_lvl,
            }
        )
    return res


def evaluate_routing(
    db: Session,
    doc_id: UUID,
    job_id: UUID | None = None,
    autonomy_override: str | None = None,
    kill_switch_override: bool | None = None,
) -> tuple[RoutingDecision, str]:
    """Evaluate S1–S7 rules to decide STP vs REVIEW."""
    doc = db.get(SourceDocument, doc_id)
    if not doc:
        return RoutingDecision.REVIEW, "DOCUMENT_NOT_FOUND"

    cfg = get_config()
    kill_switch = kill_switch_override if kill_switch_override is not None else cfg.ai_kill_switch

    # 1. Condition S1: Kill switch and Autonomy L3
    if kill_switch:
        decision, reason = RoutingDecision.REVIEW, "KILL_SWITCH_ACTIVE"
        _apply_routing_decision(db, doc, job_id, decision, reason)
        return decision, reason

    doc_type = doc.doc_type or DocType.OTHER
    autonomy = autonomy_override or get_doc_type_autonomy(doc_type)
    if autonomy != "L3":
        decision, reason = RoutingDecision.REVIEW, f"AUTONOMY_LEVEL:{autonomy}"
        _apply_routing_decision(db, doc, job_id, decision, reason)
        return decision, reason

    # 2. Condition S6: Channel must NOT be C2
    if doc.channel == InputChannel.C2:
        decision, reason = RoutingDecision.REVIEW, "CHANNEL_C2_NOT_STP"
        _apply_routing_decision(db, doc, job_id, decision, reason)
        return decision, reason

    # 3. Condition S7: Sensitive salary / employee list
    if doc.doc_type == DocType.EMPLOYEE_LIST or doc.contains_salary:
        decision, reason = RoutingDecision.REVIEW, "MANDATORY_REVIEW_SALARY"
        _apply_routing_decision(db, doc, job_id, decision, reason)
        return decision, reason

    # 4. Condition S5: Duplicate check
    if doc.duplicate_of_id is not None:
        decision, reason = RoutingDecision.REVIEW, "DUPLICATE_RECORD"
        _apply_routing_decision(db, doc, job_id, decision, reason)
        return decision, reason

    # Check suspicious content flag (PI-04)
    if doc.manual_payload and doc.manual_payload.get("suspicious_content"):
        decision, reason = RoutingDecision.REVIEW, "SUSPICIOUS_CONTENT"
        _apply_routing_decision(db, doc, job_id, decision, reason)
        return decision, reason

    # 5. Condition S2: Classification confidence >= 0.95
    job: ExtractionJob | None = None
    if job_id:
        job = db.get(ExtractionJob, job_id)
    else:
        job = (
            db.execute(
                select(ExtractionJob)
                .where(ExtractionJob.source_document_id == doc.id)
                .order_by(ExtractionJob.attempt_no.desc())
            )
            .scalars()
            .first()
        )

    cls_conf = (
        float(job.classification_confidence)
        if (job and job.classification_confidence is not None)
        else 0.0
    )
    if cls_conf < 0.95:
        decision, reason = RoutingDecision.REVIEW, f"LOW_CLASSIFICATION_CONFIDENCE:{cls_conf:.2f}"
        _apply_routing_decision(db, doc, job_id, decision, reason)
        return decision, reason

    # 6. Condition S4: Validation and Cross-doc rules

    if job and job.validation_summary:
        val_rules = job.validation_summary.get("rules", [])
        failed_rules = [r for r in val_rules if r.get("status") == "fail"]
        if failed_rules:
            failed_name = failed_rules[0].get("rule", "VR_FAIL")
            decision, reason = RoutingDecision.REVIEW, f"VALIDATION_FAILED:{failed_name}"
            _apply_routing_decision(db, doc, job_id, decision, reason)
            return decision, reason

    if job and job.cross_doc_results:
        for xd in job.cross_doc_results:
            if xd.get("severity") == "blocking" and xd.get("result") in (
                "MISMATCH",
                "NOT_COMPARABLE",
            ):
                decision, reason = (
                    RoutingDecision.REVIEW,
                    f"CROSS_DOC_CONFLICT:{xd.get('rule')}",
                )
                _apply_routing_decision(db, doc, job_id, decision, reason)
                return decision, reason

    # 7. Condition S3: Required fields value != null and confidence >= 0.90
    schema_fields = EXTRACTION_SCHEMAS.get(doc_type)
    if schema_fields:
        required_keys = {f.field_key for f in schema_fields if f.required}
        stmt_fields = select(ExtractedField).where(
            ExtractedField.source_document_id == doc.id,
            ExtractedField.table_key.is_(None),
        )
        if job_id:
            stmt_fields = stmt_fields.where(ExtractedField.extraction_job_id == job_id)

        fields = db.execute(stmt_fields).scalars().all()
        field_map = {f.field_key: f for f in fields}

        for rk in required_keys:
            if rk not in field_map or field_map[rk].value is None:
                decision, reason = RoutingDecision.REVIEW, f"MISSING_REQUIRED_FIELD:{rk}"
                _apply_routing_decision(db, doc, job_id, decision, reason)
                return decision, reason

            conf = float(field_map[rk].confidence) if field_map[rk].confidence is not None else 0.0
            if conf < 0.90:
                decision, reason = RoutingDecision.REVIEW, f"LOW_CONFIDENCE:{rk}"
                _apply_routing_decision(db, doc, job_id, decision, reason)
                return decision, reason

    # ALL S1–S7 SATISFIED -> STP!
    decision, reason = RoutingDecision.STP, "STP_CRITERIA_MET"
    _apply_routing_decision(db, doc, job_id, decision, reason)
    return decision, reason


def _apply_routing_decision(
    db: Session,
    doc: SourceDocument,
    job_id: UUID | None,
    decision: RoutingDecision,
    reason: str,
) -> None:
    """Update job and document state based on routing decision."""
    if job_id:
        job = db.get(ExtractionJob, job_id)
        if job:
            job.routing_decision = decision
            job.routing_reason = reason

    if decision == RoutingDecision.STP:
        doc.status = DocumentStatus.AUTO_APPROVED
        doc.status_reason = f"Đạt chuẩn STP: {reason}"
    else:
        doc.status = DocumentStatus.NEEDS_REVIEW
        doc.status_reason = f"Chuyển review: {reason}"

    db.flush()

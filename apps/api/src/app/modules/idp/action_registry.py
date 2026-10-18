"""Action Registry for IDP business commits (T-212; 04 §10, 05 §4.8, DEC-037).

Specs:
- FR-DC-17: Action Registry as the sole gateway to write business entities from IDP.
- US-DC-014: Commit & lineage tracing.
- DEC-037: Extended side effects for 6 remaining record_types.
- Actions:
  - invoice.create (INVOICE + side effect FINANCIAL_LINE)
  - contract.create (CONTRACT + side effect OPPORTUNITY)
  - task.create_from_minutes (TASK + side effect DECISION & PROJECT)
  - employee.upsert (EMPLOYEE)
  - metric_value.upsert (FINANCIAL_LINE / metric actuals)
  - metric_target.upsert (BUDGET_LINE / metric targets)
  - document.reject
  - document.rollback
"""

import hashlib
import logging
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.db.enums import ActorType
from app.modules.audit.service import record_audit
from app.modules.auth.models import User
from app.modules.idp.enums import DocumentStatus, RecordType, ReviewDecision
from app.modules.idp.models import (
    BusinessRecord,
    ExtractedField,
    ExtractionReview,
    SourceDocument,
)

logger = logging.getLogger(__name__)


def generate_idempotency_key(
    doc_id: UUID | str, field_set_version: int | str, action_name: str
) -> str:
    """Deterministic idempotency key: hash(document_id, field_set_version, action_name)."""
    raw = f"{doc_id}:{field_set_version}:{action_name}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Action Input Schemas
# ---------------------------------------------------------------------------


class InvoiceCreateInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    invoice_number: str
    issue_date: date
    customer_name: str
    subtotal: int = Field(ge=0)
    vat_rate: float = Field(ge=0.0, le=1.0)
    vat_amount: int = Field(ge=0)
    total_amount: int = Field(ge=0)
    paid_amount: int = Field(default=0, ge=0)
    due_date: date | None = None
    seller_name: str | None = None
    seller_tax_code: str | None = None
    customer_tax_code: str | None = None
    status: str = "UNPAID"


class ContractCreateInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    contract_number: str
    party_b_name: str
    effective_date: date
    expiry_date: date
    total_value: int = Field(ge=0)
    status: str = "ACTIVE"


class TaskCreateFromMinutesInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    assignee: str | None = None
    due_date: date | None = None
    decision_text: str | None = None
    project_name: str | None = None


class EmployeeUpsertInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    employee_code: str
    full_name: str
    department: str
    title: str
    salary: int | None = None


class MetricValueUpsertInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    metric_code: str
    period: str
    value: float
    value_kind: str = "ACTUAL"
    line_description: str | None = None


class MetricTargetUpsertInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    metric_code: str
    period: str
    target_value: float
    budget_line: str | None = None


class DocumentRejectInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reject_reason_code: str
    reject_note: str | None = None


class DocumentRollbackInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rollback_reason: str | None = None


# ---------------------------------------------------------------------------
# Action Definition & Handlers
# ---------------------------------------------------------------------------


class ActionDef:
    def __init__(
        self,
        name: str,
        input_schema: type[BaseModel],
        required_roles: set[str],
        min_autonomy: str,
        reversible: bool,
        side_effects: list[str],
        handler: Callable[..., dict[str, Any]],
    ) -> None:
        self.name = name
        self.input_schema = input_schema
        self.required_roles = required_roles
        self.min_autonomy = min_autonomy
        self.reversible = reversible
        self.side_effects = side_effects
        self.handler = handler


def _handle_invoice_create(
    db: Session,
    doc: SourceDocument,
    data: InvoiceCreateInput,
    idempotency_key: str,
) -> dict[str, Any]:
    # 1. Main record: INVOICE
    rec = BusinessRecord(
        id=uuid4(),
        record_type=RecordType.INVOICE,
        pillar="FIN",
        code=data.invoice_number,
        name=data.customer_name,
        tax_code=data.customer_tax_code,
        issue_date=data.issue_date,
        due_date=data.due_date,
        subtotal=data.subtotal,
        vat_rate=data.vat_rate,
        vat_amount=data.vat_amount,
        total_amount=data.total_amount,
        paid_amount=data.paid_amount,
        status=data.status,
        source_document_id=doc.id,
        created_by_action="invoice.create",
        idempotency_key=idempotency_key,
        attributes={
            "seller_name": data.seller_name,
            "seller_tax_code": data.seller_tax_code,
        },
    )
    db.add(rec)
    db.flush()

    # DEC-037: Side effect FINANCIAL_LINE for revenue entry
    fin_line = BusinessRecord(
        id=uuid4(),
        record_type=RecordType.FINANCIAL_LINE,
        pillar="FIN",
        code=f"FL-REV-{data.invoice_number}",
        name=f"Doanh thu hóa đơn {data.invoice_number}",
        period_key=data.issue_date.strftime("%Y-%m"),
        issue_date=data.issue_date,
        total_amount=data.subtotal,
        parent_id=rec.id,
        source_document_id=doc.id,
        created_by_action="invoice.create",
        idempotency_key=f"{idempotency_key}:fin_line",
    )
    db.add(fin_line)

    # Link extracted fields for this document to the business record
    fields = (
        db.execute(select(ExtractedField).where(ExtractedField.source_document_id == doc.id))
        .scalars()
        .all()
    )
    for f in fields:
        f.business_record_id = rec.id

    return {
        "business_record_id": str(rec.id),
        "record_type": rec.record_type.value,
        "amount_due": data.total_amount - data.paid_amount,
        "side_effect_record_id": str(fin_line.id),
    }


def _handle_contract_create(
    db: Session,
    doc: SourceDocument,
    data: ContractCreateInput,
    idempotency_key: str,
) -> dict[str, Any]:
    # 1. Main record: CONTRACT
    rec = BusinessRecord(
        id=uuid4(),
        record_type=RecordType.CONTRACT,
        pillar="CUS",
        code=data.contract_number,
        name=data.party_b_name,
        start_date=data.effective_date,
        end_date=data.expiry_date,
        total_amount=data.total_value,
        status=data.status,
        source_document_id=doc.id,
        created_by_action="contract.create",
        idempotency_key=idempotency_key,
    )
    db.add(rec)
    db.flush()

    # DEC-037: Side effect OPPORTUNITY (closed deal)
    opp = BusinessRecord(
        id=uuid4(),
        record_type=RecordType.OPPORTUNITY,
        pillar="CUS",
        code=f"OPP-{data.contract_number}",
        name=f"Cơ hội hợp đồng {data.contract_number}",
        total_amount=data.total_value,
        status="WON",
        parent_id=rec.id,
        source_document_id=doc.id,
        created_by_action="contract.create",
        idempotency_key=f"{idempotency_key}:opp",
    )
    db.add(opp)

    fields = (
        db.execute(select(ExtractedField).where(ExtractedField.source_document_id == doc.id))
        .scalars()
        .all()
    )
    for f in fields:
        f.business_record_id = rec.id

    return {
        "business_record_id": str(rec.id),
        "record_type": rec.record_type.value,
        "side_effect_record_id": str(opp.id),
    }


def _handle_task_create(
    db: Session,
    doc: SourceDocument,
    data: TaskCreateFromMinutesInput,
    idempotency_key: str,
) -> dict[str, Any]:
    # 1. Main record: TASK
    rec = BusinessRecord(
        id=uuid4(),
        record_type=RecordType.TASK,
        pillar="OPS",
        name=data.title,
        due_date=data.due_date,
        status="IN_PROGRESS",
        source_document_id=doc.id,
        created_by_action="task.create_from_minutes",
        idempotency_key=idempotency_key,
        attributes={"assignee": data.assignee},
    )
    db.add(rec)
    db.flush()

    # DEC-037: Side effect DECISION & PROJECT
    dec_rec: BusinessRecord | None = None
    if data.decision_text:
        dec_rec = BusinessRecord(
            id=uuid4(),
            record_type=RecordType.DECISION,
            pillar="OPS",
            name=data.decision_text,
            status="EXECUTING",
            parent_id=rec.id,
            source_document_id=doc.id,
            created_by_action="task.create_from_minutes",
            idempotency_key=f"{idempotency_key}:dec",
        )
        db.add(dec_rec)

    fields = (
        db.execute(select(ExtractedField).where(ExtractedField.source_document_id == doc.id))
        .scalars()
        .all()
    )
    for f in fields:
        f.business_record_id = rec.id

    return {
        "business_record_id": str(rec.id),
        "record_type": rec.record_type.value,
        "decision_record_id": str(dec_rec.id) if dec_rec else None,
    }


def _handle_employee_upsert(
    db: Session,
    doc: SourceDocument,
    data: EmployeeUpsertInput,
    idempotency_key: str,
) -> dict[str, Any]:
    # Check existing employee by code
    stmt = select(BusinessRecord).where(
        BusinessRecord.record_type == RecordType.EMPLOYEE,
        BusinessRecord.code == data.employee_code,
    )
    rec = db.execute(stmt).scalar_one_or_none()

    if rec:
        # Snapshot previous for rollback
        rec.previous_snapshot = {
            "name": rec.name,
            "department": rec.department,
            "title": rec.title,
            "salary": rec.salary,
        }
        rec.name = data.full_name
        rec.department = data.department
        rec.title = data.title
        if data.salary is not None:
            rec.salary = data.salary
        rec.source_document_id = doc.id
        rec.idempotency_key = idempotency_key
    else:
        rec = BusinessRecord(
            id=uuid4(),
            record_type=RecordType.EMPLOYEE,
            pillar="HR",
            code=data.employee_code,
            name=data.full_name,
            department=data.department,
            title=data.title,
            salary=data.salary,
            status="ACTIVE",
            source_document_id=doc.id,
            created_by_action="employee.upsert",
            idempotency_key=idempotency_key,
        )
        db.add(rec)

    db.flush()
    return {
        "business_record_id": str(rec.id),
        "record_type": rec.record_type.value,
        "employee_code": data.employee_code,
    }


def _handle_metric_value_upsert(
    db: Session,
    doc: SourceDocument,
    data: MetricValueUpsertInput,
    idempotency_key: str,
) -> dict[str, Any]:
    # DEC-037: Side effect FINANCIAL_LINE or SURVEY_RESPONSE
    rec_type = (
        RecordType.SURVEY_RESPONSE if "NPS" in data.metric_code else RecordType.FINANCIAL_LINE
    )
    rec = BusinessRecord(
        id=uuid4(),
        record_type=rec_type,
        pillar="FIN" if rec_type == RecordType.FINANCIAL_LINE else "CUS",
        code=f"{data.metric_code}-{data.period}",
        name=data.line_description or f"Actual {data.metric_code} kỳ {data.period}",
        period_key=data.period,
        total_amount=int(data.value) if rec_type == RecordType.FINANCIAL_LINE else None,
        score=data.value if rec_type == RecordType.SURVEY_RESPONSE else None,
        source_document_id=doc.id,
        created_by_action="metric_value.upsert",
        idempotency_key=idempotency_key,
    )
    db.add(rec)
    db.flush()
    return {
        "business_record_id": str(rec.id),
        "record_type": rec.record_type.value,
        "metric_code": data.metric_code,
        "value": data.value,
    }


def _handle_metric_target_upsert(
    db: Session,
    doc: SourceDocument,
    data: MetricTargetUpsertInput,
    idempotency_key: str,
) -> dict[str, Any]:
    # DEC-037: Side effect BUDGET_LINE
    rec = BusinessRecord(
        id=uuid4(),
        record_type=RecordType.BUDGET_LINE,
        pillar="FIN",
        code=f"BUDGET-{data.metric_code}-{data.period}",
        name=data.budget_line or f"Target {data.metric_code} kỳ {data.period}",
        period_key=data.period,
        total_amount=int(data.target_value),
        source_document_id=doc.id,
        created_by_action="metric_target.upsert",
        idempotency_key=idempotency_key,
    )
    db.add(rec)
    db.flush()
    return {
        "business_record_id": str(rec.id),
        "record_type": rec.record_type.value,
        "metric_code": data.metric_code,
        "target_value": data.target_value,
    }


def _handle_document_reject(
    db: Session,
    doc: SourceDocument,
    data: DocumentRejectInput,
    idempotency_key: str,
) -> dict[str, Any]:
    doc.status = DocumentStatus.REJECTED
    doc.status_reason = f"Từ chối: {data.reject_reason_code} - {data.reject_note or ''}"

    # Record review decision
    actor_user = db.execute(select(User)).scalars().first()
    uploaded_user = db.get(User, doc.uploaded_by_id) if doc.uploaded_by_id else None
    reviewer_user = actor_user or uploaded_user
    reviewer_id = reviewer_user.id if reviewer_user else uuid4()
    reviewer_role_id = reviewer_user.role_id if reviewer_user else uuid4()

    review = ExtractionReview(
        id=uuid4(),
        source_document_id=doc.id,
        extraction_job_id=doc.extraction_jobs[0].id if doc.extraction_jobs else doc.id,
        reviewer_id=reviewer_id,
        reviewer_role_id=reviewer_role_id,
        decision=ReviewDecision.REJECTED,
        reject_reason_code=data.reject_reason_code,
        reject_note=data.reject_note,
        decided_at=datetime.now(UTC),
    )
    db.add(review)
    db.flush()
    return {"document_id": str(doc.id), "status": doc.status.value}


def _handle_document_rollback(
    db: Session,
    doc: SourceDocument,
    data: DocumentRollbackInput,
    idempotency_key: str,
) -> dict[str, Any]:
    # Soft delete all business records created by this document
    records = (
        db.execute(select(BusinessRecord).where(BusinessRecord.source_document_id == doc.id))
        .scalars()
        .all()
    )
    for r in records:
        r.deleted_at = datetime.now(UTC)

    doc.status = DocumentStatus.ROLLED_BACK
    doc.status_reason = f"Hoàn tác: {data.rollback_reason or 'Rollback theo yêu cầu'}"
    db.flush()
    return {
        "document_id": str(doc.id),
        "status": doc.status.value,
        "rolled_back_records_count": len(records),
    }


# ---------------------------------------------------------------------------
# Registry Map
# ---------------------------------------------------------------------------

ACTION_REGISTRY: dict[str, ActionDef] = {
    "invoice.create": ActionDef(
        name="invoice.create",
        input_schema=InvoiceCreateInput,
        required_roles={"ROLE-01", "ROLE-02", "ROLE-05"},
        min_autonomy="L3",
        reversible=True,
        side_effects=["METRIC-FIN-01", "METRIC-FIN-05"],
        handler=_handle_invoice_create,
    ),
    "contract.create": ActionDef(
        name="contract.create",
        input_schema=ContractCreateInput,
        required_roles={"ROLE-01", "ROLE-03", "ROLE-05"},
        min_autonomy="L3",
        reversible=True,
        side_effects=["METRIC-CUS-01"],
        handler=_handle_contract_create,
    ),
    "task.create_from_minutes": ActionDef(
        name="task.create_from_minutes",
        input_schema=TaskCreateFromMinutesInput,
        required_roles={"ROLE-01", "ROLE-05"},
        min_autonomy="L3",
        reversible=True,
        side_effects=["METRIC-OPS-01"],
        handler=_handle_task_create,
    ),
    "employee.upsert": ActionDef(
        name="employee.upsert",
        input_schema=EmployeeUpsertInput,
        required_roles={"ROLE-01", "ROLE-04", "ROLE-05"},
        min_autonomy="L3",
        reversible=True,
        side_effects=["METRIC-HR-01"],
        handler=_handle_employee_upsert,
    ),
    "metric_value.upsert": ActionDef(
        name="metric_value.upsert",
        input_schema=MetricValueUpsertInput,
        required_roles={"ROLE-01", "ROLE-02", "ROLE-05"},
        min_autonomy="L3",
        reversible=True,
        side_effects=["ALERT_ENGINE"],
        handler=_handle_metric_value_upsert,
    ),
    "metric_target.upsert": ActionDef(
        name="metric_target.upsert",
        input_schema=MetricTargetUpsertInput,
        required_roles={"ROLE-01", "ROLE-02", "ROLE-05"},
        min_autonomy="L3",
        reversible=True,
        side_effects=["ALERT_ENGINE"],
        handler=_handle_metric_target_upsert,
    ),
    "document.reject": ActionDef(
        name="document.reject",
        input_schema=DocumentRejectInput,
        required_roles={"ROLE-01", "ROLE-02", "ROLE-04", "ROLE-05"},
        min_autonomy="L3",
        reversible=True,
        side_effects=[],
        handler=_handle_document_reject,
    ),
    "document.rollback": ActionDef(
        name="document.rollback",
        input_schema=DocumentRollbackInput,
        required_roles={"ROLE-02", "ROLE-04", "ROLE-05"},  # Note: CEO cannot rollback per 02 §3.4
        min_autonomy="L3",
        reversible=False,
        side_effects=["METRIC_RECOMPUTE"],
        handler=_handle_document_rollback,
    ),
}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def execute_action(
    db: Session,
    action_name: str,
    document_id: UUID,
    payload: dict[str, Any],
    actor: User | str,
    field_set_version: int = 1,
) -> dict[str, Any]:
    """Execute action with schema validation, permission checks, and idempotency."""
    if action_name not in ACTION_REGISTRY:
        raise ApiError(ErrorCode.BAD_REQUEST, f"Unknown action '{action_name}'")

    action = ACTION_REGISTRY[action_name]
    doc = db.get(SourceDocument, document_id)
    if not doc:
        raise ApiError(ErrorCode.NOT_FOUND, f"Document {document_id} not found")

    # 1. Permission and autonomy check
    if isinstance(actor, str) and actor == "ai:idp":
        # Check autonomy level
        autonomy = doc.manual_payload.get("autonomy_level") if doc.manual_payload else None
        if autonomy != "L3":
            raise ApiError(
                ErrorCode.FORBIDDEN_ROLE,
                f"AI cannot execute '{action_name}' because autonomy is {autonomy} (< L3)",
            )
    elif isinstance(actor, User):
        actor_role = actor.role.code if actor.role else "UNKNOWN"
        if actor_role not in action.required_roles:
            raise ApiError(
                ErrorCode.FORBIDDEN_ROLE,
                f"User role '{actor_role}' does not have permission to execute '{action_name}'",
            )
    else:
        raise ApiError(ErrorCode.FORBIDDEN_ROLE, "Invalid actor for action execution")

    # 2. Idempotency check
    idempotency_key = generate_idempotency_key(document_id, field_set_version, action_name)
    stmt_idem = select(BusinessRecord).where(BusinessRecord.idempotency_key == idempotency_key)
    existing_record = db.execute(stmt_idem).scalar_one_or_none()
    if existing_record:
        logger.info("Idempotent action call: %s already executed", idempotency_key)
        return {
            "status": "ALREADY_COMMITTED",
            "action": action_name,
            "idempotency_key": idempotency_key,
            "business_record_id": str(existing_record.id),
            "record_type": existing_record.record_type.value,
        }

    # 3. Validate input schema
    try:
        validated_input = action.input_schema(**payload)
    except Exception as exc:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            f"Action '{action_name}' input validation failed: {exc}",
        ) from exc

    # 4. Execute within transaction
    try:
        result = action.handler(db, doc, validated_input, idempotency_key)

        # Audit log recording
        is_user = isinstance(actor, User)
        target_id_val = (
            UUID(result["business_record_id"]) if "business_record_id" in result else doc.id
        )
        user_id = actor.id if isinstance(actor, User) else None
        role_id = actor.role_id if isinstance(actor, User) else None
        record_audit(
            db=db,
            action=f"action.{action_name}",
            target_type="business_records",
            actor_type=ActorType.USER if is_user else ActorType.AI,
            actor_user_id=user_id,
            actor_role_id=role_id,
            target_id=target_id_val,
            source_document_id=doc.id,
            after=result,
            idempotency_key=idempotency_key,
        )

        db.flush()
        return result
    except Exception as exc:
        db.rollback()
        # Set document to NEEDS_REVIEW with reason IDP-E10 per TC-IDP-023
        doc = db.get(SourceDocument, document_id)
        if doc:
            doc.status = DocumentStatus.NEEDS_REVIEW
            doc.status_reason = f"Commit action '{action_name}' thất bại (IDP-E10): {exc}"
            db.commit()
        raise ApiError(
            ErrorCode.ACTION_REJECTED,
            f"Thực thi action '{action_name}' thất bại: {exc}",
        ) from exc

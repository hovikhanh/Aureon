"""FastAPI router for IDP endpoints.

EP-20..EP-27, EP-34, EP-36, EP-40, EP-50 per 10-API-SPECIFICATION.md §4, §6.
"""

import math
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Form, Header, Query, Response, UploadFile, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import ConfigService, get_config
from app.core.envelope import Envelope, Page
from app.core.errors import ApiError, ErrorCode
from app.core.pagination import PageParams, get_page_params, paginate
from app.core.storage import get_storage_service
from app.db.enums import ActorType
from app.db.session import get_db
from app.modules.audit.models import AuditLog
from app.modules.audit.service import record_audit
from app.modules.auth.deps import require_role
from app.modules.auth.models import User
from app.modules.idp.action_registry import (
    build_action_payload_from_doc,
    execute_action,
)
from app.modules.idp.cross_doc import run_cross_document_checks
from app.modules.idp.enums import (
    DocType,
    DocumentKind,
    DocumentStatus,
    InputChannel,
    JobStatus,
    ReviewDecision,
    SensitivityLabel,
)
from app.modules.idp.extraction import (
    change_document_type_and_reextract,
    serialize_extraction_result,
)
from app.modules.idp.models import (
    BusinessRecord,
    DocumentPage,
    ExtractedField,
    ExtractionJob,
    ExtractionReview,
    SourceDocument,
)
from app.modules.idp.preprocessing import split_multi_document
from app.modules.idp.routing import (
    get_all_doc_type_autonomies,
    get_doc_type_autonomy,
)
from app.modules.idp.schemas import (
    AiConfigOut,
    BatchChecklistItem,
    BatchCreateRequest,
    BatchCreateResponse,
    CommitActionResult,
    DocTypeAutonomyOut,
    DocumentAffectedOut,
    DocumentDetailOut,
    DocumentOut,
    DocumentPageDetailOut,
    DocumentReviewOut,
    DocumentSourceOut,
    ExtractionResultOut,
    ExtractionSchemaOut,
    ImportMappingConfirmRequest,
    JobOut,
    KillSwitchConfigOut,
    ManualDocumentCreateRequest,
    ManualInfoOut,
    NaturalLanguageDocumentCreateRequest,
    RetryDocumentRequest,
    RetryMode,
    ReviewApproveCommitOut,
    ReviewApproveOut,
    ReviewApproveRequest,
    ReviewApproveReviewOut,
    ReviewOpenOut,
    ReviewQueueCountsOut,
    ReviewQueueItemOut,
    ReviewQueueMetaOut,
    ReviewQueueResponse,
    ReviewRejectRequest,
    RollbackDocumentRequest,
    RollbackOut,
    StatusTimelineItem,
    ThresholdsConfigOut,
    UpdateDocumentFieldsRequest,
    UserBrief,
)
from app.modules.idp.schemas_registry import get_extraction_schemas_for_role
from app.modules.idp.service import (
    handle_document_upload,
    handle_import_mapping_confirm,
    handle_manual_document_create,
    handle_natural_language_create,
    handle_spreadsheet_upload,
    process_upload_stream,
)
from app.modules.idp.validation import validate_internal_rules
from app.workers.idp import process_document_task

router = APIRouter(tags=["idp"])

CHECKLIST_DOC_TYPES = [
    DocType.FINANCIAL_REPORT,
    DocType.INVOICE,
    DocType.SALES_REPORT,
    DocType.CONTRACT,
    DocType.MEETING_MINUTES,
    DocType.EMPLOYEE_LIST,
    DocType.KPI_OKR,
]


def check_document_in_role_scope(doc: SourceDocument, user: User) -> bool:
    """Check if document is accessible within role scope (02 §3.4, 10 §4 EP-24)."""
    role_code = user.role.code if user.role else "ROLE-01"
    if role_code in ("ROLE-01", "ROLE-05"):
        return True
    if doc.uploaded_by_id == user.id:
        return True
    if role_code == "ROLE-02":
        return "FIN" in doc.pillars
    if role_code == "ROLE-04":
        return "HR" in doc.pillars
    if role_code == "ROLE-03":
        return False
    return False


def compute_ai_state(doc: SourceDocument, cfg: ConfigService | None = None) -> str:
    """Compute P02 AI state badge level (L0..L3) for DocumentOut."""
    if cfg is None:
        cfg = get_config()

    if cfg.ai_kill_switch and cfg.ai_kill_switch_mode == "L0":
        return "L0"

    if doc.channel == InputChannel.C1:
        return "L0"

    effective_autonomy = doc.autonomy_level or get_doc_type_autonomy(doc.doc_type)

    if cfg.ai_kill_switch and cfg.ai_kill_switch_mode == "L2":
        if effective_autonomy == "L3":
            effective_autonomy = "L2"

    if doc.status == DocumentStatus.AUTO_APPROVED:
        return "L3"

    if doc.status == DocumentStatus.COMMITTED and (
        doc.status_reason and "STP" in doc.status_reason
    ):
        return "L3"

    return effective_autonomy


def serialize_document_out(doc: SourceDocument, user: User) -> DocumentOut:
    """Map SQLAlchemy SourceDocument to DocumentOut schema."""
    uploader_name = user.full_name if doc.uploaded_by_id == user.id else "Demo User"
    uploader_id = doc.uploaded_by_id or user.id

    locked_by_brief = None
    if doc.locked_by_id:
        locked_name = user.full_name if doc.locked_by_id == user.id else "Reviewer"
        locked_by_brief = UserBrief(id=doc.locked_by_id, full_name=locked_name)

    latest_job_out = None
    if doc.extraction_jobs:
        sorted_jobs = sorted(doc.extraction_jobs, key=lambda j: j.attempt_no, reverse=True)
        lj = sorted_jobs[0]
        cls_conf = (
            float(lj.classification_confidence)
            if lj.classification_confidence is not None
            else None
        )
        avg_conf = float(lj.avg_confidence) if lj.avg_confidence is not None else None
        latest_job_out = JobOut(
            id=lj.id,
            attempt_no=lj.attempt_no,
            doc_type=lj.doc_type,
            status=lj.status,
            classification_confidence=cls_conf,
            routing_decision=lj.routing_decision,
            routing_reason=lj.routing_reason,
            error_code=lj.error_code,
            avg_confidence=avg_conf,
            validation_summary=lj.validation_summary,
            cross_doc_results=lj.cross_doc_results,
            started_at=lj.started_at,
            finished_at=lj.finished_at,
        )

    contains_salary = bool(doc.contains_salary or doc.doc_type == DocType.EMPLOYEE_LIST)

    cfg = get_config()
    ai_state = compute_ai_state(doc, cfg)
    autonomy_level = doc.autonomy_level or get_doc_type_autonomy(doc.doc_type)
    if cfg.ai_kill_switch and cfg.ai_kill_switch_mode == "L2" and autonomy_level == "L3":
        autonomy_level = "L2"

    return DocumentOut(
        id=doc.id,
        batch_id=doc.batch_id,
        channel=doc.channel,
        kind=doc.kind,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        page_count=doc.page_count,
        doc_type=doc.doc_type,
        pillars=doc.pillars,
        status=doc.status,
        status_reason=doc.status_reason,
        ai_state=ai_state,
        autonomy_level=autonomy_level,
        contains_salary=contains_salary,
        contains_pii=doc.contains_pii,
        duplicate_of_id=doc.duplicate_of_id,
        uploaded_by=UserBrief(id=uploader_id, full_name=uploader_name),
        uploaded_at=doc.uploaded_at,
        committed_at=doc.committed_at,
        undo_deadline=doc.undo_deadline,
        locked_by=locked_by_brief,
        locked_until=doc.locked_until,
        retry_count=doc.retry_count,
        latest_job=latest_job_out,
    )


@router.post(
    "/documents",
    response_model=Envelope[DocumentOut],
    status_code=status.HTTP_201_CREATED,
    summary="Upload document (EP-20)",
)
async def upload_document(
    file: UploadFile,
    response: Response,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    channel: Annotated[InputChannel, Form()] = InputChannel.C3,
    doc_type_hint: Annotated[DocType | None, Form()] = None,
    batch_id: Annotated[UUID | None, Form()] = None,
) -> Envelope[DocumentOut]:
    """EP-20: Upload document from channels C3/C4 (file upload).

    Enforces 20MB max file size, 50 max PDF pages, streaming SHA-256 calculation,
    deduplication, MinIO storage, and audit logging.
    """
    # UC-07 Scoping check (TC-UC07-002): only ROLE-01 and ROLE-05 can upload to a batch
    if batch_id is not None:
        user_role_code = current_user.role.code if current_user.role else ""
        if user_role_code not in ("ROLE-01", "ROLE-05"):
            msg = "Only CEO (ROLE-01) and Reviewer (ROLE-05) can upload to an onboarding batch"
            raise ApiError(ErrorCode.FORBIDDEN_ROLE, msg)

    file_bytes, sha256_hex, size_bytes, page_count = await process_upload_stream(file)

    doc, is_duplicate, duplicate_of_id = handle_document_upload(
        db=db,
        current_user=current_user,
        file_bytes=file_bytes,
        filename=file.filename or "uploaded_file",
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        page_count=page_count,
        sha256_hex=sha256_hex,
        channel=channel,
        doc_type_hint=doc_type_hint,
        batch_id=batch_id,
    )

    # Serialize before dispatching so the response always reports UPLOADED within
    # the 2s budget (10 §EP-20: không chờ xử lý).
    doc_out = serialize_document_out(doc, current_user)
    meta: dict[str, Any] | None = None
    if is_duplicate and duplicate_of_id:
        meta = {
            "warning": {
                "code": "DUPLICATE_DOCUMENT",
                "duplicate_of_id": str(duplicate_of_id),
            }
        }

    # EP-20: enqueue end-to-end processing for a fresh (non-duplicate) upload
    # (10 §EP-20) with a deterministic task id ("task id xác định"). The pipeline
    # owns the ExtractionJob lifecycle, so no placeholder job is created here.
    if not is_duplicate:
        process_document_task.apply_async(
            args=[str(doc.id)],
            task_id=f"{doc.id}:process:1",
        )

    return Envelope(data=doc_out, meta=meta)


@router.post(
    "/onboarding/batches",
    response_model=Envelope[BatchCreateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create onboarding batch (EP-40)",
)
def create_onboarding_batch(
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    payload: BatchCreateRequest | None = None,
) -> Envelope[BatchCreateResponse]:
    """EP-40: Create an onboarding batch (UC-07). Restricted to ROLE-01 and ROLE-05."""
    batch_id = uuid4()
    req = payload or BatchCreateRequest()

    doc_types = req.expected_doc_types or CHECKLIST_DOC_TYPES
    checklist = [BatchChecklistItem(doc_type=dt, required=True) for dt in doc_types]

    # Record audit log
    record_audit(
        db=db,
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        actor_role_id=current_user.role_id,
        action="onboarding.batch_create",
        target_type="batches",
        target_id=batch_id,
        after={
            "batch_id": str(batch_id),
            "expected_doc_types": [dt.value for dt in doc_types],
            "label": req.label,
        },
    )
    db.commit()

    response_data = BatchCreateResponse(
        batch_id=batch_id,
        checklist=checklist,
        upload_endpoint="/api/v1/documents",
    )
    return Envelope(data=response_data)


@router.post(
    "/documents/manual",
    response_model=Envelope[DocumentOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create manual document via form C1 (EP-21)",
)
def create_manual_document(
    payload: ManualDocumentCreateRequest,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[DocumentOut]:
    """EP-21: Manual data entry form (C1).

    Validates schema (e.g. Tax Code format 10/13 digits), creates SourceDocument (MANUAL, C1)
    and ExtractedField rows with confidence=1.0 and source_location.kind=manual.
    """
    doc = handle_manual_document_create(
        db=db,
        current_user=current_user,
        doc_type=payload.doc_type,
        fields=payload.fields,
        batch_id=payload.batch_id,
    )
    doc_out = serialize_document_out(doc, current_user)
    return Envelope(data=doc_out)


@router.post(
    "/documents/natural-language",
    response_model=Envelope[DocumentOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create document via natural language C2 (EP-22)",
)
def create_natural_language_document(
    payload: NaturalLanguageDocumentCreateRequest,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[DocumentOut]:
    """EP-22: Natural language entry (C2).

    Drafts extraction from natural text at L2 (AI-drafted, waiting for confirmation),
    always requires human review (never STP). Blocks with 423 AI_DISABLED when kill switch is on.
    """
    doc = handle_natural_language_create(
        db=db,
        current_user=current_user,
        text=payload.text,
        batch_id=payload.batch_id,
    )
    doc_out = serialize_document_out(doc, current_user)
    return Envelope(data=doc_out)


@router.post(
    "/documents/import",
    response_model=Envelope[DocumentOut],
    status_code=status.HTTP_201_CREATED,
    summary="Import spreadsheet file C5 - Step 1: upload & mapping suggestion (EP-23)",
)
async def import_document(
    file: UploadFile,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    doc_type: Annotated[DocType | None, Form()] = None,
    batch_id: Annotated[UUID | None, Form()] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[DocumentOut]:
    """EP-23: Bulk spreadsheet import (C5) - step 1.

    Reads XLSX/CSV file up to 5,000 rows, produces AI column mapping suggestion (L1).
    """
    file_bytes = await file.read()
    filename = file.filename or "import.xlsx"
    doc, mapping_suggestion = handle_spreadsheet_upload(
        db=db,
        current_user=current_user,
        file_bytes=file_bytes,
        filename=filename,
        doc_type_hint=doc_type,
        batch_id=batch_id,
    )
    doc_out = serialize_document_out(doc, current_user)
    return Envelope(data=doc_out, meta={"mapping_suggestion": mapping_suggestion.model_dump()})


@router.post(
    "/documents/{id}/import-mapping",
    response_model=Envelope[DocumentOut],
    status_code=status.HTTP_200_OK,
    summary="Confirm spreadsheet column mapping C5 - Step 2 (EP-36)",
)
def confirm_import_mapping(
    id: UUID,
    payload: ImportMappingConfirmRequest,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[DocumentOut]:
    """EP-36: Bulk spreadsheet import (C5) - step 2.

    Applies column mapping to extract ExtractedField rows with source_location.kind=cell.
    Row errors are collected and reported in meta.row_errors without blocking valid rows (IDP-E11).
    Restricted to the user who uploaded the document (FORBIDDEN_SCOPE).
    """
    doc, row_errors = handle_import_mapping_confirm(
        db=db,
        current_user=current_user,
        doc_id=id,
        doc_type=payload.doc_type,
        columns=payload.columns,
    )
    doc_out = serialize_document_out(doc, current_user)
    return Envelope(data=doc_out, meta={"row_errors": [e.model_dump() for e in row_errors]})


@router.get(
    "/extraction-schemas",
    response_model=Envelope[list[ExtractionSchemaOut]],
    summary="Get extraction schemas (EP-50)",
)
def get_extraction_schemas(
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")),
    ],
    doc_type: DocType | None = None,
) -> Envelope[list[ExtractionSchemaOut]]:
    """EP-50: Extraction schemas for document types.

    - ROLE-05 can read all doc types if doc_type is omitted.
    - ROLE-01..04 MUST supply doc_type; if omitted, returns 400 BAD_REQUEST.
    - For ROLE-01..04, fields with sensitivity=SALARY are hidden (DS3).
    """
    user_role_code = current_user.role.code if current_user.role else "ROLE-01"
    if user_role_code != "ROLE-05" and doc_type is None:
        raise ApiError(ErrorCode.BAD_REQUEST, "Parameter 'doc_type' is required for this role")

    schemas = get_extraction_schemas_for_role(user_role_code=user_role_code, doc_type=doc_type)
    return Envelope(data=schemas)


@router.get(
    "/documents/{id}/extraction",
    response_model=Envelope[ExtractionResultOut],
    summary="Get extraction results (EP-26)",
)
def get_document_extraction(
    id: UUID,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> Envelope[ExtractionResultOut]:
    """EP-26: Extraction result for a document.

    ROLE-03 forbidden (403).
    CFO (ROLE-02) FIN only; HR (ROLE-04) HR only.
    ROLE-04 sees full salary; ROLE-05 sees salary only when in active review lock;
    CEO (ROLE-01) has salary masked.
    Requires SUCCEEDED extraction job (otherwise 409 CONFLICT_STATE).
    """
    doc = db.get(SourceDocument, id)
    if not doc or doc.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Document {id} not found")

    result = serialize_extraction_result(db=db, doc=doc, current_user=current_user)
    return Envelope(data=result)


@router.patch(
    "/documents/{id}/fields",
    response_model=Envelope[ExtractionResultOut],
    summary="Update document fields / doc_type / split_ranges (EP-30)",
)
def update_document_fields(
    id: UUID,
    payload: UpdateDocumentFieldsRequest,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-02", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[ExtractionResultOut]:
    """EP-30: Sửa field, đổi doc_type, chỉnh ranh giới split_ranges.

    Role scoping & lock:
    - Must hold lock (doc.locked_by_id == current_user.id and doc.status == IN_REVIEW)
      when modifying fields or confirming fields.
    - If locked by another user -> 409 CONFLICT_STATE / REVIEW_LOCKED.
    - CFO (ROLE-02) FIN only; HR Manager (ROLE-04) HR only.
    - Changes: corrected=True, corrected_value, corrected_by_id, preserves AI value.
    - Audit: field.correct (salary masked as ••••).
    """
    doc = db.get(SourceDocument, id)
    if not doc or doc.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Document {id} not found")

    role_code = current_user.role.code if current_user.role else "ROLE-05"
    if role_code == "ROLE-02" and "FIN" not in doc.pillars:
        raise ApiError(
            ErrorCode.FORBIDDEN_SCOPE, "CFO chỉ có quyền chỉnh sửa tài liệu trụ Tài chính"
        )
    if role_code == "ROLE-04" and "HR" not in doc.pillars:
        raise ApiError(
            ErrorCode.FORBIDDEN_SCOPE, "HR Manager chỉ có quyền chỉnh sửa tài liệu trụ Con người"
        )

    now = datetime.now(UTC)
    is_locked_by_other = (
        doc.locked_by_id
        and doc.locked_by_id != current_user.id
        and doc.locked_until is not None
        and doc.locked_until > now
    )
    if is_locked_by_other:
        raise ApiError(ErrorCode.CONFLICT_STATE, "Tài liệu đang được khóa bởi người khác")

    if payload.fields or payload.confirmed_field_ids:
        is_held_by_user = (
            doc.status == DocumentStatus.IN_REVIEW
            and doc.locked_by_id == current_user.id
            and doc.locked_until is not None
            and doc.locked_until > now
        )
        if not is_held_by_user:
            raise ApiError(
                ErrorCode.CONFLICT_STATE,
                "Tài liệu cần được mở review và giữ khóa để sửa hoặc xác nhận trường dữ liệu",
            )

    if payload.split_ranges:
        ranges = [(r.from_page, r.to_page) for r in payload.split_ranges]
        split_multi_document(
            db=db, parent_id=doc.id, split_ranges=ranges, actor_user_id=current_user.id
        )

    if payload.doc_type and payload.doc_type != doc.doc_type:
        change_document_type_and_reextract(
            db=db,
            doc_id=doc.id,
            new_doc_type=payload.doc_type,
            actor_user_id=current_user.id,
        )

    if payload.fields:
        for f_item in payload.fields:
            field = db.get(ExtractedField, f_item.id)
            if not field or field.source_document_id != doc.id:
                continue

            old_val = field.corrected_value if field.corrected else field.value
            field.corrected = True
            field.corrected_value = f_item.corrected_value
            field.corrected_by_id = current_user.id

            if field.sensitivity == SensitivityLabel.SALARY:
                b_str = "••••"
                a_str = "••••"
            else:
                b_str = str(old_val) if old_val is not None else ""
                a_str = str(f_item.corrected_value) if f_item.corrected_value is not None else ""

            record_audit(
                db=db,
                action="field.correct",
                target_type="extracted_fields",
                actor_type=ActorType.USER,
                actor_user_id=current_user.id,
                actor_role_id=current_user.role_id,
                target_id=field.id,
                source_document_id=doc.id,
                before={"field_key": field.field_key, "value": b_str},
                after={"field_key": field.field_key, "value": a_str},
            )

    if payload.confirmed_field_ids:
        for c_id in payload.confirmed_field_ids:
            field = db.get(ExtractedField, c_id)
            if not field or field.source_document_id != doc.id:
                continue
            field.corrected = True
            if field.corrected_value is None:
                field.corrected_value = field.value
            field.corrected_by_id = current_user.id

    if payload.fields or payload.confirmed_field_ids:
        latest_job_id = None
        if doc.extraction_jobs:
            latest_job_id = sorted(doc.extraction_jobs, key=lambda j: j.attempt_no, reverse=True)[
                0
            ].id
        db.flush()
        validate_internal_rules(db, doc_id=doc.id, job_id=latest_job_id)
        run_cross_document_checks(db, doc_id=doc.id, job_id=latest_job_id)
        db.commit()

    result = serialize_extraction_result(db=db, doc=doc, current_user=current_user)
    return Envelope(data=result)


@router.get(
    "/documents",
    response_model=Page[DocumentOut],
    summary="List documents (EP-24)",
)
def list_documents(
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    params: Annotated[PageParams, Depends(get_page_params)],
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    doc_type: Annotated[DocType | None, Query(description="Filter by doc_type")] = None,
    pillar: Annotated[str | None, Query(description="Filter by pillar")] = None,
    channel: Annotated[InputChannel | None, Query(description="Filter by channel")] = None,
    batch_id: Annotated[UUID | None, Query(description="Filter by batch_id")] = None,
    uploaded_by_id: Annotated[UUID | None, Query(description="Filter by uploaded_by_id")] = None,
    q: Annotated[str | None, Query(description="Search filename")] = None,
    sort: Annotated[str, Query(description="Sort order")] = "-uploaded_at",
) -> Page[DocumentOut]:
    """EP-24: List documents scoped by user role.

    - ROLE-01 & ROLE-05: all documents.
    - ROLE-02: FIN pillar + own uploads.
    - ROLE-03: own uploads only.
    - ROLE-04: HR pillar + own uploads.
    """
    role_code = current_user.role.code if current_user.role else "ROLE-01"
    stmt = select(SourceDocument).where(SourceDocument.deleted_at.is_(None))

    if role_code in ("ROLE-01", "ROLE-05"):
        pass
    elif role_code == "ROLE-02":
        stmt = stmt.where(
            or_(
                SourceDocument.pillars.contains(["FIN"]),
                SourceDocument.uploaded_by_id == current_user.id,
            )
        )
    elif role_code == "ROLE-03":
        stmt = stmt.where(SourceDocument.uploaded_by_id == current_user.id)
    elif role_code == "ROLE-04":
        stmt = stmt.where(
            or_(
                SourceDocument.pillars.contains(["HR"]),
                SourceDocument.uploaded_by_id == current_user.id,
            )
        )

    if status:
        st_list = [s.strip() for s in status.split(",") if s.strip()]
        if len(st_list) == 1:
            try:
                enum_st = DocumentStatus(st_list[0])
                stmt = stmt.where(SourceDocument.status == enum_st)
            except ValueError:
                pass
        elif len(st_list) > 1:
            enum_sts = []
            for s in st_list:
                try:
                    enum_sts.append(DocumentStatus(s))
                except ValueError:
                    pass
            if enum_sts:
                stmt = stmt.where(SourceDocument.status.in_(enum_sts))

    if doc_type is not None:
        stmt = stmt.where(SourceDocument.doc_type == doc_type)
    if pillar:
        stmt = stmt.where(SourceDocument.pillars.contains([pillar]))
    if channel:
        stmt = stmt.where(SourceDocument.channel == channel)
    if batch_id:
        stmt = stmt.where(SourceDocument.batch_id == batch_id)
    if uploaded_by_id:
        stmt = stmt.where(SourceDocument.uploaded_by_id == uploaded_by_id)
    if q:
        stmt = stmt.where(SourceDocument.original_filename.ilike(f"%{q}%"))

    if sort == "uploaded_at":
        stmt = stmt.order_by(asc(SourceDocument.uploaded_at))
    else:
        stmt = stmt.order_by(desc(SourceDocument.uploaded_at))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    rows = db.execute(stmt.offset(params.offset).limit(params.limit)).scalars().all()
    items = [serialize_document_out(d, current_user) for d in rows]
    return paginate(items, params=params, total=total)


@router.get(
    "/documents/{id}",
    response_model=Envelope[DocumentDetailOut],
    summary="Get document details (EP-25)",
)
def get_document_details(
    id: UUID,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> Envelope[DocumentDetailOut]:
    """EP-25: Get document detail, jobs, timeline, and affected records.

    Enforces role scope (outside scope -> 403 FORBIDDEN_SCOPE).
    """
    doc = db.get(SourceDocument, id)
    if not doc or doc.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Document {id} not found")

    if not check_document_in_role_scope(doc, current_user):
        raise ApiError(ErrorCode.FORBIDDEN_SCOPE, "Tài liệu nằm ngoài phạm vi quyền của bạn")

    stmt_jobs = (
        select(ExtractionJob)
        .where(ExtractionJob.source_document_id == doc.id)
        .order_by(asc(ExtractionJob.attempt_no))
    )
    jobs = db.execute(stmt_jobs).scalars().all()
    jobs_out = [
        JobOut(
            id=j.id,
            attempt_no=j.attempt_no,
            doc_type=j.doc_type,
            status=j.status,
            classification_confidence=(
                float(j.classification_confidence)
                if j.classification_confidence is not None
                else None
            ),
            routing_decision=j.routing_decision,
            routing_reason=j.routing_reason,
            error_code=j.error_code,
            avg_confidence=(float(j.avg_confidence) if j.avg_confidence is not None else None),
            validation_summary=j.validation_summary,
            cross_doc_results=j.cross_doc_results,
            started_at=j.started_at,
            finished_at=j.finished_at,
        )
        for j in jobs
    ]

    stmt_audit = (
        select(AuditLog)
        .where(
            or_(
                AuditLog.target_id == doc.id,
                AuditLog.source_document_id == doc.id,
            )
        )
        .order_by(asc(AuditLog.occurred_at))
    )
    audit_rows = db.execute(stmt_audit).scalars().all()
    timeline = [
        StatusTimelineItem(
            status=a.action,
            at=a.occurred_at,
            actor_type=a.actor_type.value if hasattr(a.actor_type, "value") else str(a.actor_type),
        )
        for a in audit_rows
    ]
    if not timeline:
        timeline.append(
            StatusTimelineItem(
                status="UPLOADED",
                at=doc.uploaded_at,
                actor_type="USER",
            )
        )

    stmt_recs = select(BusinessRecord).where(
        BusinessRecord.source_document_id == doc.id,
        BusinessRecord.deleted_at.is_(None),
    )
    biz_records = db.execute(stmt_recs).scalars().all()
    affected = DocumentAffectedOut(
        business_record_ids=[r.id for r in biz_records],
        metric_codes=[r.code for r in biz_records if r.code and r.code.startswith("METRIC-")],
    )

    stmt_reviews = (
        select(ExtractionReview)
        .where(ExtractionReview.source_document_id == doc.id)
        .order_by(asc(ExtractionReview.opened_at))
    )
    reviews_rows = db.execute(stmt_reviews).scalars().all()
    reviews_out = []
    for r in reviews_rows:
        reviewer = db.get(User, r.reviewer_id)
        reviews_out.append(
            DocumentReviewOut(
                reviewer_full_name=reviewer.full_name if reviewer else "Reviewer",
                decision=r.decision.value if r.decision else None,
                reject_reason_code=r.reject_reason_code,
                decided_at=r.decided_at,
            )
        )

    doc_out = serialize_document_out(doc, current_user)
    detail = DocumentDetailOut(
        document=doc_out,
        jobs=jobs_out,
        status_timeline=timeline,
        affected=affected,
        reviews=reviews_out,
    )
    return Envelope(data=detail)


@router.get(
    "/documents/{id}/source",
    response_model=Envelope[DocumentSourceOut],
    summary="Get source document presigned URL (EP-27)",
)
def get_document_source(
    id: UUID,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int | None, Query(description="Page number (optional)")] = None,
    disposition: Annotated[str, Query(description="inline or attachment")] = "inline",
) -> Envelope[DocumentSourceOut]:
    """EP-27: Get source document presigned URL (expires in <= 15m) and page metadata.

    Enforces DS4 salary protection:
    - contains_salary=true:
      - ROLE-04: allowed inline + attachment.
      - ROLE-05: allowed ONLY IF in active review lock AND disposition=inline (attachment -> 403).
      - ROLE-01, ROLE-02, ROLE-03 -> 403 FORBIDDEN_SALARY + audit document.open_denied.
    - contains_pii=true -> audit document.open_pii.
    - disposition=attachment -> audit document.download.
    """
    doc = db.get(SourceDocument, id)
    if not doc or doc.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Document {id} not found")

    role_code = current_user.role.code if current_user.role else "ROLE-01"
    now = datetime.now(UTC)

    contains_salary = bool(doc.contains_salary or doc.doc_type == DocType.EMPLOYEE_LIST)
    if contains_salary:
        if role_code == "ROLE-04":
            pass
        elif role_code == "ROLE-05":
            is_actively_reviewing = (
                doc.status == DocumentStatus.IN_REVIEW
                and doc.locked_by_id == current_user.id
                and doc.locked_until is not None
                and doc.locked_until > now
            )
            if not is_actively_reviewing or disposition == "attachment":
                record_audit(
                    db=db,
                    action="document.open_denied",
                    target_type="source_documents",
                    actor_type=ActorType.USER,
                    actor_user_id=current_user.id,
                    actor_role_id=current_user.role_id,
                    target_id=doc.id,
                    source_document_id=doc.id,
                )
                db.commit()
                raise ApiError(
                    ErrorCode.FORBIDDEN_SALARY,
                    "Reviewer chỉ được xem inline tài liệu lương khi đang trực tiếp khóa review",
                )
        else:
            record_audit(
                db=db,
                action="document.open_denied",
                target_type="source_documents",
                actor_type=ActorType.USER,
                actor_user_id=current_user.id,
                actor_role_id=current_user.role_id,
                target_id=doc.id,
                source_document_id=doc.id,
            )
            db.commit()
            raise ApiError(
                ErrorCode.FORBIDDEN_SALARY,
                "Vai trò này không có quyền truy cập tài liệu chứa thông tin lương",
            )

    if not check_document_in_role_scope(doc, current_user):
        raise ApiError(ErrorCode.FORBIDDEN_SCOPE, "Tài liệu nằm ngoài phạm vi quyền của bạn")

    if doc.contains_pii:
        record_audit(
            db=db,
            action="document.open_pii",
            target_type="source_documents",
            actor_type=ActorType.USER,
            actor_user_id=current_user.id,
            actor_role_id=current_user.role_id,
            target_id=doc.id,
            source_document_id=doc.id,
        )
    if disposition == "attachment":
        record_audit(
            db=db,
            action="document.download",
            target_type="source_documents",
            actor_type=ActorType.USER,
            actor_user_id=current_user.id,
            actor_role_id=current_user.role_id,
            target_id=doc.id,
            source_document_id=doc.id,
        )
    db.commit()

    if doc.kind in (DocumentKind.MANUAL, DocumentKind.TRANSCRIPT):
        is_owner = doc.uploaded_by_id == current_user.id
        creator_name = current_user.full_name if is_owner else "Demo User"
        return Envelope(
            data=DocumentSourceOut(
                manual_info=ManualInfoOut(
                    created_by_full_name=creator_name,
                    created_at=doc.uploaded_at,
                )
            )
        )

    storage = get_storage_service()
    storage_key = doc.storage_key or f"documents/{doc.id}.pdf"
    url = storage.generate_presigned_url(storage_key, expires_in=900)
    expires_at = datetime.now(UTC) + timedelta(seconds=900)

    stmt_pages = (
        select(DocumentPage)
        .where(DocumentPage.source_document_id == doc.id)
        .order_by(asc(DocumentPage.page_number))
    )
    db_pages = db.execute(stmt_pages).scalars().all()
    pages_out = [
        DocumentPageDetailOut(
            page_number=p.page_number,
            image_url=p.image_storage_key,
            width_px=p.width_px,
            height_px=p.height_px,
            ocr_used=p.ocr_used,
            ocr_confidence=float(p.ocr_confidence) if p.ocr_confidence is not None else None,
        )
        for p in db_pages
    ]

    return Envelope(
        data=DocumentSourceOut(
            url=url,
            expires_at=expires_at,
            mime_type=doc.mime_type,
            page_count=doc.page_count,
            pages=pages_out,
        )
    )


@router.post(
    "/documents/{id}/retry",
    response_model=Envelope[DocumentOut],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry, reopen, or force-duplicate document (EP-34)",
)
def retry_document(
    id: UUID,
    payload: RetryDocumentRequest,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> Envelope[DocumentOut]:
    """EP-34: Retry failed document, reopen rejected document, or force process duplicate."""
    doc = db.get(SourceDocument, id)
    if not doc or doc.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Document {id} not found")

    role_code = current_user.role.code if current_user.role else "ROLE-01"

    if payload.mode == RetryMode.RETRY:
        if doc.status != DocumentStatus.FAILED:
            raise ApiError(
                ErrorCode.CONFLICT_STATE,
                f"Chỉ có thể RETRY tài liệu ở trạng thái FAILED (hiện tại: {doc.status.value})",
            )
        if role_code == "ROLE-05":
            pass
        elif role_code == "ROLE-02" and "FIN" in doc.pillars:
            pass
        elif role_code == "ROLE-04" and "HR" in doc.pillars:
            pass
        else:
            raise ApiError(
                ErrorCode.FORBIDDEN_ROLE,
                "Bạn không có quyền retry tài liệu này",
            )

        max_attempt = max([j.attempt_no for j in doc.extraction_jobs], default=0)
        new_job = ExtractionJob(
            id=uuid4(),
            source_document_id=doc.id,
            attempt_no=max_attempt + 1,
            doc_type=doc.doc_type or DocType.OTHER,
            status=JobStatus.QUEUED,
            started_at=datetime.now(UTC),
        )
        db.add(new_job)
        doc.status = DocumentStatus.PREPROCESSING
        doc.status_reason = f"Thử lại lần {new_job.attempt_no}: {payload.note or ''}"
        doc.retry_count = doc.retry_count + 1
        db.flush()

        record_audit(
            db=db,
            action="document.retry",
            target_type="source_documents",
            actor_type=ActorType.USER,
            actor_user_id=current_user.id,
            actor_role_id=current_user.role_id,
            target_id=doc.id,
            source_document_id=doc.id,
            idempotency_key=idempotency_key,
        )
        db.commit()

        process_document_task.apply_async(args=[str(doc.id), str(new_job.id)])

    elif payload.mode == RetryMode.REOPEN:
        if doc.status != DocumentStatus.REJECTED:
            raise ApiError(
                ErrorCode.CONFLICT_STATE,
                f"Chỉ có thể REOPEN tài liệu ở trạng thái REJECTED (hiện tại: {doc.status.value})",
            )
        if role_code == "ROLE-05":
            pass
        elif role_code == "ROLE-02" and "FIN" in doc.pillars:
            pass
        elif role_code == "ROLE-04" and "HR" in doc.pillars:
            pass
        else:
            raise ApiError(
                ErrorCode.FORBIDDEN_ROLE,
                "Bạn không có quyền mở lại tài liệu này",
            )

        doc.status = DocumentStatus.NEEDS_REVIEW
        doc.status_reason = f"Mở lại: {payload.note or 'Reopen theo yêu cầu'}"
        db.flush()

        record_audit(
            db=db,
            action="document.reopen",
            target_type="source_documents",
            actor_type=ActorType.USER,
            actor_user_id=current_user.id,
            actor_role_id=current_user.role_id,
            target_id=doc.id,
            source_document_id=doc.id,
            idempotency_key=idempotency_key,
        )
        db.commit()

    elif payload.mode == RetryMode.FORCE_DUPLICATE:
        if doc.status != DocumentStatus.DUPLICATE:
            msg = (
                f"Chỉ có thể FORCE_DUPLICATE tài liệu ở trạng thái DUPLICATE "
                f"(hiện tại: {doc.status.value})"
            )
            raise ApiError(ErrorCode.CONFLICT_STATE, msg)
        is_uploader = doc.uploaded_by_id == current_user.id
        if role_code != "ROLE-05" and not is_uploader:
            raise ApiError(
                ErrorCode.FORBIDDEN_ROLE,
                "Chỉ người upload hoặc Reviewer mới có quyền 'Vẫn xử lý' tài liệu trùng",
            )

        max_attempt = max([j.attempt_no for j in doc.extraction_jobs], default=0)
        new_job = ExtractionJob(
            id=uuid4(),
            source_document_id=doc.id,
            attempt_no=max_attempt + 1,
            doc_type=doc.doc_type or DocType.OTHER,
            status=JobStatus.QUEUED,
            started_at=datetime.now(UTC),
        )
        db.add(new_job)
        doc.status = DocumentStatus.PREPROCESSING
        doc.status_reason = f"Vẫn xử lý: {payload.note or ''}"
        db.flush()

        record_audit(
            db=db,
            action="document.force_duplicate",
            target_type="source_documents",
            actor_type=ActorType.USER,
            actor_user_id=current_user.id,
            actor_role_id=current_user.role_id,
            target_id=doc.id,
            source_document_id=doc.id,
            idempotency_key=idempotency_key,
        )
        db.commit()

        process_document_task.apply_async(args=[str(doc.id), str(new_job.id)])
    else:
        raise ApiError(ErrorCode.BAD_REQUEST, f"Chế độ retry không hợp lệ: {payload.mode}")

    doc_out = serialize_document_out(doc, current_user)
    return Envelope(data=doc_out)


@router.get(
    "/review-queue",
    response_model=ReviewQueueResponse,
    summary="Get review queue (EP-28)",
)
def get_review_queue(
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    params: Annotated[PageParams, Depends(get_page_params)],
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    doc_type: Annotated[DocType | None, Query(description="Filter by doc_type")] = None,
    pillar: Annotated[str | None, Query(description="Filter by pillar")] = None,
    batch_id: Annotated[UUID | None, Query(description="Filter by batch_id")] = None,
    confidence_band: Annotated[str | None, Query(description="Filter by confidence band")] = None,
) -> ReviewQueueResponse:
    """EP-28: Prioritized review queue.

    Role scoping:
    - ROLE-05 (Reviewer): sees all.
    - ROLE-01 (CEO): sees all (metadata only for salary documents).
    - ROLE-02 (CFO): FIN pillar only.
    - ROLE-04 (HR Manager): HR pillar only.

    Ordering per FR-DC-16:
    - Blocking cross-document conflict first.
    - Lowest confidence next.
    - Oldest uploaded_at last.
    """
    role_code = current_user.role.code if current_user.role else "ROLE-01"
    base_scope = select(SourceDocument).where(SourceDocument.deleted_at.is_(None))

    if role_code == "ROLE-02":
        base_scope = base_scope.where(SourceDocument.pillars.contains(["FIN"]))
    elif role_code == "ROLE-04":
        base_scope = base_scope.where(SourceDocument.pillars.contains(["HR"]))

    counts_needs_review = (
        db.scalar(
            select(func.count()).select_from(
                base_scope.where(SourceDocument.status == DocumentStatus.NEEDS_REVIEW).subquery()
            )
        )
        or 0
    )
    counts_in_review = (
        db.scalar(
            select(func.count()).select_from(
                base_scope.where(SourceDocument.status == DocumentStatus.IN_REVIEW).subquery()
            )
        )
        or 0
    )
    counts_failed = (
        db.scalar(
            select(func.count()).select_from(
                base_scope.where(SourceDocument.status == DocumentStatus.FAILED).subquery()
            )
        )
        or 0
    )
    counts_out = ReviewQueueCountsOut(
        needs_review=counts_needs_review,
        in_review=counts_in_review,
        failed=counts_failed,
    )

    stmt = base_scope
    if status:
        st_list = [s.strip() for s in status.split(",") if s.strip()]
        enum_sts = []
        for s in st_list:
            try:
                enum_sts.append(DocumentStatus(s))
            except ValueError:
                pass
        if enum_sts:
            stmt = stmt.where(SourceDocument.status.in_(enum_sts))
    else:
        stmt = stmt.where(
            SourceDocument.status.in_(
                [
                    DocumentStatus.NEEDS_REVIEW,
                    DocumentStatus.IN_REVIEW,
                    DocumentStatus.FAILED,
                ]
            )
        )

    if doc_type is not None:
        stmt = stmt.where(SourceDocument.doc_type == doc_type)
    if pillar:
        stmt = stmt.where(SourceDocument.pillars.contains([pillar]))
    if batch_id:
        stmt = stmt.where(SourceDocument.batch_id == batch_id)

    matched_docs = db.execute(stmt).scalars().all()

    items: list[ReviewQueueItemOut] = []
    for doc in matched_docs:
        routing_reason: str | None = None
        avg_confidence: float | None = None
        has_conflict = False
        fields_to_check = 0

        if doc.extraction_jobs:
            sorted_jobs = sorted(doc.extraction_jobs, key=lambda j: j.attempt_no, reverse=True)
            lj = sorted_jobs[0]
            routing_reason = lj.routing_reason
            if lj.avg_confidence is not None:
                avg_confidence = float(lj.avg_confidence)
            if lj.cross_doc_results:
                has_conflict = any(
                    r.get("status") in ("fail", "mismatch") for r in lj.cross_doc_results
                )
            if lj.fields:
                for f in lj.fields:
                    c = float(f.confidence) if f.confidence is not None else 0.0
                    val_fail = any(
                        v.get("status") in ("fail", "warn") for v in (f.validation or [])
                    )
                    if c < 0.90 or f.value is None or val_fail:
                        fields_to_check += 1

        if confidence_band:
            c_val = avg_confidence or 0.0
            band = "HIGH" if c_val >= 0.90 else ("MEDIUM" if c_val >= 0.70 else "LOW")
            if band != confidence_band:
                continue

        locked_by_user = None
        if doc.locked_by_id:
            holder = db.get(User, doc.locked_by_id)
            locked_name = holder.full_name if holder else "Reviewer"
            locked_by_user = UserBrief(id=doc.locked_by_id, full_name=locked_name)

        item = ReviewQueueItemOut(
            document=serialize_document_out(doc, current_user),
            routing_reason=routing_reason,
            avg_confidence=avg_confidence,
            fields_to_check=fields_to_check,
            has_conflict=has_conflict,
            locked_by=locked_by_user,
            locked_until=doc.locked_until,
        )
        items.append(item)

    items.sort(
        key=lambda x: (
            0 if x.has_conflict else 1,
            x.avg_confidence if x.avg_confidence is not None else 0.0,
            x.document.uploaded_at,
        )
    )

    total_items = len(items)
    total_pages = math.ceil(total_items / params.page_size) if total_items > 0 else 0
    paged_items = items[params.offset : params.offset + params.limit]
    meta = ReviewQueueMetaOut(
        page=params.page,
        page_size=params.page_size,
        total=total_items,
        total_pages=total_pages,
        counts=counts_out,
    )
    return ReviewQueueResponse(data=paged_items, meta=meta)


@router.post(
    "/documents/{id}/review/open",
    response_model=Envelope[ReviewOpenOut],
    summary="Open review and lock document for 15 minutes (EP-29)",
)
def open_document_review(
    id: UUID,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-02", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> Envelope[ReviewOpenOut]:
    """EP-29: Open review for a document and acquire 15-minute lock.

    - Transitions NEEDS_REVIEW -> IN_REVIEW.
    - Sets locked_by_id = current_user.id, locked_until = now + 15m.
    - Creates ExtractionReview record.
    - If locked by another user -> 409 REVIEW_LOCKED.
    - If same user -> extends lock.
    """
    doc = db.get(SourceDocument, id)
    if not doc or doc.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Document {id} not found")

    role_code = current_user.role.code if current_user.role else "ROLE-05"
    if role_code == "ROLE-02" and "FIN" not in doc.pillars:
        raise ApiError(ErrorCode.FORBIDDEN_SCOPE, "CFO chỉ có quyền review tài liệu trụ Tài chính")
    if role_code == "ROLE-04" and "HR" not in doc.pillars:
        raise ApiError(
            ErrorCode.FORBIDDEN_SCOPE, "HR Manager chỉ có quyền review tài liệu trụ Con người"
        )

    if doc.status not in (DocumentStatus.NEEDS_REVIEW, DocumentStatus.IN_REVIEW):
        msg = f"Không thể mở review tài liệu ở trạng thái {doc.status.value}"
        raise ApiError(ErrorCode.CONFLICT_STATE, msg)

    now = datetime.now(UTC)
    if doc.locked_by_id and doc.locked_until is not None and doc.locked_until > now:
        if doc.locked_by_id != current_user.id:
            holder = db.get(User, doc.locked_by_id)
            holder_name = holder.full_name if holder else "người dùng khác"
            rem_sec = int((doc.locked_until - now).total_seconds())
            raise ApiError(
                ErrorCode.REVIEW_LOCKED,
                f"Tài liệu đang được khóa bởi {holder_name}",
                details={
                    "locked_by": holder_name,
                    "locked_until": doc.locked_until.isoformat(),
                    "remaining_seconds": rem_sec,
                },
            )
        doc.locked_until = now + timedelta(minutes=15)
    else:
        doc.locked_by_id = current_user.id
        doc.locked_until = now + timedelta(minutes=15)
        doc.status = DocumentStatus.IN_REVIEW

    stmt_rev = (
        select(ExtractionReview)
        .where(
            ExtractionReview.source_document_id == doc.id,
            ExtractionReview.reviewer_id == current_user.id,
            ExtractionReview.decision.is_(None),
        )
        .order_by(desc(ExtractionReview.opened_at))
    )
    active_rev = db.execute(stmt_rev).scalars().first()
    if not active_rev:
        latest_job_id = None
        if doc.extraction_jobs:
            latest_job_id = sorted(doc.extraction_jobs, key=lambda j: j.attempt_no, reverse=True)[
                0
            ].id
        active_rev = ExtractionReview(
            id=uuid4(),
            source_document_id=doc.id,
            extraction_job_id=latest_job_id,
            reviewer_id=current_user.id,
            reviewer_role_id=current_user.role_id,
            opened_at=now,
        )
        db.add(active_rev)

    record_audit(
        db=db,
        action="review.open",
        target_type="source_documents",
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        actor_role_id=current_user.role_id,
        target_id=doc.id,
        source_document_id=doc.id,
    )
    db.commit()

    doc_out = serialize_document_out(doc, current_user)
    extraction = serialize_extraction_result(db=db, doc=doc, current_user=current_user)
    return Envelope(
        data=ReviewOpenOut(
            document=doc_out,
            review_id=active_rev.id,
            extraction=extraction,
        )
    )


@router.post(
    "/documents/{id}/review/release",
    response_model=Envelope[DocumentOut],
    summary="Release review lock without saving (EP-35)",
)
def release_document_review(
    id: UUID,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-02", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> Envelope[DocumentOut]:
    """EP-35: Release review lock and return document to NEEDS_REVIEW.

    Marks any pending ExtractionReview as ABANDONED.
    """
    doc = db.get(SourceDocument, id)
    if not doc or doc.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Document {id} not found")

    if doc.status != DocumentStatus.IN_REVIEW:
        msg = f"Tài liệu không ở trạng thái IN_REVIEW (hiện tại: {doc.status.value})"
        raise ApiError(ErrorCode.CONFLICT_STATE, msg)

    role_code = current_user.role.code if current_user.role else "ROLE-05"
    if doc.locked_by_id != current_user.id and role_code != "ROLE-05":
        raise ApiError(
            ErrorCode.FORBIDDEN_ROLE,
            "Chỉ người giữ khóa hoặc Reviewer mới có quyền giải phóng review",
        )

    now = datetime.now(UTC)
    doc.locked_by_id = None
    doc.locked_until = None
    doc.status = DocumentStatus.NEEDS_REVIEW

    stmt_rev = (
        select(ExtractionReview)
        .where(
            ExtractionReview.source_document_id == doc.id,
            ExtractionReview.decision.is_(None),
        )
        .order_by(desc(ExtractionReview.opened_at))
    )
    active_rev = db.execute(stmt_rev).scalars().first()
    if active_rev:
        active_rev.decision = ReviewDecision.ABANDONED
        active_rev.decided_at = now

    record_audit(
        db=db,
        action="review.release",
        target_type="source_documents",
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        actor_role_id=current_user.role_id,
        target_id=doc.id,
        source_document_id=doc.id,
    )
    db.commit()

    doc_out = serialize_document_out(doc, current_user)
    return Envelope(data=doc_out)


@router.post(
    "/documents/{id}/review/approve",
    response_model=Envelope[ReviewApproveOut],
    summary="Approve and commit document via Action Registry (EP-31)",
)
def approve_document_review(
    id: UUID,
    payload: ReviewApproveRequest,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-02", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[ReviewApproveOut]:
    """EP-31: Duyệt và commit dữ liệu qua Action Registry.

    - Kiểm tra khóa review (phải đang IN_REVIEW và giữ khóa).
    - Mọi field required có confidence LOW hoặc null phải được sửa/xác nhận (EP-30).
    - XD MISMATCH blocking phải được chấp nhận với ghi chú (accepted_conflicts).
    - Commit vào business_records / metric_values + cập nhật COMMITTED + undo 7 ngày.
    """
    doc = db.get(SourceDocument, id)
    if not doc or doc.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Document {id} not found")

    if doc.status != DocumentStatus.IN_REVIEW:
        msg = f"Tài liệu không ở trạng thái IN_REVIEW (hiện tại: {doc.status.value})"
        raise ApiError(ErrorCode.CONFLICT_STATE, msg)

    now = datetime.now(UTC)
    has_valid_lock = (
        doc.locked_by_id == current_user.id
        and doc.locked_until is not None
        and doc.locked_until > now
    )
    if not has_valid_lock:
        holder = db.get(User, doc.locked_by_id) if doc.locked_by_id else None
        holder_name = holder.full_name if holder else "người dùng khác"
        raise ApiError(
            ErrorCode.REVIEW_LOCKED,
            f"Tài liệu đang được khóa bởi {holder_name} hoặc đã hết hạn khóa",
        )

    role_code = current_user.role.code if current_user.role else "ROLE-05"
    if role_code == "ROLE-02" and "FIN" not in doc.pillars:
        raise ApiError(ErrorCode.FORBIDDEN_SCOPE, "CFO chỉ có quyền duyệt tài liệu trụ Tài chính")
    if role_code == "ROLE-04" and "HR" not in doc.pillars:
        raise ApiError(
            ErrorCode.FORBIDDEN_SCOPE, "HR Manager chỉ có quyền duyệt tài liệu trụ Con người"
        )

    review = db.get(ExtractionReview, payload.review_id)
    if not review or review.source_document_id != doc.id:
        msg = f"Review session {payload.review_id} không tồn tại cho tài liệu này"
        raise ApiError(ErrorCode.NOT_FOUND, msg)

    latest_job = None
    if doc.extraction_jobs:
        latest_job = sorted(doc.extraction_jobs, key=lambda j: j.attempt_no, reverse=True)[0]

    unconfirmed_fields: list[str] = []
    if latest_job and latest_job.fields:
        for f in latest_job.fields:
            c = float(f.confidence) if f.confidence is not None else 0.0
            val = f.corrected_value if f.corrected else f.value
            is_low = c < 0.70
            is_empty = val is None or str(val).strip() == ""
            if (is_low or is_empty) and not f.corrected:
                unconfirmed_fields.append(f.field_key)

    if unconfirmed_fields:
        msg = (
            "Các trường bắt buộc có độ tin cậy thấp hoặc chưa có giá trị cần được"
            " sửa/xác nhận trước khi duyệt"
        )
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            msg,
            details={"fields": unconfirmed_fields},
        )

    if latest_job and latest_job.cross_doc_results:
        for xd in latest_job.cross_doc_results:
            st = str(xd.get("status", "")).lower()
            if st in ("fail", "mismatch"):
                rule = str(xd.get("rule", ""))
                accepted = any(
                    ac.rule == rule and bool(ac.note and ac.note.strip())
                    for ac in payload.accepted_conflicts
                )
                if not accepted:
                    raise ApiError(
                        ErrorCode.ACTION_REJECTED,
                        f"Xung đột đối chiếu chéo {rule} chưa được chấp nhận kèm ghi chú",
                        details={
                            "rule": rule,
                            "reason": "Conflict blocking chưa được chấp nhận với ghi chú",
                        },
                    )

    action_name, action_payload = build_action_payload_from_doc(doc, latest_job)
    field_set_version = latest_job.attempt_no if latest_job else 1
    action_res = execute_action(
        db=db,
        action_name=action_name,
        document_id=doc.id,
        payload=action_payload,
        actor=current_user,
        field_set_version=field_set_version,
    )

    doc.status = DocumentStatus.COMMITTED
    doc.committed_at = now
    doc.undo_deadline = now + timedelta(days=7)
    doc.locked_by_id = None
    doc.locked_until = None

    review.decision = ReviewDecision.APPROVED
    review.decided_at = now
    if review.opened_at:
        review.duration_ms = int((now - review.opened_at).total_seconds() * 1000)
    review.fields_corrected = sum(1 for f in latest_job.fields if f.corrected) if latest_job else 0

    record_audit(
        db=db,
        action="review.approve",
        target_type="source_documents",
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        actor_role_id=current_user.role_id,
        target_id=doc.id,
        source_document_id=doc.id,
        metadata={
            "review_id": str(review.id),
            "action_name": action_name,
            "business_record_id": action_res.get("business_record_id"),
        },
    )
    db.commit()

    biz_ids: list[UUID] = []
    if action_res.get("business_record_id"):
        biz_ids.append(UUID(action_res["business_record_id"]))

    metric_ids: list[UUID] = []
    if action_res.get("metric_value_id"):
        metric_ids.append(UUID(action_res["metric_value_id"]))

    doc_out = serialize_document_out(doc, current_user)
    review_out = ReviewApproveReviewOut(
        id=review.id,
        decision="APPROVED",
        decided_at=now,
        duration_ms=review.duration_ms,
        fields_corrected=review.fields_corrected,
    )
    affected_metrics = ["METRIC-FIN-01"]
    if "metric_code" in action_payload:
        affected_metrics = [str(action_payload["metric_code"])]
    commit_out = ReviewApproveCommitOut(
        actions=[
            CommitActionResult(
                action_name=action_name,
                business_record_ids=biz_ids,
                metric_value_ids=metric_ids,
            )
        ],
        affected_metric_codes=affected_metrics,
        recompute_job_id=None,
    )
    return Envelope(
        data=ReviewApproveOut(
            document=doc_out,
            review=review_out,
            commit=commit_out,
        )
    )


@router.post(
    "/documents/{id}/review/reject",
    response_model=Envelope[DocumentOut],
    summary="Reject document in review (EP-32)",
)
def reject_document_review(
    id: UUID,
    payload: ReviewRejectRequest,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-02", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[DocumentOut]:
    """EP-32: Từ chối tài liệu trong review.

    - Bắt buộc reject_reason_code.
    - Nếu reject_reason_code = OTHER, bắt buộc reject_note.
    - Chuyển trạng thái sang REJECTED và giải phóng khóa.
    """
    doc = db.get(SourceDocument, id)
    if not doc or doc.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Document {id} not found")

    if doc.status != DocumentStatus.IN_REVIEW:
        msg = f"Tài liệu không ở trạng thái IN_REVIEW (hiện tại: {doc.status.value})"
        raise ApiError(ErrorCode.CONFLICT_STATE, msg)

    now = datetime.now(UTC)
    has_valid_lock = (
        doc.locked_by_id == current_user.id
        and doc.locked_until is not None
        and doc.locked_until > now
    )
    if not has_valid_lock:
        holder = db.get(User, doc.locked_by_id) if doc.locked_by_id else None
        holder_name = holder.full_name if holder else "người dùng khác"
        raise ApiError(
            ErrorCode.REVIEW_LOCKED,
            f"Tài liệu đang được khóa bởi {holder_name} hoặc đã hết hạn khóa",
        )

    role_code = current_user.role.code if current_user.role else "ROLE-05"
    if role_code == "ROLE-02" and "FIN" not in doc.pillars:
        raise ApiError(ErrorCode.FORBIDDEN_SCOPE, "CFO chỉ có quyền từ chối tài liệu trụ Tài chính")
    if role_code == "ROLE-04" and "HR" not in doc.pillars:
        raise ApiError(
            ErrorCode.FORBIDDEN_SCOPE, "HR Manager chỉ có quyền từ chối tài liệu trụ Con người"
        )

    allowed_reasons = {
        "WRONG_DOC_TYPE",
        "UNREADABLE",
        "DUPLICATE_BUSINESS",
        "WRONG_DATA",
        "SUSPICIOUS_CONTENT",
        "OTHER",
    }
    if payload.reject_reason_code not in allowed_reasons:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            f"Lý do từ chối không hợp lệ: {payload.reject_reason_code}",
        )

    if payload.reject_reason_code == "OTHER" and not (
        payload.reject_note and payload.reject_note.strip()
    ):
        raise ApiError(
            ErrorCode.VALIDATION_ERROR, "reject_note là bắt buộc khi reject_reason_code là OTHER"
        )

    review = db.get(ExtractionReview, payload.review_id)
    if not review or review.source_document_id != doc.id:
        msg = f"Review session {payload.review_id} không tồn tại cho tài liệu này"
        raise ApiError(ErrorCode.NOT_FOUND, msg)

    doc.status = DocumentStatus.REJECTED
    doc.status_reason = f"{payload.reject_reason_code}: {payload.reject_note or ''}"
    doc.locked_by_id = None
    doc.locked_until = None

    review.decision = ReviewDecision.REJECTED
    review.reject_reason_code = payload.reject_reason_code
    review.reject_note = payload.reject_note
    review.decided_at = now
    if review.opened_at:
        review.duration_ms = int((now - review.opened_at).total_seconds() * 1000)

    record_audit(
        db=db,
        action="review.reject",
        target_type="source_documents",
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        actor_role_id=current_user.role_id,
        target_id=doc.id,
        source_document_id=doc.id,
        metadata={
            "review_id": str(review.id),
            "reject_reason_code": payload.reject_reason_code,
            "reject_note": payload.reject_note,
        },
    )
    db.commit()

    doc_out = serialize_document_out(doc, current_user)
    return Envelope(data=doc_out)


@router.post(
    "/documents/{id}/rollback",
    response_model=Envelope[RollbackOut],
    summary="Rollback committed document within undo deadline (EP-33)",
)
def rollback_document(
    id: UUID,
    payload: RollbackDocumentRequest,
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-02", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[RollbackOut]:
    """EP-33: Hoàn tác commit tài liệu trong thời hạn undo (7 ngày).

    - Role: require_role(ROLE-02, ROLE-04, ROLE-05) + review_pillars (CEO không hoàn tác).
    - Header: Idempotency-Key bắt buộc.
    - Điều kiện: status=COMMITTED và now <= undo_deadline.
    - Xử lý: execute_action("document.rollback", payload={"rollback_reason": payload.reason})
      -> soft delete business_records -> ROLLED_BACK -> audit document.rollback.
    - Trả về Envelope[RollbackOut].
    """
    doc = db.get(SourceDocument, id)
    if not doc or doc.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Document {id} not found")

    if doc.status != DocumentStatus.COMMITTED:
        msg = f"Tài liệu không ở trạng thái COMMITTED (hiện tại: {doc.status.value})"
        raise ApiError(ErrorCode.CONFLICT_STATE, msg)

    now = datetime.now(UTC)
    if doc.undo_deadline is None or now > doc.undo_deadline:
        raise ApiError(
            ErrorCode.UNDO_EXPIRED,
            "Thời hạn hoàn tác tài liệu đã hết (tối đa 7 ngày kể từ khi duyệt)",
        )

    role_code = current_user.role.code if current_user.role else "ROLE-05"
    if role_code == "ROLE-02" and "FIN" not in doc.pillars:
        raise ApiError(
            ErrorCode.FORBIDDEN_SCOPE, "CFO chỉ có quyền hoàn tác tài liệu trụ Tài chính"
        )
    if role_code == "ROLE-04" and "HR" not in doc.pillars:
        raise ApiError(
            ErrorCode.FORBIDDEN_SCOPE, "HR Manager chỉ có quyền hoàn tác tài liệu trụ Con người"
        )

    if not payload.reason or not payload.reason.strip():
        raise ApiError(ErrorCode.VALIDATION_ERROR, "Lý do hoàn tác không được để trống")

    latest_job = None
    if doc.extraction_jobs:
        latest_job = sorted(doc.extraction_jobs, key=lambda j: j.attempt_no, reverse=True)[0]
    field_set_version = latest_job.attempt_no if latest_job else 1

    action_res = execute_action(
        db=db,
        action_name="document.rollback",
        document_id=doc.id,
        payload={"rollback_reason": payload.reason.strip()},
        actor=current_user,
        field_set_version=field_set_version,
    )

    doc.locked_by_id = None
    doc.locked_until = None

    record_audit(
        db=db,
        action="document.rollback",
        target_type="source_documents",
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        actor_role_id=current_user.role_id,
        target_id=doc.id,
        source_document_id=doc.id,
        before={"status": DocumentStatus.COMMITTED.value},
        after={"status": DocumentStatus.ROLLED_BACK.value},
        metadata={
            "reason": payload.reason.strip(),
            "rolled_back_records_count": action_res.get("rolled_back_records_count", 0),
        },
    )
    db.commit()

    affected_metrics = ["METRIC-FIN-01"]
    if "HR" in doc.pillars:
        affected_metrics.append("METRIC-HR-01")
    if "CUS" in doc.pillars:
        affected_metrics.append("METRIC-CUS-01")

    doc_out = serialize_document_out(doc, current_user)
    return Envelope(
        data=RollbackOut(
            document=doc_out,
            affected_metric_codes=affected_metrics,
        )
    )


@router.get(
    "/ai-config",
    response_model=Envelope[AiConfigOut],
    summary="Get AI configuration (EP-51, read-only)",
)
def get_ai_config(
    current_user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-05")),
    ],
) -> Envelope[AiConfigOut]:
    """EP-51: Cấu hình AI chỉ đọc (SCR-15).

    - Quyền: require_role(ROLE-01, ROLE-05) - chỉ đọc.
    - ROLE-02..04 -> 403 FORBIDDEN_ROLE.
    - Trả về kill_switch, doc_types, thresholds, source="SEED".
    """
    cfg = get_config()
    kill_switch_out = KillSwitchConfigOut(
        enabled=cfg.ai_kill_switch,
        mode=cfg.ai_kill_switch_mode if cfg.ai_kill_switch else None,
    )
    doc_types_raw = get_all_doc_type_autonomies()
    doc_types_out = [
        DocTypeAutonomyOut(
            doc_type=dt["doc_type"],
            autonomy_level=dt["autonomy_level"],
            max_autonomy_level=dt["max_autonomy_level"],
        )
        for dt in doc_types_raw
    ]
    thresholds_out = ThresholdsConfigOut(
        field_high=0.90,
        field_low=0.70,
        classification_min=0.80,
        stp_classification=0.95,
    )
    return Envelope(
        data=AiConfigOut(
            kill_switch=kill_switch_out,
            doc_types=doc_types_out,
            thresholds=thresholds_out,
            source="SEED",
        )
    )

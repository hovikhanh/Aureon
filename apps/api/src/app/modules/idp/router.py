"""FastAPI router for IDP endpoints (EP-20, EP-40 per 10-API-SPECIFICATION.md §4, §6).
"""

from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Form, Header, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.envelope import Envelope
from app.core.errors import ApiError, ErrorCode
from app.db.enums import ActorType
from app.db.session import get_db
from app.modules.audit.service import record_audit
from app.modules.auth.deps import require_role
from app.modules.auth.models import User
from app.modules.idp.enums import DocType, InputChannel
from app.modules.idp.extraction import (
    change_document_type_and_reextract,
    serialize_extraction_result,
)
from app.modules.idp.models import SourceDocument
from app.modules.idp.preprocessing import split_multi_document
from app.modules.idp.schemas import (
    BatchChecklistItem,
    BatchCreateRequest,
    BatchCreateResponse,
    DocumentOut,
    ExtractionResultOut,
    ExtractionSchemaOut,
    ImportMappingConfirmRequest,
    ManualDocumentCreateRequest,
    NaturalLanguageDocumentCreateRequest,
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


def serialize_document_out(doc: SourceDocument, user: User) -> DocumentOut:
    """Map SQLAlchemy SourceDocument to DocumentOut schema."""
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
        ai_state=None,
        autonomy_level=doc.autonomy_level,
        contains_salary=doc.contains_salary,
        contains_pii=doc.contains_pii,
        duplicate_of_id=doc.duplicate_of_id,
        uploaded_by=UserBrief(id=user.id, full_name=user.full_name),
        uploaded_at=doc.uploaded_at,
        committed_at=doc.committed_at,
        undo_deadline=doc.undo_deadline,
        locked_by=None,
        locked_until=doc.locked_until,
        retry_count=doc.retry_count,
        latest_job=None,
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
        Depends(
            require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")
        ),
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

    doc_out = serialize_document_out(doc, current_user)
    meta: dict[str, Any] | None = None
    if is_duplicate and duplicate_of_id:
        meta = {
            "warning": {
                "code": "DUPLICATE_DOCUMENT",
                "duplicate_of_id": str(duplicate_of_id),
            }
        }

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
        Depends(
            require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")
        ),
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
        Depends(
            require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")
        ),
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
        Depends(
            require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")
        ),
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
        Depends(
            require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")
        ),
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
        Depends(
            require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")
        ),
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
        Depends(
            require_role("ROLE-01", "ROLE-02", "ROLE-04", "ROLE-05")
        ),
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
        Depends(
            require_role("ROLE-02", "ROLE-04", "ROLE-05")
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[ExtractionResultOut]:
    """EP-30: Sửa field, đổi doc_type, chỉnh ranh giới split_ranges.

    Đổi doc_type: xóa fields cũ, trích xuất lại theo schema mới.
    split_ranges: chia tách tài liệu con theo dải trang đã điều chỉnh.
    """
    doc = db.get(SourceDocument, id)
    if not doc or doc.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Document {id} not found")

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

    result = serialize_extraction_result(db=db, doc=doc, current_user=current_user)
    return Envelope(data=result)




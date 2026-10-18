"""FastAPI router for IDP endpoints (EP-20, EP-40 per 10-API-SPECIFICATION.md §4, §6).
"""

from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.envelope import Envelope
from app.db.enums import ActorType
from app.db.session import get_db
from app.modules.audit.service import record_audit
from app.modules.auth.deps import require_role
from app.modules.auth.models import User
from app.modules.idp.enums import DocType, InputChannel
from app.modules.idp.models import SourceDocument
from app.modules.idp.schemas import (
    BatchChecklistItem,
    BatchCreateRequest,
    BatchCreateResponse,
    DocumentOut,
    UserBrief,
)
from app.modules.idp.service import handle_document_upload, process_upload_stream

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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN_ROLE", "message": msg}},
            )

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

"""HTTP routes for `idp` (10 §3.3). EP-20 upload runs the ingest synchronously, then the
pipeline (scan → OCR → extract → validate) runs out of band; the response is `202` with the
created document and job ids (04 §3). Other read endpoints expose the pipeline results.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, File, Query, Response, UploadFile, status

from app.core.concurrency import IfMatch, parse_if_match
from app.core.deps import DbSession, Principal, require_permission
from app.core.envelope import Page
from app.core.errors import NotFoundError
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.idp.schemas import (
    ApproveIn,
    ApproveOut,
    DocumentOut,
    ExtractionResultOut,
    FieldPatchIn,
    FieldPatchOut,
    MergeIn,
    MergeOut,
    ReassignIn,
    ReassignOut,
    RejectIn,
    ReviewDetailOut,
    ReviewOpenOut,
    ReviewQueueItemOut,
    UploadResultOut,
)
from app.modules.idp.services.commit_service import CommitService
from app.modules.idp.services.query_service import IdpQueryService
from app.modules.idp.services.review_service import QueueFilters, ReviewService
from app.modules.idp.services.upload_service import UploadFile as SvcUploadFile
from app.modules.idp.services.upload_service import UploadService

router = EnvelopeRouter(prefix="/idp", tags=["idp"])

IdpWriter = Annotated[Principal, Depends(require_permission("idp", "write"))]
IdpReader = Annotated[Principal, Depends(require_permission("idp", "read"))]
IdpApprover = Annotated[Principal, Depends(require_permission("idp", "approve"))]

_UPLOAD_CHUNK = 1024 * 1024


def _to_svc_file(upload: UploadFile) -> SvcUploadFile:
    def _chunks() -> Iterator[bytes]:
        upload.file.seek(0)
        while True:
            data = upload.file.read(_UPLOAD_CHUNK)
            if not data:
                return
            yield data

    return SvcUploadFile(
        filename=upload.filename,
        content_type=upload.content_type,
        chunks=_chunks(),
    )


@router.post(
    "/documents",
    response_model=UploadResultOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="EP-20 Upload documents (C3/C4, 1..100 files)",
)
async def upload_documents(
    user: IdpWriter,
    db: DbSession,
    idem: Idem,
    files: Annotated[list[UploadFile], File(description="1..100 files")],
) -> UploadResultOut:
    result = await UploadService(db).upload(user, [_to_svc_file(f) for f in files])
    await db.commit()
    # Hand each accepted (non-duplicate) document to the pipeline out of band.
    from app.modules.idp.services.pipeline import enqueue_pipeline

    for doc_id in result.document_ids:
        if doc_id not in result.duplicates:
            enqueue_pipeline(doc_id)
    return UploadResultOut(
        document_ids=result.document_ids,
        job_ids=result.job_ids,
        batch_id=result.batch_id,
        duplicates=result.duplicates,
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentOut,
    summary="EP-25 Document detail",
)
async def get_document(document_id: uuid.UUID, user: IdpReader, db: DbSession) -> DocumentOut:
    doc = await IdpQueryService(db).get_document(user, document_id)
    if doc is None:
        raise NotFoundError("document not found")
    return DocumentOut.model_validate(doc)


@router.get(
    "/documents/{document_id}/extraction",
    response_model=ExtractionResultOut,
    summary="EP-26 Extraction result (field results)",
)
async def get_extraction(
    document_id: uuid.UUID, user: IdpReader, db: DbSession
) -> ExtractionResultOut:
    out = await IdpQueryService(db).get_extraction(user, document_id)
    if out is None:
        raise NotFoundError("extraction result not found")
    return out


# ---------------------------------------------------------------------------
# S4b review workflow (10 §3.11 EP-28..35, §3.12 EP-126/127).
# ---------------------------------------------------------------------------


@router.get(
    "/review-queue",
    response_model=list[ReviewQueueItemOut],
    summary="EP-28 Review queue (paginated, filterable, dept-scoped)",
)
async def review_queue(
    user: IdpApprover,
    db: DbSession,
    page: Annotated[PageParams, Depends(page_params("created_at", "submitted_at"))],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    document_type: Annotated[str | None, Query()] = None,
    assigned_to: Annotated[uuid.UUID | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
) -> Page[ReviewQueueItemOut]:
    from datetime import datetime

    filters = QueueFilters(
        status=status_filter,
        document_type=document_type,
        assigned_to=assigned_to,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
    )
    items, total = await ReviewService(db).queue(user, page, filters)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get(
    "/documents/{document_id}/review",
    response_model=ReviewDetailOut,
    summary="Review detail — fields + confidence + validation + lineage",
)
async def review_detail(
    document_id: uuid.UUID, user: IdpApprover, db: DbSession
) -> ReviewDetailOut:
    return await ReviewService(db).detail(user, document_id)


@router.post(
    "/documents/{document_id}/review/open",
    response_model=ReviewOpenOut,
    summary="EP-29 Open review (15-min soft lock)",
)
async def review_open(
    document_id: uuid.UUID, user: IdpApprover, db: DbSession, idem: Idem
) -> ReviewOpenOut:
    out = await ReviewService(db).open(user, document_id)
    await db.commit()
    return out


@router.patch(
    "/documents/{document_id}/fields",
    response_model=FieldPatchOut,
    summary="EP-30 Correct/confirm fields (validation recompute)",
)
async def patch_fields(
    document_id: uuid.UUID,
    body: FieldPatchIn,
    user: IdpApprover,
    db: DbSession,
    if_match: IfMatch = None,
) -> FieldPatchOut:
    parse_if_match(if_match)  # validates header shape if present (optional on PATCH here)
    out = await ReviewService(db).patch_fields(user, document_id, body)
    await db.commit()
    return out


@router.post(
    "/documents/{document_id}/review/approve",
    response_model=ApproveOut,
    summary="EP-31 Approve + commit to domain via Action Registry",
)
async def review_approve(
    document_id: uuid.UUID,
    body: ApproveIn,
    user: IdpApprover,
    db: DbSession,
    idem: Idem,
    if_match: IfMatch = None,
) -> ApproveOut:
    exp = parse_if_match(if_match)
    out = await CommitService(db).approve(
        user,
        document_id,
        comment=body.comment,
        expected_version=exp if exp is not None else body.version,
    )
    await db.commit()
    return out


@router.post(
    "/documents/{document_id}/review/reject",
    response_model=DocumentOut,
    summary="EP-32 Reject (reason required)",
)
async def review_reject(
    document_id: uuid.UUID, body: RejectIn, user: IdpApprover, db: DbSession, idem: Idem
) -> DocumentOut:
    out = await ReviewService(db).reject(user, document_id, body.reason)
    await db.commit()
    return out


@router.post(
    "/documents/{document_id}/review/release",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="EP-35 Release review (no save)",
)
async def review_release(document_id: uuid.UUID, user: IdpApprover, db: DbSession) -> Response:
    await ReviewService(db).release(user, document_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/documents/{document_id}/review/reassign",
    response_model=ReassignOut,
    summary="EP-126 Reassign reviewer (ACT-reassign_review)",
)
async def review_reassign(
    document_id: uuid.UUID, body: ReassignIn, user: IdpApprover, db: DbSession, idem: Idem
) -> ReassignOut:
    out = await ReviewService(db).reassign(
        user,
        document_id,
        to_user_id=body.to_user_id,
        to_role_code=body.to_role_code,
        reason=body.reason,
    )
    await db.commit()
    return out


@router.post(
    "/review-queue/merge",
    response_model=MergeOut,
    summary="EP-127 Merge documents into one review (ACT-merge_review)",
)
async def review_merge(body: MergeIn, user: IdpApprover, db: DbSession, idem: Idem) -> MergeOut:
    parent, children = await ReviewService(db).merge(user, body.document_ids, body.primary_id)
    await db.commit()
    return MergeOut(parent=parent, children=children)

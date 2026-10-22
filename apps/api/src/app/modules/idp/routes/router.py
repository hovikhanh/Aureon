"""HTTP routes for `idp` (10 §3.3). EP-20 upload runs the ingest synchronously, then the
pipeline (scan → OCR → extract → validate) runs out of band; the response is `202` with the
created document and job ids (04 §3). Other read endpoints expose the pipeline results.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, File, UploadFile, status

from app.core.deps import DbSession, Principal, require_permission
from app.core.errors import NotFoundError
from app.core.idempotency import Idem
from app.core.routing import EnvelopeRouter
from app.modules.idp.schemas import DocumentOut, ExtractionResultOut, UploadResultOut
from app.modules.idp.services.query_service import IdpQueryService
from app.modules.idp.services.upload_service import UploadFile as SvcUploadFile
from app.modules.idp.services.upload_service import UploadService

router = EnvelopeRouter(prefix="/idp", tags=["idp"])

IdpWriter = Annotated[Principal, Depends(require_permission("idp", "write"))]
IdpReader = Annotated[Principal, Depends(require_permission("idp", "read"))]

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

"""T-640 test helpers — confirm every critical field (FR-DC-16) before approve."""

import uuid

from sqlalchemy import select

from app.core.deps import Principal
from app.modules.idp.models import ExtractedField, ExtractionJob
from app.modules.idp.schemas import FieldCorrectionIn, FieldPatchIn
from app.modules.idp.services.review_service import ReviewService


async def critical_ids(db, doc_id: uuid.UUID) -> list[uuid.UUID]:
    stmt = (
        select(ExtractedField.id)
        .join(ExtractionJob, ExtractionJob.id == ExtractedField.extraction_job_id)
        .where(ExtractionJob.source_document_id == doc_id, ExtractedField.is_critical.is_(True))
    )
    return list((await db.execute(stmt)).scalars())


async def confirm_critical(db, user: Principal, doc_id: uuid.UUID, *, opened: bool = False) -> None:
    """Service path: open (soft lock) + EP-30 `confirm` on every critical field."""
    svc = ReviewService(db)
    if not opened:
        await svc.open(user, doc_id)
    edits = [
        FieldCorrectionIn(field_id=i, action="confirm") for i in await critical_ids(db, doc_id)
    ]
    await svc.patch_fields(user, doc_id, FieldPatchIn(fields=edits))


async def approve_http(api, db, role: str, doc_id: str) -> object:
    """HTTP path: EP-DC-06 open + EP-DC-07 confirm every critical field + EP-DC-08 approve,
    all as one user (the soft lock is per user)."""
    uid = uuid.uuid4()
    base = f"/api/v1/idp/documents/{doc_id}"
    r = await api.http.post(f"{base}/review/open", json={},
                            headers=api.headers(role, user_id=uid, idem=True))  # fmt: skip
    assert r.status_code == 200, r.text
    ids = await critical_ids(db, uuid.UUID(str(doc_id)))
    body = {"fields": [{"field_id": str(i), "action": "confirm"} for i in ids]}
    r = await api.http.patch(f"{base}/fields", json=body, headers=api.headers(role, user_id=uid))
    assert r.status_code == 200, r.text
    return await api.http.post(f"{base}/review/approve", json={},
                               headers=api.headers(role, user_id=uid, idem=True))  # fmt: skip

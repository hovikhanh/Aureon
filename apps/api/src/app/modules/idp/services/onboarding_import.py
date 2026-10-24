"""`idp` reader of the onboarding org import commit state (`core/onboarding`, 05 §2.8).

Step `review` of UC-07 is `done` once the `org_import` C5 document is `COMMITTED`; `platform`
asks through `core/onboarding.import_committed_at` (it may not import `idp`). Ids only.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.idp.repositories import ImportRepository, SourceDocumentRepository


async def import_committed_at(
    db: AsyncSession, batch_id: uuid.UUID | None, document_id: uuid.UUID | None
) -> str | None:
    doc_id = document_id
    if doc_id is None and batch_id is not None:
        batch = await ImportRepository(db).excel_batch(batch_id)  # tenant-scoped
        doc_id = batch.source_document_id if batch else None
    doc = await SourceDocumentRepository(db).by_id(doc_id) if doc_id else None
    if doc is None or doc.status != "COMMITTED":
        return None
    at = doc.committed_at
    return at.isoformat().replace("+00:00", "Z") if at else None

"""Celery tasks for the IDP pipeline (T-206; 07 §3.1, §5.1)."""

import logging
from typing import Any
from uuid import UUID

from app.db.session import SessionLocal
from app.modules.idp.preprocessing import preprocess_document
from app.worker import QUEUE_IDP, celery_app
from app.workers.base import IdempotentTask

logger = logging.getLogger(__name__)


@celery_app.task(  # type: ignore[untyped-decorator]
    base=IdempotentTask,
    bind=True,
    name="app.workers.idp.preprocess_document",
    queue=QUEUE_IDP,
)
def preprocess_document_task(
    self: Any, document_id: str, db: Any = None
) -> dict[str, Any]:
    """Execute step 1 (preprocessing & OCR) for a source document."""
    logger.info("Starting preprocess_document_task for doc %s", document_id)
    doc_uuid = UUID(document_id)
    if db is not None:
        doc = preprocess_document(db=db, doc_id=doc_uuid)
    else:
        with SessionLocal() as session:
            doc = preprocess_document(db=session, doc_id=doc_uuid)
    return {
        "document_id": str(doc.id),
        "status": doc.status.value,
        "page_count": doc.page_count,
    }

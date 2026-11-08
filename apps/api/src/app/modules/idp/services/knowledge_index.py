"""Page embeddings for Knowledge search (F-H2, R-DEC-141, DEC-142 bge-m3).

`index_document` runs at the end of the pipeline; `index_pending` is the backfill job, also
callable as `python -m app.modules.idp.services.knowledge_index [limit]`. Vectors come from
`ModelGateway.embed`, which only ever uses the local provider. Level-4 documents are skipped:
SECRET goes to no model, embedding included.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.core.model_gateway import ModelGateway
from app.core.model_gateway.sinks import session_sink
from app.modules.idp.models import DocumentPage
from app.modules.idp.repositories import DocumentPageSearchRepository

MAX_EMBED_SENSITIVITY = 3
MAX_PAGE_CHARS = 2000  # bge-m3 reads a page opening fine; a page is one vector at P0
BATCH = 8
PIPELINE_EMBED_TIMEOUT_S = 30.0  # inside a document run; the backfill uses the normal timeout


class KnowledgeIndexService:
    def __init__(self, db: AsyncSession, gateway: Any = None) -> None:
        self.db = db
        self.gateway = gateway or ModelGateway(session_sink(db))
        self.repo = DocumentPageSearchRepository(db)

    async def _embed(self, pages: Sequence[DocumentPage], *, timeout_s: float | None = None) -> int:
        model = get_config().embedding_model
        for start in range(0, len(pages), BATCH):
            batch = pages[start : start + BATCH]
            texts = [(p.text_content or "")[:MAX_PAGE_CHARS] for p in batch]
            vectors = await self.gateway.embed(texts, caller_module="idp", timeout_s=timeout_s)
            for page, vector in zip(batch, vectors, strict=True):
                page.embedding = vector
                page.embedding_model = model
        await self.db.flush()
        return len(pages)

    async def index_document(self, document_id: uuid.UUID) -> int:
        return await self._embed(await self.repo.pages_to_embed(
            document_id=document_id, limit=1000, max_sensitivity=MAX_EMBED_SENSITIVITY,
        ), timeout_s=PIPELINE_EMBED_TIMEOUT_S)  # fmt: skip

    async def index_pending(self, *, limit: int = 200) -> int:
        return await self._embed(await self.repo.pages_to_embed(
            document_id=None, limit=limit, max_sensitivity=MAX_EMBED_SENSITIVITY,
        ))  # fmt: skip


async def _main(limit: int) -> None:  # pragma: no cover - operator entry point
    import importlib

    from app.core.base_model import DEFAULT_TENANT_ID
    from app.core.db import get_sessionmaker
    from app.core.tenant import tenant_scope

    importlib.import_module("app.modules.ai")  # registers the model-call log sink
    with tenant_scope(DEFAULT_TENANT_ID):
        async with get_sessionmaker()() as db:
            done = await KnowledgeIndexService(db).index_pending(limit=limit)
            await db.commit()
    print(f"embedded {done} page(s)")


if __name__ == "__main__":  # pragma: no cover
    import asyncio
    import sys

    asyncio.run(_main(int(sys.argv[1]) if len(sys.argv) > 1 else 200))

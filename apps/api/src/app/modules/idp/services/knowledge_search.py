"""Knowledge / document search (M3.4, T-828, R-DEC-141/142b) — EP-24 + `TOOL-search_documents`.

One engine behind both the HTTP endpoint and the AI tool. Semantic when embeddings are enabled
(`embedding_model` set) and usable: embed the query via the gateway and order
`idp.document_pages` by pgvector cosine distance (`<=>`). When the embedding call fails or no page
has a vector yet, search falls back to keyword `ILIKE` over the page text (F-H2): the phrase, then
any of its words. An embedding outage never fails a search. `last_mode` says which engine answered.
Results are always scoped to what the caller may see
(reuses the EP-DC-13 `inbox_filter`), and expose a page `SourceRef` (document_id + page_number),
never a raw storage URL (05 §11). The snippet is a short excerpt around the match.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.core.deps import Principal
from app.core.errors import AIError
from app.core.model_gateway import ModelGateway
from app.core.model_gateway.sinks import session_sink
from app.modules.idp.models import SourceDocument
from app.modules.idp.repositories import DocumentPageSearchRepository
from app.modules.idp.schemas import DocumentSearchHit
from app.modules.idp.services.scope import inbox_filter

log = logging.getLogger(__name__)

SNIPPET_LEN = 200
EMBED_QUERY_TIMEOUT_S = 3.0  # inside the 5 s tool budget; a slower model falls back to keyword
_MIN_TERM = 3


def _snippet(text: str | None, query: str) -> str:
    if not text:
        return ""
    body = " ".join(text.split())
    low = body.casefold()
    idx = low.find(query.casefold().strip())
    if idx < 0:
        return body[:SNIPPET_LEN] + ("…" if len(body) > SNIPPET_LEN else "")
    start = max(0, idx - SNIPPET_LEN // 4)
    end = min(len(body), start + SNIPPET_LEN)
    return ("…" if start > 0 else "") + body[start:end] + ("…" if end < len(body) else "")


class KnowledgeSearchService:
    def __init__(self, db: AsyncSession, gateway: ModelGateway | None = None) -> None:
        self.db = db
        self.gateway = gateway or ModelGateway(session_sink(db))
        self.repo = DocumentPageSearchRepository(db)
        self.last_mode = "keyword"

    @property
    def semantic_enabled(self) -> bool:
        return bool(get_config().embedding_model)

    async def _semantic(self, scope: Any, q: str, limit: int, offset: int) -> tuple[Any, int]:
        try:
            vecs = await self.gateway.embed([q], caller_module="idp",
                                            timeout_s=EMBED_QUERY_TIMEOUT_S)  # fmt: skip
        except AIError as exc:
            log.warning("knowledge search: embedding unavailable (%s), keyword only", exc.code)
            return [], 0
        return await self.repo.semantic(scope, vecs[0], limit=limit, offset=offset)

    async def _keyword(self, scope: Any, q: str, limit: int, offset: int) -> tuple[Any, int]:
        rows, total = await self.repo.keyword(scope, f"%{q}%", limit=limit, offset=offset)
        terms = [t for t in re.findall(r"\w+", q) if len(t) >= _MIN_TERM]
        if rows or len(terms) < 2:
            return rows, total
        return await self.repo.keyword_any(scope, terms, limit=limit, offset=offset)

    async def search(
        self, user: Principal, query: str, *, limit: int = 10, offset: int = 0,
        max_sensitivity: int | None = None,
    ) -> tuple[list[DocumentSearchHit], int]:  # fmt: skip
        """`max_sensitivity` bounds what may reach a model: the AI tool passes 3 (SECRET documents
        never enter a prompt); the HTTP endpoint keeps the caller's document scope."""
        q = (query or "").strip()
        if not q:
            raise ValueError("empty search query")
        limit = max(1, min(limit, 20))

        scope = await inbox_filter(self.db, user)
        if max_sensitivity is not None:
            bound = SourceDocument.sensitivity_level <= max_sensitivity
            scope = bound if scope is None else and_(scope, bound)
        rows: Any = []
        total = 0
        if self.semantic_enabled:
            rows, total = await self._semantic(scope, q, limit, offset)
            self.last_mode = "semantic"
        if not rows:
            rows, total = await self._keyword(scope, q, limit, offset)
            self.last_mode = "keyword"
        hits = [
            DocumentSearchHit(
                document_id=r[0],
                title=r[3] or "(no title)",
                doc_type=r[4],
                page_number=r[1],
                snippet=_snippet(r[2], q),
                score=round(float(r[5]), 4),
            )
            for r in rows
        ]
        return hits, total

    async def as_source_refs(
        self, user: Principal, query: str, *, limit: int = 5
    ) -> list[dict[str, object]]:
        """Shape for `TOOL-search_documents`: page SourceRefs (no raw URL to the LLM, 05 §11)."""
        hits, _ = await self.search(user, query, limit=limit)
        return [
            {
                "type": "document_page",
                "id": f"{h.document_id}#p{h.page_number}",
                "label": f"{h.title} · tr.{h.page_number}",
                "document_id": str(h.document_id),
                "page_number": h.page_number,
                "snippet": h.snippet,
                "score": h.score,
            }
            for h in hits
        ]

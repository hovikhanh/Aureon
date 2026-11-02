"""Knowledge / document search (M3.4, T-828, R-DEC-141/142b) — EP-24 + `TOOL-search_documents`.

One engine behind both the HTTP endpoint and the AI tool. Semantic when embeddings are enabled
(`embedding_model` set): embed the query via the gateway and order `idp.document_pages` by
pgvector cosine distance (`<=>`); otherwise fall back to a keyword `ILIKE` over the page text
(R-DEC-141 — gated off, never fabricates). Results are always scoped to what the caller may see
(reuses the EP-DC-13 `inbox_filter`), and expose a page `SourceRef` (document_id + page_number),
never a raw storage URL (05 §11). The snippet is a short excerpt around the match.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.core.deps import Principal
from app.core.model_gateway import ModelGateway
from app.core.model_gateway.sinks import session_sink
from app.modules.idp.repositories import DocumentPageSearchRepository
from app.modules.idp.schemas import DocumentSearchHit
from app.modules.idp.services.scope import inbox_filter

SNIPPET_LEN = 200


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

    @property
    def semantic_enabled(self) -> bool:
        return bool(get_config().embedding_model)

    async def search(
        self, user: Principal, query: str, *, limit: int = 10, offset: int = 0
    ) -> tuple[list[DocumentSearchHit], int]:
        q = (query or "").strip()
        if not q:
            raise ValueError("empty search query")
        limit = max(1, min(limit, 20))

        scope = await inbox_filter(self.db, user)
        if self.semantic_enabled:
            vec = (await self.gateway.embed([q], caller_module="idp"))[0]
            rows, total = await self.repo.semantic(scope, vec, limit=limit, offset=offset)
        else:
            rows, total = await self.repo.keyword(scope, f"%{q}%", limit=limit, offset=offset)
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

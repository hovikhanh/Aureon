"""Document classifier — 4 tiers (R-DEC-65, 04 §3.2 step 4, FR-DC-09).

1. `type_preselected` — the user chose the type (EP-DC-01 `document_type` / C1 form): confidence
   1.0, no classification at all.
2. C5 header heuristic — header cells vs `header_aliases` of each active published schema;
   ≥ 60 % of the required fields matched → confidence = matched/required share.
3. Keywords — `document_types.classifier_keywords` (Admin, EP-DC-28) in the text.
4. LLM `task="classify"` via the ModelGateway (fixture in dev/CI), content wrapped in
   `<<<DATA…DATA>>>`; answer must be `{code, confidence}` with `code` in the active set.

The caller routes `< 0.95` to `NEEDS_REVIEW` (the reviewer picks the type). Nothing found →
`OTHER`.
"""

from __future__ import annotations

import logging
import unicodedata
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.model_gateway import ChatRequest, ChatResponse, Message
from app.core.model_gateway.errors import FixtureMissingError, TemplateRequired
from app.modules.idp.models import DocumentType, ExtractionSchema

log = logging.getLogger(__name__)

HEADER_MIN_SHARE = 0.60
FALLBACK = "OTHER"
_KEYWORD_BASE, _KEYWORD_STEP, _KEYWORD_CAP = 0.80, 0.05, 0.94  # keywords alone never reach STP
_INVOICE_HINTS = ("hoa don", "invoice", "vat", "gtgt", "mst", "tien thue")
_MAX_LLM_CHARS = 6000


class _Gateway(Protocol):
    async def chat(self, req: ChatRequest) -> ChatResponse: ...


@dataclass(frozen=True)
class Classification:
    code: str
    confidence: float
    tier: str  # preselected | header | keyword | llm | fallback


@dataclass(frozen=True)
class _Candidate:
    code: str
    keywords: tuple[str, ...]
    fields: tuple[dict[str, Any], ...]


def fold(text: str) -> str:
    """Lower-case, strip Vietnamese diacritics (đ→d) and collapse whitespace."""
    s = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.split())


def header_score(headers: list[str], fields: tuple[dict[str, Any], ...]) -> float:
    """Share of the schema's required fields whose name/alias equals a header cell."""
    cells = {fold(h) for h in headers if h and h.strip()}
    required = [f for f in fields if f.get("required")]
    if not required or not cells:
        return 0.0
    hit = sum(1 for f in required
              if {fold(a) for a in [f["name"], *f.get("header_aliases", [])]} & cells)  # fmt: skip
    return round(hit / len(required), 4)


def keyword_score(text: str, keywords: tuple[str, ...]) -> float:
    folded = fold(text)
    hits = sum(1 for k in keywords if k and fold(k) in folded)
    if hits < 2:  # one stray word is not evidence
        return 0.0
    return round(min(_KEYWORD_BASE + _KEYWORD_STEP * (hits - 2), _KEYWORD_CAP), 4)


def invoice_score(text: str) -> float:
    """Built-in INVOICE hints (v2.1 reference type, kept until its keywords are configured)."""
    folded = fold(text)
    hits = sum(1 for h in _INVOICE_HINTS if h in folded)
    return round(min(0.90 + 0.02 * hits, 0.99), 4) if hits >= 2 else 0.0


class Classifier:
    def __init__(self, db: AsyncSession, gateway: _Gateway | None = None) -> None:
        self.db = db
        self.gateway = gateway

    async def candidates(self) -> list[_Candidate]:
        rows = (await self.db.execute(
            select(DocumentType.code, DocumentType.classifier_keywords, ExtractionSchema.fields)
            .join(ExtractionSchema, ExtractionSchema.id == DocumentType.current_schema_id)
            .where(DocumentType.is_active.is_(True), ExtractionSchema.status == "published")
            .order_by(DocumentType.code)
        )).all()  # fmt: skip
        return [_Candidate(c, tuple(k or ()), tuple(f or ())) for c, k, f in rows]

    async def classify(
        self, text: str, *, preselected: str | None = None, headers: list[str] | None = None,
        document_id: uuid.UUID | None = None, classification: str = "INTERNAL",
    ) -> Classification:  # fmt: skip
        if preselected:
            return Classification(preselected, 1.0, "preselected")
        cands = await self.candidates()
        if headers:
            best = max(((header_score(headers, c.fields), c.code) for c in cands), default=None)
            if best and best[0] >= HEADER_MIN_SHARE:
                return Classification(best[1], best[0], "header")
        scored = [(keyword_score(text, c.keywords), c.code) for c in cands]
        scored.append((invoice_score(text), "INVOICE"))
        score, code = max(scored, default=(0.0, FALLBACK))
        if score >= 0.95 or (score > 0 and self.gateway is None):
            return Classification(code, score, "keyword")
        if self.gateway is not None and classification != "SECRET":
            llm = await self._llm(text, [c.code for c in cands], document_id, classification)
            if llm is not None and llm.confidence > score:
                return llm
        if score > 0:
            return Classification(code, score, "keyword")
        return Classification(FALLBACK, 0.5, "fallback")

    async def _llm(
        self, text: str, codes: list[str], document_id: uuid.UUID | None, classification: str
    ) -> Classification | None:
        system = ("Bạn phân loại tài liệu doanh nghiệp. Chỉ trả JSON {code, confidence} với code "
                  "thuộc danh sách cho trước; không chắc thì code=OTHER.")  # fmt: skip
        user = f"Danh sách loại: {', '.join(codes)}\n<<<DATA\n{text[:_MAX_LLM_CHARS]}\nDATA>>>"
        req = ChatRequest(
            task="classify", caller_module="idp", source_document_id=document_id,
            messages=(Message("system", system), Message("user", user)),
            classification=classification,  # type: ignore[arg-type]
            json_schema={"type": "object", "required": ["code", "confidence"], "properties": {
                "code": {"type": "string", "enum": codes},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1}}},
        )  # fmt: skip
        try:
            resp = await self.gateway.chat(req)  # type: ignore[union-attr]
        except (FixtureMissingError, TemplateRequired, AppError) as exc:  # degrade to tiers 2–3
            log.warning("idp classify: LLM tier unavailable (%s)", type(exc).__name__)
            return None
        data = resp.data if isinstance(resp.data, dict) else {}
        code, conf = data.get("code"), data.get("confidence")
        if code not in codes or not isinstance(conf, (int, float)):  # answer outside the set
            return None
        return Classification(str(code), round(max(0.0, min(float(conf), 1.0)), 4), "llm")

"""LLM extraction (04 §3 step 6, §5, FR-DC-11). Builds a schema-driven prompt from the page
text and asks the ModelGateway (`task="extract"`) for structured output; every field becomes a
field result `{value, raw_text, confidence, source_location, confidence_band}` (§5.1). Missing
fields are `null` with confidence 0 — never fabricated (P05, §5.1).

Classification routing (04 §7.4, DEC-157, D-11) is the gateway's job: CONFIDENTIAL → local LLM,
SECRET → blocked (no LLM). We pass `classification` derived from the document's sensitivity level.
Documents start at level 3 and only ever go up (`Pipeline`), so a document never reaches a cloud
model; the extract prompt is not PII-scrubbed because the level-4 documents never reach any model
and a local model needs the identifiers it is asked to extract.

`source_location.page` is the page where the value was actually found in the text, or `null` when
it cannot be located (a value the model produced that is not in the document is a review signal,
not page 1). Field confidence is the model's self-report, uncalibrated (04 §5.1).

The gateway is injected so the HTTP/pipeline path is testable without a live provider
(same DI pattern as chat, DEC-233): a test supplies a fake gateway returning `ChatResponse`
with `data` = the extracted field map.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.core.model_gateway import ChatRequest, ChatResponse, Message
from app.modules.idp.services.critical import is_critical

# DEC-133 confidence bands.
HIGH, MEDIUM, LOW = "HIGH", "MEDIUM", "LOW"


def confidence_band(confidence: float) -> str:
    if confidence >= 0.90:
        return HIGH
    if confidence >= 0.60:
        return MEDIUM
    return LOW


def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _digit_tokens(text: str) -> set[str]:
    """Numbers in a page, grouping removed: `275.000.000 đ` → `275000000`."""
    return {re.sub(r"\D", "", t) for t in re.findall(r"\d[\d.,]*\d|\d", text)}


def _digits_of(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if re.fullmatch(r"[\d.,\s]+", text):
        digits = re.sub(r"\D", "", text)
        return digits if len(digits) >= 3 else None
    return None


def _date_forms(value: str) -> list[str]:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value.strip())
    return [f"{m[3]}/{m[2]}/{m[1]}", f"{m[3]}-{m[2]}-{m[1]}"] if m else []


def locate_page(pages: Sequence[tuple[int, str]], value: Any, raw_text: Any = None) -> int | None:
    """First page holding `raw_text` or `value`, comparing numbers without their grouping and ISO
    dates in their printed form. Too short to be evidence, or found nowhere → `None`."""
    for needle in (raw_text, value):
        if needle is None or isinstance(needle, bool):
            continue
        digits = _digits_of(needle)
        text = _norm(str(needle))
        forms = [text, *(_norm(d) for d in _date_forms(str(needle)))]
        for number, body in pages:
            if digits is not None and digits in _digit_tokens(body):
                return number
            if len(text) >= 2 and any(f in _norm(body) for f in forms):
                return number
    return None


def normalize_value(value: Any, value_type: str) -> Any:
    """The model's text → the schema's type, only when the whole value parses: `250.000.000 đ`
    (money) → 250000000, `10%` (percent) → 10, `12/09/2026` (date) → `2026-09-12`. A local model
    copies the printed form; validators and ACTs expect the typed one. Anything else is left as
    it is, for validation and the reviewer to see."""
    if not isinstance(value, str):
        return value
    text = value.strip()
    if value_type == "money":
        m = re.fullmatch(r"(\d{1,3}(?:[.,\s]\d{3})+|\d+)\s*(?:đ|đồng|vnd|vnđ)?", text, re.I)
        return int(re.sub(r"\D", "", m[1])) if m else value
    if value_type in ("percent", "number"):
        m = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*%?", text)
        if not m:
            return value
        number = float(m[1].replace(",", "."))
        return int(number) if number.is_integer() else number
    if value_type == "date":
        m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
        return f"{m[3]}-{int(m[2]):02d}-{int(m[1]):02d}" if m else value
    return value


def classification_for_sensitivity(level: int) -> str:
    """Map sensitivity level (1–4) to a ModelGateway classification (04 §7.4, 02 §5.3)."""
    if level >= 4:
        return "SECRET"  # salary/health → no LLM
    if level == 3:
        return "CONFIDENTIAL"  # PII → local only
    if level == 2:
        return "INTERNAL"
    return "PUBLIC"


@dataclass
class ExtractedFieldResult:
    field_name: str
    value_type: str
    value: Any
    raw_text: str | None
    confidence: float
    confidence_band: str
    is_critical: bool
    sensitivity_level: int
    source_location: dict[str, Any]
    row_index: int | None = None


@dataclass
class ExtractionOutput:
    fields: list[ExtractedFieldResult] = field(default_factory=list)
    document_confidence: float = 0.0
    provider: str | None = None
    model: str | None = None


class Extractor:
    def __init__(self, gateway: Any) -> None:
        self.gateway = gateway

    async def extract(
        self,
        *,
        schema_fields: list[dict[str, Any]],
        page_text: str,
        sensitivity_level: int,
        document_id: uuid.UUID | None = None,
        pages: Sequence[tuple[int, str]] | None = None,
    ) -> ExtractionOutput:
        classification = classification_for_sensitivity(sensitivity_level)
        req = self._build_request(schema_fields, page_text, classification, document_id)
        # Structured output: `extract()` guarantees `resp.data` is the parsed JSON field map
        # (it parses `content` for a live provider; a test/fake gateway that already sets `data`
        # in `chat()` is returned unchanged). Calling `chat()` here left `data=None` for a live
        # provider — every field parsed as null (bug only visible outside fixture mode).
        resp: ChatResponse = await self._call(req)
        return self._parse(resp, schema_fields, pages or [(1, page_text)])

    async def _call(self, req: ChatRequest) -> ChatResponse:
        """Prefer the gateway's structured-output path; fall back to `chat` for a fake gateway
        that only implements `chat` (and already returns `data`)."""
        extract = getattr(self.gateway, "extract", None)
        resp: ChatResponse = await (extract(req) if callable(extract) else self.gateway.chat(req))
        return resp

    def _build_request(
        self,
        schema_fields: list[dict[str, Any]],
        page_text: str,
        classification: str,
        document_id: uuid.UUID | None,
    ) -> ChatRequest:
        names = [f["name"] for f in schema_fields]
        field_props = {
            f["name"]: {
                "type": "object",
                "properties": {
                    "value": {},
                    "raw_text": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                },
                # A local model under a grammar drops what is optional: an absent confidence
                # read as 0 and sent a correct extraction to review as "low confidence".
                "required": ["value", "confidence"],
            }
            for f in schema_fields
        }
        # A document may carry several records of the same shape (R-DEC-99: a meeting minutes has
        # many action items, a roster many rows). The model returns `rows: [...]`, one object per
        # record; a single-record document may also return the fields flat (both parsed).
        json_schema = {
            "type": "object",
            "properties": {
                **field_props,
                "rows": {"type": "array", "items": {"type": "object", "properties": field_props}},
            },
        }
        # Output is bounded (≤ 2048 tokens, CLAUDE.md §5.5) — ask for the compact form: minified
        # JSON, no fence, rows only when there are several records, short raw_text (R-DEC-164).
        # A field left out parses as value=null, confidence=0 (`_field`), so nulls are not written.
        system = (
            "Bạn trích xuất dữ liệu có cấu trúc từ tài liệu. Chỉ trả về các trường yêu cầu; "
            "trường không tìm thấy thì bỏ hẳn, không ghi null. Không bịa số (P05). Nếu tài liệu "
            "có nhiều bản ghi cùng loại (vd nhiều việc cần làm), chỉ trả mảng `rows`, mỗi phần "
            "tử là một bản ghi, không lặp lại các trường ở cấp ngoài. Trả JSON thu gọn trên một "
            "dòng, không markdown, không khối ```; chỉ ghi `raw_text` khi khác `value` (tối đa "
            "40 ký tự)."
        )
        # Document content is wrapped as DATA, not instructions (04 §2.3, no tool calling).
        user = f"Các trường cần trích: {', '.join(names)}\n<<<DATA\n{page_text}\nDATA>>>"
        return ChatRequest(
            task="extract",
            messages=(Message("system", system), Message("user", user)),
            caller_module="idp",
            classification=classification,  # type: ignore[arg-type]
            json_schema=json_schema,
            source_document_id=document_id,
            agent_profile_code="data_capture",  # M1.6 R-DEC-71 (AGT-DATA_CAPTURE)
        )

    def _field(
        self, spec: dict[str, Any], raw: Any, row_index: int | None,
        pages: Sequence[tuple[int, str]],
    ) -> tuple[ExtractedFieldResult, float]:  # fmt: skip
        printed = raw.get("value") if isinstance(raw, dict) else None
        value = normalize_value(printed, spec["value_type"])
        raw_text = raw.get("raw_text") if isinstance(raw, dict) else None
        if raw_text is None and value != printed:
            raw_text = printed
        raw_conf = raw.get("confidence") if isinstance(raw, dict) else None
        conf = float(raw_conf) if isinstance(raw_conf, (int, float)) else 0.0
        if value is None:
            conf = 0.0
        result = ExtractedFieldResult(
            field_name=spec["name"],
            value_type=spec["value_type"],
            value=value,
            raw_text=raw_text,
            confidence=round(conf, 4),
            confidence_band=confidence_band(conf),
            is_critical=is_critical(spec),
            sensitivity_level=int(spec.get("sensitivity_level", 2)),
            source_location={"kind": "page", "page": locate_page(pages, value, raw_text)},
            row_index=row_index,
        )
        return result, conf

    def blank(self, schema_fields: list[dict[str, Any]]) -> ExtractionOutput:
        """No model may read this document: one empty field per spec for a person to fill in."""
        return ExtractionOutput(
            fields=[self._field(spec, {}, None, ())[0] for spec in schema_fields]
        )

    def _parse(
        self, resp: ChatResponse, schema_fields: list[dict[str, Any]],
        pages: Sequence[tuple[int, str]],
    ) -> ExtractionOutput:  # fmt: skip
        data = resp.data if isinstance(resp.data, dict) else {}
        out = ExtractionOutput(provider=resp.provider, model=resp.model)
        confidences: list[float] = []
        # Row-group extraction (M2.3, R-DEC-99): a `rows` array yields one field per (row, spec)
        # with `row_index` — the commit layer groups by it into one ACT per row. A flat payload
        # (single value per field, legacy / scalar doc types) stays a single row_index=None set.
        rows = data.get("rows") if isinstance(data.get("rows"), list) else None
        if rows is not None:
            for idx, row in enumerate(rows):
                row = row if isinstance(row, dict) else {}
                for spec in schema_fields:
                    fr, conf = self._field(spec, row.get(spec["name"]) or {}, idx, pages)
                    out.fields.append(fr)
                    confidences.append(conf)
        else:
            for spec in schema_fields:
                fr, conf = self._field(spec, data.get(spec["name"]) or {}, None, pages)
                out.fields.append(fr)
                confidences.append(conf)
        out.document_confidence = (
            round(sum(confidences) / len(confidences), 4) if confidences else 0.0
        )
        return out

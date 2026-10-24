"""LLM extraction (04 §3 step 6, §5, FR-DC-11). Builds a schema-driven prompt from the page
text and asks the ModelGateway (`task="extract"`) for structured output; every field becomes a
field result `{value, raw_text, confidence, source_location, confidence_band}` (§5.1). Missing
fields are `null` with confidence 0 — never fabricated (P05, §5.1).

Classification routing (04 §7.4, DEC-157) is the gateway's job:
- PUBLIC/INTERNAL → cloud; CONFIDENTIAL (PII) → local LLM; SECRET → blocked (no LLM).
We pass `classification` derived from the document's sensitivity level so salary/health docs
never reach a cloud model.

The gateway is injected so the HTTP/pipeline path is testable without a live provider
(same DI pattern as chat, DEC-233): a test supplies a fake gateway returning `ChatResponse`
with `data` = the extracted field map.
"""

from __future__ import annotations

import uuid
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
    ) -> ExtractionOutput:
        classification = classification_for_sensitivity(sensitivity_level)
        req = self._build_request(schema_fields, page_text, classification, document_id)
        resp: ChatResponse = await self.gateway.chat(req)
        return self._parse(resp, schema_fields)

    def _build_request(
        self,
        schema_fields: list[dict[str, Any]],
        page_text: str,
        classification: str,
        document_id: uuid.UUID | None,
    ) -> ChatRequest:
        names = [f["name"] for f in schema_fields]
        properties = {
            f["name"]: {
                "type": "object",
                "properties": {
                    "value": {},
                    "raw_text": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                },
            }
            for f in schema_fields
        }
        json_schema = {"type": "object", "properties": properties}
        system = (
            "Bạn trích xuất dữ liệu có cấu trúc từ tài liệu. Chỉ trả về các trường yêu cầu; "
            "trường không tìm thấy để value=null và confidence=0. Không bịa số (P05)."
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
        )

    def _parse(self, resp: ChatResponse, schema_fields: list[dict[str, Any]]) -> ExtractionOutput:
        data = resp.data if isinstance(resp.data, dict) else {}
        out = ExtractionOutput(provider=resp.provider, model=resp.model)
        confidences: list[float] = []
        for spec in schema_fields:
            name = spec["name"]
            raw = data.get(name) or {}
            value = raw.get("value") if isinstance(raw, dict) else None
            raw_text = raw.get("raw_text") if isinstance(raw, dict) else None
            raw_conf = raw.get("confidence") if isinstance(raw, dict) else None
            conf = float(raw_conf) if isinstance(raw_conf, (int, float)) else 0.0
            if value is None:
                conf = 0.0
            confidences.append(conf)
            out.fields.append(
                ExtractedFieldResult(
                    field_name=name,
                    value_type=spec["value_type"],
                    value=value,
                    raw_text=raw_text,
                    confidence=round(conf, 4),
                    confidence_band=confidence_band(conf),
                    is_critical=is_critical(spec),
                    sensitivity_level=int(spec.get("sensitivity_level", 2)),
                    source_location={"kind": "page", "page": 1},
                )
            )
        out.document_confidence = (
            round(sum(confidences) / len(confidences), 4) if confidences else 0.0
        )
        return out

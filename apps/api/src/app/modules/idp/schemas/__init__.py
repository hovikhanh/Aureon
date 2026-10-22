"""Pydantic v2 DTOs for `idp` (10 §3.3). Payload models only — the EnvelopeRouter wraps them."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UploadResultOut(BaseModel):
    """EP-20 response — async ingest (202). One job per accepted document (04 §3)."""

    model_config = ConfigDict(from_attributes=True)

    document_ids: list[uuid.UUID]
    job_ids: list[uuid.UUID]
    batch_id: uuid.UUID | None = None
    duplicates: list[uuid.UUID] = Field(default_factory=list)


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str | None
    mime_type: str | None
    size_bytes: int | None
    page_count: int | None
    channel: str
    kind: str
    status: str
    status_reason: str | None
    scan_status: str
    pillars: list[str]
    sensitivity_level: int
    submitted_at: datetime


class DocumentPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    page_number: int
    sheet_name: str | None
    text_layer_exists: bool
    ocr_used: bool
    ocr_confidence: float | None
    text_content: str | None


class FieldResultOut(BaseModel):
    """ENT-ExtractedField as the 04 §5.1 field result (`{value, confidence, source_location}`)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    field_name: str
    row_index: int | None
    value_type: str
    value: Any
    raw_text: str | None
    confidence: float
    confidence_band: str
    is_critical: bool
    source_location: dict[str, Any]
    validation: list[dict[str, Any]]


class ExtractionResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID
    document_id: uuid.UUID
    status: str
    document_confidence: float | None
    routing_decision: str | None
    routing_reasons: list[str]
    fields: list[FieldResultOut]
    validation_errors: list[dict[str, Any]]

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


# ---------------------------------------------------------------------------
# S4b review workflow DTOs (10 §3.3 / §3.12, EP-28..35, EP-126/127).
# ---------------------------------------------------------------------------


class ReviewQueueItemOut(BaseModel):
    """One row of the review queue (EP-28). `confidence_avg` is the mean field confidence;
    `critical_fields_count` drives priority (conflict > critical > low confidence > oldest)."""

    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID
    filename: str | None
    document_type: str | None
    status: str
    confidence_avg: float | None
    critical_fields_count: int
    validation_error_count: int
    routing_reason: str | None
    age_hours: float
    assigned_to: uuid.UUID | None
    due_at: datetime | None
    locked_by: uuid.UUID | None
    locked_until: datetime | None


class ReviewFieldOut(BaseModel):
    """A field as shown in the review detail (EP-30 effective value = corrected ?? ai)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    field_name: str
    row_index: int | None
    value_type: str
    ai_value: Any
    corrected_value: Any
    effective_value: Any
    confidence: float
    confidence_band: str
    is_critical: bool
    is_confirmed: bool
    source_location: dict[str, Any]
    validation: list[dict[str, Any]]
    correction_reason: str | None


class ReviewAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    to_user_id: uuid.UUID | None
    to_role_code: str | None
    due_at: datetime
    is_current: bool


class ReviewDetailOut(BaseModel):
    """EP-25/30 review detail — document + pages + fields + validation + assignment (04 §12.1)."""

    document: DocumentOut
    job_id: uuid.UUID | None
    pages: list[DocumentPageOut]
    fields: list[ReviewFieldOut]
    validation_errors: list[dict[str, Any]]
    document_confidence: float | None
    routing_decision: str | None
    routing_reasons: list[str]
    assigned_to: uuid.UUID | None
    locked_by: uuid.UUID | None
    locked_until: datetime | None


class ReviewOpenOut(BaseModel):
    """EP-29 — soft lock acquired (15 min)."""

    locked_until: datetime
    document: DocumentOut


class FieldCorrectionIn(BaseModel):
    """EP-30 one field edit. `action`: confirm (accept AI value), correct (set `value`),
    clear (set null). `reason` is required for financial/money fields (FR-DC-05)."""

    field_id: uuid.UUID
    action: str = "correct"  # confirm | correct | clear
    value: Any = None
    reason: str | None = None


class FieldPatchIn(BaseModel):
    """EP-30 request — one or more field edits + optional doc-type change + accept_all_high."""

    doc_type: str | None = None
    fields: list[FieldCorrectionIn] = Field(default_factory=list)
    accept_all_high: bool = False


class FieldPatchOut(BaseModel):
    fields: list[ReviewFieldOut]
    validation_errors: list[dict[str, Any]]
    validations_ok: bool


class ApproveIn(BaseModel):
    """EP-31 — approve + commit. `field_paths` null = all fields; `comment` optional."""

    comment: str | None = None
    version: int | None = None


class ActionRefOut(BaseModel):
    action_name: str
    ids: list[str]
    table: str


class ApproveOut(BaseModel):
    document: DocumentOut
    actions: list[ActionRefOut]
    undo_deadline: datetime | None


class RejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ReassignIn(BaseModel):
    """EP-126 — reassign reviewer. Exactly one of `to_user_id` / `to_role_code`; reason req'd."""

    to_user_id: uuid.UUID | None = None
    to_role_code: str | None = None
    reason: str = Field(min_length=1, max_length=2000)


class ReassignOut(BaseModel):
    document: DocumentOut
    assignment: ReviewAssignmentOut


class MergeIn(BaseModel):
    """EP-127 — merge 2..20 documents of one doc type/batch into one review."""

    document_ids: list[uuid.UUID] = Field(min_length=2, max_length=20)
    primary_id: uuid.UUID | None = None


class MergeOut(BaseModel):
    parent: DocumentOut
    children: list[DocumentOut]

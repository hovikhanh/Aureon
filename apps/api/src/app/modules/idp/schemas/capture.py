"""Pydantic v2 DTOs of the M1.5 D03 Data Capture contract (10 §7.2.4, 05 §2.7).

`/data-capture/*` (EP-DC-13..25, 27..37) and `/lineage/*` (EP-DC-26). Payload models only —
the `EnvelopeRouter` wraps them in `{data, meta?}`. Level-3/4 values the caller may not read
are `{"masked": true}` (`core.field_policy.Masked`).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.field_policy import Masked
from app.modules.idp.schemas import ActionRefOut, DocumentOut

InboxGroup = Literal[
    "processing", "needs_review", "approved", "committed", "rejected", "failed", "rolled_back"
]
RollbackReason = Literal["mistake", "critical_field_wrong", "duplicate", "other"]
SchemaStatus = Literal["draft", "published", "retired"]
RuleKind = Literal["field", "cross_field", "cross_document", "master_data"]
RuleSeverity = Literal["warn", "fail", "blocking"]
LineageRestrictedReason = Literal["target_out_of_scope", "source_out_of_scope"]


# ---------- EP-DC-13 inbox / EP-DC-14 source ----------
class InboxItemOut(BaseModel):
    """EP-DC-13 — one row of the Data Inbox (SCR-45)."""

    document: DocumentOut
    document_type: str | None
    channel: str
    submitted_by_name: str | None
    record_count: int | None
    undo_deadline: datetime | None
    can_undo: bool
    batch_id: uuid.UUID | None


class SourceViewOut(BaseModel):
    """EP-DC-14 — presigned GET (5 min) of the original file / one page."""

    url: str
    mime_type: str | None
    page_count: int | None
    page: int | None


# ---------- EP-DC-15/16 C1 manual form ----------
class FormFieldOut(BaseModel):
    name: str
    label_key: str
    value_type: str
    required: bool
    is_critical: bool
    sensitivity_level: int
    enum: list[str] | None = None
    master_ref: str | None = None
    repeatable_group: str | None = None


class FormOut(BaseModel):
    """EP-DC-15 — C1 form generated from the published ExtractionSchema."""

    document_type: str
    schema_version: int
    fields: list[FormFieldOut]
    required_permissions: list[str]
    permitted: bool


class ManualSubmitIn(BaseModel):
    """EP-DC-16 — C1 submit (`values` = single fields, `rows` = repeatable group)."""

    document_type: str
    schema_version: int
    values: dict[str, Any] = Field(default_factory=dict)
    rows: list[dict[str, Any]] | None = None
    department_id: uuid.UUID | None = None


class ManualSubmitOut(BaseModel):
    document: DocumentOut
    status: str
    actions: list[ActionRefOut]
    validation_errors: list[dict[str, Any]]
    undo_deadline: datetime | None


# ---------- EP-DC-17..22 C5 import ----------
class ImportColumnOut(BaseModel):
    index: int
    header: str | None


class ImportSheetOut(BaseModel):
    name: str
    row_count: int
    header_row: int
    columns: list[ImportColumnOut]


class SuggestedTypeOut(BaseModel):
    code: str
    confidence: float


class ColumnMappingOut(BaseModel):
    """One column → schema field (null = ignored), with the mapping confidence."""

    field: str | None
    confidence: float


class ImportSummaryOut(BaseModel):
    rows_total: int
    rows_valid: int
    rows_invalid: int


class ImportPreviewOut(BaseModel):
    """EP-DC-17/18/19 — current import preview (`column_mapping` keyed by column header)."""

    batch_id: uuid.UUID
    document_id: uuid.UUID
    sheets: list[ImportSheetOut]
    suggested_document_type: SuggestedTypeOut | None
    column_mapping: dict[str, ColumnMappingOut]
    preview_rows: list[dict[str, Any]] = Field(max_length=20)
    summary: ImportSummaryOut
    version: int


class ImportMappingIn(BaseModel):
    """EP-DC-19 — change doc type / sheet / header row / column mapping (re-validates rows)."""

    document_type: str
    sheet: str
    header_row: int = Field(ge=1, le=50)
    mapping: dict[str, str | None]
    version: int


class RowErrorOut(BaseModel):
    field: str | None
    rule_code: str
    message_key: str
    params: dict[str, Any] = Field(default_factory=dict)


class ImportRowOut(BaseModel):
    """EP-DC-20 — one imported row (`values[field]` masked when level 4 not readable)."""

    row_number: int
    values: dict[str, Any | Masked]
    errors: list[RowErrorOut]


class VersionIn(BaseModel):
    """`{version}` body of EP-DC-22/23 (optimistic lock)."""

    version: int


class ImportSubmitOut(BaseModel):
    document: DocumentOut
    rows_submitted: int
    rows_excluded: int


# ---------- EP-DC-24/25 undo + document actions ----------
class UndoIn(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    reason_code: RollbackReason


class UndoOut(BaseModel):
    document: DocumentOut
    reverted_actions: list[ActionRefOut]


class ResultRefOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_: str = Field(alias="schema", serialization_alias="schema")
    table: str
    id: uuid.UUID
    reused: bool = False


class DocumentActionOut(BaseModel):
    """EP-DC-25 — one `idp.document_actions` row."""

    seq: int
    action_name: str
    result_refs: list[ResultRefOut]
    status: Literal["applied", "reverted"]
    reverted_at: datetime | None


# ---------- EP-DC-26 lineage ----------
class LineageLinkOut(BaseModel):
    target_column: str | None
    source_document_id: uuid.UUID
    document_type: str | None
    original_filename: str | None
    page_number: int | None
    sheet_name: str | None
    row_index: int | None
    field_name: str | None
    raw_text: str | Masked | None
    confidence: float | None
    action_name: str | None
    committed_at: datetime | None
    revoked_at: datetime | None


class LineageOut(BaseModel):
    """EP-DC-26 — visible: `{entity, id, links[]}`; out of scope: `{restricted, reason}`."""

    entity: str | None = None
    id: uuid.UUID | None = None
    links: list[LineageLinkOut] | None = None
    restricted: bool = False
    reason: LineageRestrictedReason | None = None


# ---------- EP-DC-27/28 document types ----------
class DocumentTypeOut(BaseModel):
    id: uuid.UUID
    code: str
    name_vi: str
    name_en: str
    pillars: list[str]
    is_active: bool
    current_schema_version: int | None
    channels_supported: list[str]
    version: int  # optimistic lock for EP-DC-28 (R-DEC-60bis)


class DocumentTypePatch(BaseModel):
    name_vi: str | None = Field(default=None, min_length=1, max_length=200)
    name_en: str | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None
    classifier_keywords: list[str] | None = None
    version: int


# ---------- EP-DC-29..32 extraction schemas (05 §2.7 JSONB shape) ----------
class SchemaFieldTarget(BaseModel):
    action: str
    param: str


class SchemaFieldDef(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    label_key: str | None = None
    value_type: str
    required: bool = False
    is_critical: bool = False
    sensitivity_level: int = Field(default=2, ge=1, le=4)
    group: Literal["row"] | None = None
    target: SchemaFieldTarget | None = None
    enum: list[str] | None = None
    master_ref: str | None = None
    header_aliases: list[str] = Field(default_factory=list)


class SchemaThresholds(BaseModel):
    classification_confidence_min: float = Field(ge=0, le=1)
    required_field_min: float = Field(ge=0, le=1)


class ExtractionSchemaOut(BaseModel):
    id: uuid.UUID
    document_type: str
    schema_version: int
    status: SchemaStatus
    fields: list[SchemaFieldDef]
    thresholds: SchemaThresholds
    action_names: list[str]
    published_at: datetime | None
    version: int


class ExtractionSchemaCreate(BaseModel):
    document_type: str
    clone_from_id: uuid.UUID | None = None
    fields: list[SchemaFieldDef] = Field(default_factory=list)
    thresholds: SchemaThresholds | None = None
    action_names: list[str] = Field(default_factory=list)


class ExtractionSchemaPatch(BaseModel):
    fields: list[SchemaFieldDef] | None = None
    thresholds: SchemaThresholds | None = None
    action_names: list[str] | None = None
    version: int


# ---------- EP-DC-33..35 validation rules ----------
class ValidationRuleOut(BaseModel):
    id: uuid.UUID
    extraction_schema_id: uuid.UUID | None
    code: str
    kind: RuleKind
    expression: dict[str, Any]
    severity: RuleSeverity
    tolerance: float | None
    is_active: bool
    version: int


class ValidationRuleCreate(BaseModel):
    extraction_schema_id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=50)
    kind: RuleKind
    expression: dict[str, Any]
    severity: RuleSeverity
    tolerance: float | None = None


class ValidationRulePatch(BaseModel):
    expression: dict[str, Any] | None = None
    severity: RuleSeverity | None = None
    tolerance: float | None = None
    is_active: bool | None = None
    version: int


# ---------- EP-DC-36/37 capture incidents (G4) ----------
class IncidentCreate(BaseModel):
    source_document_id: uuid.UUID
    extracted_field_id: uuid.UUID | None = None
    field_name: str = Field(min_length=1, max_length=100)
    target_table: str | None = None
    target_id: uuid.UUID | None = None
    description: str = Field(min_length=1, max_length=2000)


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_document_id: uuid.UUID
    extracted_field_id: uuid.UUID | None
    field_name: str
    is_critical: bool
    detected_by: Literal["review", "post_commit", "undo"]
    undetected: bool
    target_table: str | None
    target_id: uuid.UUID | None
    description: str
    reported_by: uuid.UUID
    reported_at: datetime

"""Pydantic schemas for IDP endpoints per docs/3.EXECUTION/10-API-SPECIFICATION.md §4."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.envelope import PageMeta
from app.modules.idp.enums import (
    AutonomyLevel,
    DocType,
    DocumentKind,
    DocumentStatus,
    FieldValueType,
    InputChannel,
    JobStatus,
    RoutingDecision,
    SensitivityLabel,
)


class UserBrief(BaseModel):
    """Brief representation of a user for uploaded_by and locked_by."""

    id: UUID
    full_name: str


class JobOut(BaseModel):
    """Extraction job summary."""

    id: UUID
    attempt_no: int
    doc_type: DocType | None = None
    status: JobStatus
    classification_confidence: float | None = None
    routing_decision: RoutingDecision | None = None
    routing_reason: str | None = None
    error_code: str | None = None
    avg_confidence: float | None = None
    validation_summary: dict[str, Any] | None = None
    cross_doc_results: list[dict[str, Any]] | None = None
    token_cost_usd: float | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class DocumentOut(BaseModel):
    """Standard representation of a source document (10 §4 DocumentOut)."""

    id: UUID
    batch_id: UUID | None = None
    channel: InputChannel
    kind: DocumentKind
    original_filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    page_count: int | None = None
    doc_type: DocType | None = None
    pillars: list[str] = Field(default_factory=list)
    status: DocumentStatus
    status_reason: str | None = None
    ai_state: str | None = None
    autonomy_level: AutonomyLevel | None = None
    contains_salary: bool = False
    contains_pii: bool = False
    duplicate_of_id: UUID | None = None
    uploaded_by: UserBrief
    uploaded_at: datetime
    committed_at: datetime | None = None
    undo_deadline: datetime | None = None
    locked_by: UserBrief | None = None
    locked_until: datetime | None = None
    retry_count: int = 0
    latest_job: JobOut | None = None


class BatchChecklistItem(BaseModel):
    """Item in an onboarding batch checklist (EP-40)."""

    doc_type: DocType
    required: bool = True


class BatchCreateRequest(BaseModel):
    """Request payload for EP-40 POST /api/v1/onboarding/batches."""

    expected_doc_types: list[DocType] | None = None
    label: str | None = Field(default=None, max_length=100)


class BatchCreateResponse(BaseModel):
    """Response payload for EP-40 POST /api/v1/onboarding/batches."""

    batch_id: UUID
    checklist: list[BatchChecklistItem]
    upload_endpoint: str = "/api/v1/documents"


class DuplicateWarningMeta(BaseModel):
    """Warning metadata when document is a duplicate."""

    code: str = "DUPLICATE_DOCUMENT"
    duplicate_of_id: UUID


class ManualDocumentCreateRequest(BaseModel):
    """Request payload for EP-21 POST /api/v1/documents/manual."""

    doc_type: DocType
    fields: dict[str, Any]
    batch_id: UUID | None = None


class NaturalLanguageDocumentCreateRequest(BaseModel):
    """Request payload for EP-22 POST /api/v1/documents/natural-language (JSON form)."""

    text: str = Field(..., max_length=2000)
    batch_id: UUID | None = None


class ColumnMappingSuggestionItem(BaseModel):
    """One suggested column-to-field mapping in EP-23."""

    column: str
    header: str
    suggested_field_key: str | None = None
    confidence: float = 0.0


class MappingSuggestion(BaseModel):
    """AI suggested column mapping in EP-23."""

    sheet_name: str = "Sheet1"
    header_row: int = 1
    columns: list[ColumnMappingSuggestionItem]


class ColumnConfirmItem(BaseModel):
    """One confirmed column mapping in EP-36."""

    column: str
    field_key: str


class ImportMappingConfirmRequest(BaseModel):
    """Request payload for EP-36 POST /api/v1/documents/{id}/import-mapping."""

    doc_type: DocType = DocType.INVOICE
    columns: list[ColumnConfirmItem]


class RowErrorItem(BaseModel):
    """One row error in EP-36 import processing."""

    row_index: int
    field_key: str
    code: str
    message: str | None = None


class SplitRangeItem(BaseModel):
    """Page range for multi-document splitting (FR-DC-09, EP-30)."""

    model_config = ConfigDict(extra="forbid")

    from_page: int = Field(ge=1, description="1-based starting page number")
    to_page: int = Field(ge=1, description="1-based ending page number")


class ExtractionSchemaFieldOut(BaseModel):
    """Field specification within an extraction schema (04 §5, EP-50)."""

    field_key: str
    table_key: str | None = None
    value_type: FieldValueType
    required: bool = False
    sensitivity: SensitivityLabel = SensitivityLabel.NONE
    validation_rules: list[str] = Field(default_factory=list)


class ExtractionSchemaOut(BaseModel):
    """Extraction schema for one document type (04 §5, EP-50)."""

    doc_type: DocType
    field_set_version: str = "1.0.0"
    fields: list[ExtractionSchemaFieldOut]


class ExtractedFieldOut(BaseModel):
    """Extracted field representation for API response (05 §4.6, EP-26)."""

    id: UUID
    field_key: str
    table_key: str | None = None
    row_index: int | None = None
    record_group: str | None = None
    value: Any = None
    raw_text: str | None = None
    value_type: FieldValueType
    confidence: float
    confidence_band: str
    source_location: dict[str, Any] | None = None
    document_page_id: UUID | None = None
    validation: list[dict[str, Any]] = Field(default_factory=list)
    sensitivity: SensitivityLabel = SensitivityLabel.NONE
    corrected: bool = False
    corrected_value: Any = None
    final_value: Any = None
    required: bool = False
    masked: bool = False


class ExtractionResultOut(BaseModel):
    """Full extraction result response for EP-26 GET /documents/{id}/extraction."""

    document: DocumentOut
    job: JobOut
    fields: list[ExtractedFieldOut]
    cross_doc_results: list[dict[str, Any]] = Field(default_factory=list)
    validation_summary: dict[str, Any] = Field(default_factory=dict)
    suspicious_content: bool = False


class FieldCorrectionItem(BaseModel):
    """One field correction item in EP-30."""

    id: UUID
    corrected_value: Any = None


class UpdateDocumentFieldsRequest(BaseModel):
    """Payload for EP-30 PATCH /documents/{id}/fields."""

    doc_type: DocType | None = None
    split_ranges: list[SplitRangeItem] | None = None
    fields: list[FieldCorrectionItem] | None = None
    confirmed_field_ids: list[UUID] | None = None


class StatusTimelineItem(BaseModel):
    """One event in the document status timeline (EP-25)."""

    status: str
    at: datetime
    actor_type: str = "USER"


class DocumentAffectedOut(BaseModel):
    """Business records and metrics affected by this document (EP-25)."""

    business_record_ids: list[UUID] = Field(default_factory=list)
    metric_codes: list[str] = Field(default_factory=list)


class DocumentReviewOut(BaseModel):
    """Review entry on a document (EP-25)."""

    reviewer_full_name: str
    decision: str | None = None
    reject_reason_code: str | None = None
    decided_at: datetime | None = None


class DocumentDetailOut(BaseModel):
    """Detailed document representation with jobs, timeline, and reviews (EP-25)."""

    document: DocumentOut
    jobs: list[JobOut] = Field(default_factory=list)
    status_timeline: list[StatusTimelineItem] = Field(default_factory=list)
    affected: DocumentAffectedOut = Field(default_factory=DocumentAffectedOut)
    reviews: list[DocumentReviewOut] = Field(default_factory=list)


class DocumentPageDetailOut(BaseModel):
    """Page detail for SourceViewer (EP-27)."""

    page_number: int
    image_url: str | None = None
    width_px: int | None = None
    height_px: int | None = None
    ocr_used: bool = False
    ocr_confidence: float | None = None


class ManualInfoOut(BaseModel):
    """Metadata for virtual documents created manually (EP-27)."""

    created_by_full_name: str
    created_at: datetime


class DocumentSourceOut(BaseModel):
    """Presigned source URL and pages response (EP-27)."""

    url: str | None = None
    expires_at: datetime | None = None
    mime_type: str | None = None
    page_count: int | None = None
    pages: list[DocumentPageDetailOut] = Field(default_factory=list)
    manual_info: ManualInfoOut | None = None


class RetryMode(str):
    """Allowed modes for EP-34 POST /documents/{id}/retry."""

    RETRY = "RETRY"
    REOPEN = "REOPEN"
    FORCE_DUPLICATE = "FORCE_DUPLICATE"


class RetryDocumentRequest(BaseModel):
    """Payload for EP-34 POST /documents/{id}/retry."""

    mode: str = Field(..., description="RETRY, REOPEN, or FORCE_DUPLICATE")
    note: str | None = None


class ReviewQueueCountsOut(BaseModel):
    """Counts by document status for EP-28."""

    needs_review: int = 0
    in_review: int = 0
    failed: int = 0


class ReviewQueueItemOut(BaseModel):
    """One document item in the review queue (EP-28)."""

    document: DocumentOut
    routing_reason: str | None = None
    avg_confidence: float | None = None
    fields_to_check: int = 0
    has_conflict: bool = False
    locked_by: UserBrief | None = None
    locked_until: datetime | None = None


class ReviewQueueMetaOut(PageMeta):
    """Paginated metadata including counts for EP-28."""

    counts: ReviewQueueCountsOut = Field(default_factory=ReviewQueueCountsOut)


class ReviewQueueResponse(BaseModel):
    """Response envelope for EP-28 GET /review-queue."""

    data: list[ReviewQueueItemOut]
    meta: ReviewQueueMetaOut


class ReviewOpenOut(BaseModel):
    """Response payload for EP-29 POST /documents/{id}/review/open."""

    document: DocumentOut
    review_id: UUID
    extraction: ExtractionResultOut


class AcceptedConflictItem(BaseModel):
    """Accepted cross-document conflict with mandatory note (EP-31)."""

    rule: str
    note: str


class ReviewApproveRequest(BaseModel):
    """Payload for EP-31 POST /documents/{id}/review/approve."""

    review_id: UUID
    field_ids: list[UUID] | None = None
    accepted_conflicts: list[AcceptedConflictItem] = Field(default_factory=list)


class ReviewApproveReviewOut(BaseModel):
    """Review execution details for EP-31."""

    id: UUID
    decision: str = "APPROVED"
    decided_at: datetime
    duration_ms: int | None = None
    fields_corrected: int = 0


class CommitActionResult(BaseModel):
    """Business record IDs created by Action Registry."""

    action_name: str
    business_record_ids: list[UUID] = Field(default_factory=list)
    metric_value_ids: list[UUID] = Field(default_factory=list)


class ReviewApproveCommitOut(BaseModel):
    """Commit outcome for EP-31."""

    actions: list[CommitActionResult] = Field(default_factory=list)
    affected_metric_codes: list[str] = Field(default_factory=list)
    recompute_job_id: str | None = None


class ReviewApproveOut(BaseModel):
    """Response payload for EP-31 POST /documents/{id}/review/approve."""

    document: DocumentOut
    review: ReviewApproveReviewOut
    commit: ReviewApproveCommitOut


class ReviewRejectRequest(BaseModel):
    """Payload for EP-32 POST /documents/{id}/review/reject."""

    review_id: UUID
    reject_reason_code: str
    reject_note: str | None = None

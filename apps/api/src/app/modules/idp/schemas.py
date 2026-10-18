"""Pydantic schemas for IDP endpoints per docs/3.EXECUTION/10-API-SPECIFICATION.md §4.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.idp.enums import (
    AutonomyLevel,
    DocType,
    DocumentKind,
    DocumentStatus,
    InputChannel,
    JobStatus,
    RoutingDecision,
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
    routing_decision: RoutingDecision | None = None
    avg_confidence: float | None = None
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


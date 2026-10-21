"""EP-42 meetings, EP-43 decisions, EP-45 projects DTOs (10 §4.4; 05 §4.7; DEC-221).

Field names follow 10; fields beyond 10's "main fields" use the 05 column name. Project
`due_date` (10) ↔ column `planned_end_date` (05); project `code` is required by 05 (UQ).
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.execution.schemas.common import (
    DecisionStatus,
    Out,
    Patch,
    ProjectStatus,
)


# ---------- EP-42 meetings ----------
class MeetingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    held_at: datetime
    chair_id: uuid.UUID | None = None
    attendee_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)
    department_id: uuid.UUID | None = None
    summary: str | None = Field(default=None, max_length=20000)
    source_document_id: uuid.UUID | None = None
    transcript_id: uuid.UUID | None = None


class MeetingUpdate(Patch):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    held_at: datetime | None = None
    chair_id: uuid.UUID | None = None
    attendee_ids: list[uuid.UUID] | None = Field(default=None, max_length=200)
    department_id: uuid.UUID | None = None
    summary: str | None = Field(default=None, max_length=20000)
    transcript_id: uuid.UUID | None = None


class MeetingOut(Out):
    title: str
    held_at: datetime
    chair_id: uuid.UUID | None
    attendee_ids: list[uuid.UUID]
    department_id: uuid.UUID | None
    summary: str | None
    source_document_id: uuid.UUID | None
    transcript_id: uuid.UUID | None


# ---------- EP-43 decisions ----------
class DecisionCreate(BaseModel):
    meeting_id: uuid.UUID | None = None
    content: str = Field(min_length=1, max_length=10000)
    rationale: str | None = Field(default=None, max_length=10000)
    alternatives_rejected: str | None = Field(default=None, max_length=10000)
    expected_outcome: str | None = Field(default=None, max_length=10000)
    owner_id: uuid.UUID | None = None
    decided_at: datetime
    due_date: date | None = None
    review_at: list[date] | None = Field(default=None, max_length=20)
    initiative_id: uuid.UUID | None = None
    status: DecisionStatus = "open"
    source_document_id: uuid.UUID | None = None


class DecisionUpdate(Patch):
    content: str | None = Field(default=None, min_length=1, max_length=10000)
    rationale: str | None = Field(default=None, max_length=10000)
    alternatives_rejected: str | None = Field(default=None, max_length=10000)
    expected_outcome: str | None = Field(default=None, max_length=10000)
    owner_id: uuid.UUID | None = None
    due_date: date | None = None
    review_at: list[date] | None = Field(default=None, max_length=20)
    initiative_id: uuid.UUID | None = None
    status: DecisionStatus | None = None
    actual_outcome: str | None = Field(default=None, max_length=10000)
    outcome_verified_at: datetime | None = None


class DecisionOut(Out):
    meeting_id: uuid.UUID | None
    content: str
    rationale: str | None
    alternatives_rejected: str | None
    expected_outcome: str | None
    owner_id: uuid.UUID | None
    decided_at: datetime
    due_date: date | None
    review_at: list[date]
    actual_outcome: str | None
    outcome_verified_at: datetime | None
    initiative_id: uuid.UUID | None
    source_insight_id: uuid.UUID | None
    status: str
    done_at: datetime | None
    source_document_id: uuid.UUID | None


# ---------- EP-45 projects ----------
class ProjectCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=500)
    owner_id: uuid.UUID
    department_id: uuid.UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    status: ProjectStatus = "planned"
    budget_amount: int | None = Field(default=None, ge=0)
    currency: str = Field(default="VND", pattern=r"^[A-Z]{3}$")


class ProjectUpdate(Patch):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=500)
    owner_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    actual_end_date: date | None = None
    status: ProjectStatus | None = None
    budget_amount: int | None = Field(default=None, ge=0)


class ProjectOut(Out):
    code: str
    name: str
    owner_id: uuid.UUID
    department_id: uuid.UUID | None
    start_date: date | None
    due_date: date | None
    actual_end_date: date | None
    status: str
    budget_amount: int | None
    currency: str

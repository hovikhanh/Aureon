"""EP-44 tasks DTOs (10 §4.4; 05 ENT-Task; DEC-147 7 statuses; DEC-154 `task_source`)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.modules.execution.schemas.common import Out, Patch, TaskPriority, TaskSource, TaskStatus


def hours() -> Any:
    """numeric(6,2) hours."""
    return Field(default=None, ge=0, le=Decimal("9999.99"), max_digits=6, decimal_places=2)


class EvidenceItem(BaseModel):
    kind: Literal["file", "link", "note"]
    ref: str = Field(min_length=1, max_length=2000)


class _TaskFields(BaseModel):
    description: str | None = Field(default=None, max_length=10000)
    owner_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    blocked_reason: str | None = Field(default=None, min_length=1, max_length=2000)
    estimate_hours: Decimal | None = hours()
    actual_hours: Decimal | None = hours()
    evidence: list[EvidenceItem] | None = Field(default=None, max_length=50)
    project_id: uuid.UUID | None = None
    initiative_id: uuid.UUID | None = None
    milestone_id: uuid.UUID | None = None
    meeting_id: uuid.UUID | None = None
    decision_id: uuid.UUID | None = None
    key_result_id: uuid.UUID | None = None
    kpi_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    is_critical: bool = False
    source_document_id: uuid.UUID | None = None


class TaskCreate(_TaskFields):
    title: str = Field(min_length=1, max_length=500)
    priority: TaskPriority = "medium"
    status: TaskStatus = "todo"
    task_source: TaskSource = "manual"


class TaskUpdate(Patch):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    owner_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    blocked_reason: str | None = Field(default=None, min_length=1, max_length=2000)
    estimate_hours: Decimal | None = hours()
    actual_hours: Decimal | None = hours()
    evidence: list[EvidenceItem] | None = Field(default=None, max_length=50)
    project_id: uuid.UUID | None = None
    initiative_id: uuid.UUID | None = None
    milestone_id: uuid.UUID | None = None
    meeting_id: uuid.UUID | None = None
    decision_id: uuid.UUID | None = None
    key_result_id: uuid.UUID | None = None
    kpi_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    is_critical: bool | None = None


class TaskOut(Out):
    title: str
    description: str | None
    owner_id: uuid.UUID | None
    assignee_id: uuid.UUID | None
    department_id: uuid.UUID | None
    start_date: date | None
    due_date: date | None
    priority: str
    status: str
    blocked_reason: str | None
    done_at: datetime | None
    estimate_hours: float | None
    actual_hours: float | None
    evidence: list[dict[str, Any]] | None
    project_id: uuid.UUID | None
    initiative_id: uuid.UUID | None
    milestone_id: uuid.UUID | None
    meeting_id: uuid.UUID | None
    decision_id: uuid.UUID | None
    key_result_id: uuid.UUID | None
    kpi_id: uuid.UUID | None
    parent_id: uuid.UUID | None
    is_critical: bool
    task_source: str
    source_document_id: uuid.UUID | None
    overdue: bool

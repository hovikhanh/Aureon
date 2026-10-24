"""EP-TASK-01..08 tasks DTOs (10 §7.2.2; 05 §2.5 ENT-Task/ENT-TaskDependency; DEC-147; DEC-154)."""

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


SourceRefKind = Literal["meeting", "decision", "ai_action", "document", "mitigation"]
TaskDependencyType = Literal["finish_to_start"]


class SourceRef(BaseModel):
    """05 §2.5 `tasks.source_ref` — pointer to the record a task came from (P06 lineage)."""

    kind: SourceRefKind
    id: uuid.UUID
    page: int | None = Field(default=None, ge=1)


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
    parent_task_id: uuid.UUID | None = None
    source_ref: SourceRef | None = None
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
    parent_task_id: uuid.UUID | None = None
    source_ref: SourceRef | None = None
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
    parent_task_id: uuid.UUID | None
    source_ref: SourceRef | None = None
    is_critical: bool
    task_source: str
    source_document_id: uuid.UUID | None
    overdue: bool
    subtask_count: int = 0
    depends_on_open: int = 0


# ---------- EP-TASK-06..08 dependencies (FR-TASK-02, R-DEC-43) ----------
class TaskDependencyCreate(BaseModel):
    depends_on_task_id: uuid.UUID
    dependency_type: TaskDependencyType = "finish_to_start"


class TaskDependencyOut(Out):
    task_id: uuid.UUID
    depends_on_task_id: uuid.UUID
    dependency_type: TaskDependencyType


class TaskBriefOut(BaseModel):
    """One side of a dependency; out-of-scope task → only `{task_id, restricted: true}`."""

    dependency_id: uuid.UUID | None = None
    task_id: uuid.UUID
    title: str | None = None
    status: str | None = None
    due_date: date | None = None
    overdue: bool | None = None
    assignee_id: uuid.UUID | None = None
    restricted: bool = False


class TaskDependenciesOut(BaseModel):
    depends_on: list[TaskBriefOut]
    blocks: list[TaskBriefOut]


# ---------- EP-TASK-19 reassign request (R-DEC-45) ----------
class ReassignRequestCreate(BaseModel):
    to_assignee_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=500)

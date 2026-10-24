"""M1.3 `/work/*` read models (10 §7.2.2 EP-TASK-11, EP-TASK-18; 05 §2.5; R-DEC-44/49)."""

import uuid

from pydantic import BaseModel, Field

from app.modules.execution.schemas.initiatives import MilestoneOut
from app.modules.execution.schemas.meetings import ProjectOut


class TaskCountsOut(BaseModel):
    by_status: dict[str, int]


class ProjectDetailOut(ProjectOut):
    """EP-TASK-11 — `ProjectOut` + milestones (sorted by `due_date`) + task counts."""

    milestones: list[MilestoneOut] = Field(default_factory=list)
    task_counts: TaskCountsOut = Field(default_factory=lambda: TaskCountsOut(by_status={}))


class WorkloadCellOut(BaseModel):
    week: str  # ISO week `YYYY-Www`
    load_pct: float
    hours: float
    open_tasks: int


class WorkloadRowOut(BaseModel):
    """One person; no name on purpose (R-DEC-44 — FE joins `members[]` of EP-ORG-24)."""

    employee_id: uuid.UUID
    department_id: uuid.UUID | None
    cells: list[WorkloadCellOut]
    overloaded: bool


class WorkloadSummaryOut(BaseModel):
    people: int
    overloaded_count: int
    overloaded_pct: float


class WorkloadOut(BaseModel):
    """EP-TASK-18 heatmap person × week (computed at read, DEC-226 thresholds)."""

    weeks: list[str]
    threshold_pct: float
    overload_weeks: int
    capacity_hours: float
    rows: list[WorkloadRowOut]
    summary: WorkloadSummaryOut

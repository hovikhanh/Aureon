"""EP-STR-12..21 initiatives + milestones (10 §7.2.3, 05 §2.6; v2.1 EP-45, T-133).

Milestone DTOs are shared with the project milestones EP-TASK-14..17 (`/work/*`).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.execution.schemas.common import (
    InitiativeStatus,
    MilestoneStatus,
    Out,
    Patch,
    Pillar,
)


class InitiativeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    strategic_objective_id: uuid.UUID  # EP-STR-13: required (R-DEC-50)
    objective_id: uuid.UUID | None = None  # contributing OKR, optional
    pillar: Pillar | None = None
    owner_id: uuid.UUID
    department_id: uuid.UUID | None = None
    start_date: date
    planned_end_date: date
    status: InitiativeStatus = "planned"
    weight_pct: Decimal = Field(default=Decimal(0), ge=0, le=100, max_digits=7, decimal_places=4)
    budget_amount: int | None = Field(default=None, ge=0)
    currency: str = Field(default="VND", pattern=r"^[A-Z]{3}$")


class InitiativeUpdate(Patch):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    objective_id: uuid.UUID | None = None
    strategic_objective_id: uuid.UUID | None = None
    pillar: Pillar | None = None
    owner_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    start_date: date | None = None
    planned_end_date: date | None = None
    status: InitiativeStatus | None = None
    weight_pct: Decimal | None = Field(default=None, ge=0, le=100, max_digits=7, decimal_places=4)
    budget_amount: int | None = Field(default=None, ge=0)


class InitiativeOut(Out):
    code: str
    title: str
    description: str | None
    objective_id: uuid.UUID | None
    strategic_objective_id: uuid.UUID | None
    pillar: str | None
    owner_id: uuid.UUID
    department_id: uuid.UUID | None
    start_date: date
    planned_end_date: date
    status: str
    progress_pct: float
    weight_pct: float
    budget_amount: int | None
    currency: str


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    due_date: date
    status: MilestoneStatus = "planned"


class MilestoneUpdate(Patch):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    due_date: date | None = None
    status: MilestoneStatus | None = None


class MilestoneOut(Out):
    initiative_id: uuid.UUID | None
    project_id: uuid.UUID | None = None  # EP-TASK-14..17 (milestone per project)
    title: str
    due_date: date
    status: str
    done_at: datetime | None
    late: bool | None = None  # `planned` and past `due_date` (R-DEC-49), computed at read

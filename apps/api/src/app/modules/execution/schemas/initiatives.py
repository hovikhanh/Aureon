"""EP-45 sub-resources — initiatives + milestones (T-133, 10 §4.4, 05 ENT-Initiative)."""

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
    objective_id: uuid.UUID
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
    objective_id: uuid.UUID
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
    title: str
    due_date: date
    status: str
    done_at: datetime | None

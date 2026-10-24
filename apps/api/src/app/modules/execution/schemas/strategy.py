"""EP-STR-01..11, 22 — Strategy, StrategicObjective, goal tree (10 §7.2.3; 05 §2.6, R-DEC-50).

Initiative + milestone DTOs (EP-STR-12..21) stay in `schemas/initiatives.py`.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.modules.execution.schemas.common import (
    Confidence,
    KpiDirection,
    OkrStatus,
    Out,
    Patch,
    Pillar,
    StrategyStatus,
)
from app.modules.execution.schemas.kpi import KpiEvaluationBrief


# ---------- EP-STR-02..06 strategies ----------
class StrategyCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=500)
    vision: str | None = Field(default=None, max_length=10000)
    mission: str | None = Field(default=None, max_length=10000)
    period_start: date
    period_end: date
    owner_id: uuid.UUID
    status: StrategyStatus = "draft"

    @model_validator(mode="after")
    def _period(self) -> "StrategyCreate":
        if self.period_end <= self.period_start:  # 10 EP-STR-03 → 422 VALIDATION_ERROR
            raise ValueError("period_end must be after period_start")
        return self


class StrategyUpdate(Patch):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    vision: str | None = Field(default=None, max_length=10000)
    mission: str | None = Field(default=None, max_length=10000)
    period_start: date | None = None
    period_end: date | None = None
    owner_id: uuid.UUID | None = None
    status: StrategyStatus | None = None


class StrategyOut(Out):
    code: str
    name: str
    vision: str | None
    mission: str | None
    period_start: date
    period_end: date
    owner_id: uuid.UUID
    status: str


# ---------- EP-STR-07..11 strategic objectives ----------
class StrategicObjectiveCreate(BaseModel):
    strategy_id: uuid.UUID
    code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    pillar: Pillar | None = None
    owner_id: uuid.UUID
    department_id: uuid.UUID | None = None
    weight_pct: Decimal = Field(default=Decimal(0), ge=0, le=100, max_digits=7, decimal_places=4)
    sort_order: int | None = Field(default=None, ge=0)


class StrategicObjectiveUpdate(Patch):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    pillar: Pillar | None = None
    owner_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    weight_pct: Decimal | None = Field(default=None, ge=0, le=100, max_digits=7, decimal_places=4)
    sort_order: int | None = Field(default=None, ge=0)
    status: OkrStatus | None = None


class StrategicObjectiveOut(Out):
    strategy_id: uuid.UUID
    code: str
    title: str
    description: str | None
    pillar: str | None
    owner_id: uuid.UUID
    department_id: uuid.UUID | None
    weight_pct: float
    sort_order: int
    status: str
    progress_pct: float
    kpi_count: int | None = None  # EP-STR-09 detail only
    objective_count: int | None = None
    initiative_count: int | None = None


# ---------- EP-STR-22 initiative → projects ----------
class InitiativeProjectOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    status: str
    start_date: date | None
    planned_end_date: date | None
    owner_id: uuid.UUID


# ---------- EP-STR-01 goal tree ----------
# A node outside the caller's scope that is an ancestor of a visible node is sent reduced:
# `restricted = true`, only `id` + `code`/`title` (+ the children leading to visible nodes);
# every other field is `null` (10 EP-STR-01, R-DEC-57).
class KrNode(BaseModel):
    id: uuid.UUID
    title: str
    unit: str
    baseline: float
    target: float
    current_value: float | None
    progress_pct: float
    confidence: Confidence | None
    at_risk: bool
    last_checked_in_at: datetime | None
    owner_id: uuid.UUID


class KpiNode(BaseModel):
    id: uuid.UUID
    code: str | None = None
    name: str | None = None
    restricted: bool = False
    unit: str | None = None
    direction: KpiDirection | None = None
    owner_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    latest_evaluation: KpiEvaluationBrief | None = None
    children: list["KpiNode"] = []


class ObjNode(BaseModel):
    id: uuid.UUID
    title: str | None = None
    restricted: bool = False
    period_key: str | None = None
    level: str | None = None
    status: str | None = None
    progress_pct: float | None = None
    owner_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    at_risk_kr_count: int | None = None
    key_results: list[KrNode] = []
    children: list["ObjNode"] = []


class IniProjectNode(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    status: str


class IniNode(BaseModel):
    id: uuid.UUID
    code: str | None = None
    title: str | None = None
    restricted: bool = False
    status: str | None = None
    progress_pct: float | None = None
    start_date: date | None = None
    planned_end_date: date | None = None
    on_track: bool | None = None
    projects: list[IniProjectNode] = []


class SONode(BaseModel):
    id: uuid.UUID
    code: str | None = None
    title: str | None = None
    restricted: bool = False
    pillar: Pillar | None = None
    owner_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    progress_pct: float | None = None
    status: str | None = None
    kpis: list[KpiNode] = []
    objectives: list[ObjNode] = []
    initiatives: list[IniNode] = []


class StrategyNode(BaseModel):
    id: uuid.UUID
    code: str | None = None
    name: str | None = None
    restricted: bool = False
    status: StrategyStatus | None = None
    period_start: date | None = None
    period_end: date | None = None
    owner_id: uuid.UUID | None = None
    strategic_objectives: list[SONode] = []


class UnalignedOut(BaseModel):
    kpis: list[KpiNode] = []
    objectives: list[ObjNode] = []


class GoalTreeOut(BaseModel):
    strategies: list[StrategyNode] = []
    unaligned: UnalignedOut = UnalignedOut()

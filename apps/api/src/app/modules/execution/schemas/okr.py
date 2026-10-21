"""EP-46 objectives / key results, EP-47 KPIs / measurements, EP-48 check-ins (10 §4.4).

10 ↔ 05 renames (DEC-222): KPI `target` ↔ column `target_value`; check-in filter `owner_id`
↔ column `user_id`. Fields beyond 10's "main fields" carry the 05 column name.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.modules.execution.schemas.common import (
    Confidence,
    KpiDataSource,
    KpiDirection,
    KpiPeriodType,
    KpiValueType,
    LogOut,
    ObjectiveLevel,
    OkrStatus,
    OkrType,
    Out,
    Patch,
    Pillar,
)


def measure(required: bool = False) -> Any:
    """numeric(20,6) (05 C10)."""
    if required:
        return Field(max_digits=20, decimal_places=6)
    return Field(default=None, max_digits=20, decimal_places=6)


def weight(default: Decimal | None = Decimal(100)) -> Any:
    return Field(default=default, ge=0, le=100, max_digits=7, decimal_places=4)


PERIOD = r"^\d{4}(-Q[1-4]|-(0[1-9]|1[0-2]))?$"


# ---------- EP-46 objectives ----------
class ObjectiveCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    owner_id: uuid.UUID
    period_key: str = Field(pattern=PERIOD)
    parent_id: uuid.UUID | None = None
    level: ObjectiveLevel = "company"
    okr_type: OkrType = "committed"
    weight_pct: Decimal = weight()
    team_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    pillar: Pillar | None = None
    status: OkrStatus = "draft"
    source_document_id: uuid.UUID | None = None


class ObjectiveUpdate(Patch):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    owner_id: uuid.UUID | None = None
    period_key: str | None = Field(default=None, pattern=PERIOD)
    parent_id: uuid.UUID | None = None
    level: ObjectiveLevel | None = None
    okr_type: OkrType | None = None
    weight_pct: Decimal | None = weight(None)
    team_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    pillar: Pillar | None = None
    status: OkrStatus | None = None
    score: Decimal | None = Field(default=None, ge=0, le=1, max_digits=3, decimal_places=2)


class ObjectiveOut(Out):
    title: str
    owner_id: uuid.UUID
    period_key: str
    parent_id: uuid.UUID | None
    level: str
    okr_type: str
    weight_pct: float
    team_id: uuid.UUID | None
    department_id: uuid.UUID | None
    pillar: str | None
    status: str
    progress_pct: float
    score: float | None
    source_document_id: uuid.UUID | None


class KeyResultCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    baseline: Decimal = measure(True)
    target: Decimal = measure(True)
    unit: str = Field(min_length=1, max_length=50)
    owner_id: uuid.UUID
    metric_code: str | None = Field(default=None, pattern=r"^METRIC-[A-Z]+-\d{2}$")
    current_value: Decimal | None = measure()
    status: OkrStatus = "draft"
    weight_pct: Decimal = weight()


class KeyResultUpdate(Patch):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    baseline: Decimal | None = measure()
    target: Decimal | None = measure()
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    owner_id: uuid.UUID | None = None
    metric_code: str | None = Field(default=None, pattern=r"^METRIC-[A-Z]+-\d{2}$")
    status: OkrStatus | None = None
    weight_pct: Decimal | None = weight(None)


class KeyResultOut(Out):
    objective_id: uuid.UUID
    title: str
    metric_code: str | None
    unit: str
    baseline: float
    target: float
    current_value: float | None
    owner_id: uuid.UUID
    status: str
    confidence: str | None
    weight_pct: float
    progress_pct: float


# ---------- EP-47 KPIs ----------
class KpiCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=50)
    target: Decimal = measure(True)
    owner_id: uuid.UUID
    metric_code: str | None = Field(default=None, pattern=r"^METRIC-[A-Z]+-\d{2}$")
    key_result_id: uuid.UUID | None = None
    period_type: KpiPeriodType = "MONTH"
    direction: KpiDirection = "HIGHER_IS_BETTER"
    value_type: KpiValueType = "numeric"
    data_source_kind: KpiDataSource = "manual"
    parent_kpi_id: uuid.UUID | None = None
    weight_pct: Decimal = weight()
    initiative_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    status: OkrStatus = "active"


class KpiUpdate(Patch):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    target: Decimal | None = measure()
    owner_id: uuid.UUID | None = None
    metric_code: str | None = Field(default=None, pattern=r"^METRIC-[A-Z]+-\d{2}$")
    key_result_id: uuid.UUID | None = None
    direction: KpiDirection | None = None
    value_type: KpiValueType | None = None
    data_source_kind: KpiDataSource | None = None
    parent_kpi_id: uuid.UUID | None = None
    weight_pct: Decimal | None = weight(None)
    initiative_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    status: OkrStatus | None = None


class KpiOut(Out):
    code: str
    name: str
    unit: str
    target: float
    owner_id: uuid.UUID
    metric_code: str | None
    key_result_id: uuid.UUID | None
    period_type: str
    direction: str
    value_type: str
    data_source_kind: str
    parent_kpi_id: uuid.UUID | None
    weight_pct: float
    initiative_id: uuid.UUID | None
    department_id: uuid.UUID | None
    status: str


class MeasurementCreate(BaseModel):
    period_key: str = Field(pattern=PERIOD)
    actual_value: Decimal = measure(True)
    source_document_id: uuid.UUID | None = None


class MeasurementOut(LogOut):
    kpi_id: uuid.UUID
    period_key: str
    actual_value: float
    achievement_pct: float
    evaluation_band: str
    kpi_target_id: uuid.UUID
    locked_at: datetime | None
    measured_at: datetime
    source_document_id: uuid.UUID | None


# ---------- EP-48 check-ins ----------
class CheckInCreate(BaseModel):
    key_result_id: uuid.UUID | None = None
    kpi_id: uuid.UUID | None = None
    value: Decimal = measure(True)
    confidence: Confidence
    note: str | None = Field(default=None, max_length=5000)
    blocker: str | None = Field(default=None, max_length=5000)
    support_needed: str | None = Field(default=None, max_length=5000)
    next_action: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def _exactly_one(self) -> "CheckInCreate":
        if (self.key_result_id is None) == (self.kpi_id is None):
            raise ValueError("exactly one of key_result_id / kpi_id is required")
        return self


class CheckInOut(LogOut):
    key_result_id: uuid.UUID | None
    kpi_id: uuid.UUID | None
    value: float
    confidence: str
    note: str | None
    blocker: str | None
    support_needed: str | None
    next_action: str | None
    checked_in_at: datetime
    user_id: uuid.UUID

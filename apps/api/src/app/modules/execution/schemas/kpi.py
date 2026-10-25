"""EP-KPI-01..10 KPIs / measurements / targets / evaluations (10 §7.2.3; 05 §2.6).

10 ↔ 05 renames (DEC-222): KPI `target` ↔ column `target_value`. Fields added in M1.4 that land
with a later migration (T-626 `strategic_objective_id`/`pillar`, T-627 measurement history +
`latest_evaluation`) default to `None` until their task fills them.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.execution.schemas.common import (
    PERIOD,
    KpiBand,
    KpiDataSource,
    KpiDirection,
    KpiPeriodType,
    KpiValueType,
    LogOut,
    OkrStatus,
    Out,
    Patch,
    Pillar,
    measure,
    weight,
)

METRIC = r"^METRIC-[A-Z]+-\d{2}$"


class KpiEvaluationBrief(BaseModel):
    """Latest `KPIEvaluation` of a KPI (EP-KPI-01/03, EP-STR-01 `KpiNode`)."""

    period_key: str
    actual_value: float
    target: float
    achievement_pct: float
    band: KpiBand
    previous_band: KpiBand | None
    evaluated_at: datetime


class KpiCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=50)
    target: Decimal = measure(True)
    owner_id: uuid.UUID
    metric_code: str | None = Field(default=None, pattern=METRIC)
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
    strategic_objective_id: uuid.UUID | None = None  # root KPI only (EP-KPI-02)
    pillar: Pillar | None = None


class KpiUpdate(Patch):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    target: Decimal | None = measure()
    owner_id: uuid.UUID | None = None
    metric_code: str | None = Field(default=None, pattern=METRIC)
    key_result_id: uuid.UUID | None = None
    direction: KpiDirection | None = None
    value_type: KpiValueType | None = None
    data_source_kind: KpiDataSource | None = None
    parent_kpi_id: uuid.UUID | None = None
    weight_pct: Decimal | None = weight(None)
    initiative_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    status: OkrStatus | None = None
    strategic_objective_id: uuid.UUID | None = None
    pillar: Pillar | None = None


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
    strategic_objective_id: uuid.UUID | None = None
    pillar: str | None = None
    latest_evaluation: KpiEvaluationBrief | None = None


# ---------- EP-KPI-06/07 measurements (R-DEC-51: one row per measurement) ----------
class MeasurementCreate(BaseModel):
    period_key: str = Field(pattern=PERIOD)
    actual_value: Decimal = measure(True)
    source_document_id: uuid.UUID | None = None
    data_source: KpiDataSource = "manual"  # persisted from T-627 (0017)
    note: str | None = Field(default=None, max_length=5000)  # persisted from T-627 (0017)


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
    measured_by: uuid.UUID | None = None
    data_source: str | None = None
    note: str | None = None
    check_in_id: uuid.UUID | None = None


# ---------- EP-KPI-08/09 targets (effective-dated, R-DEC-52) ----------
class KpiTargetCreate(BaseModel):
    period_key: str = Field(pattern=PERIOD)
    target: Decimal = measure(True)
    baseline: Decimal | None = measure()
    minimum: Decimal | None = measure()
    stretch: Decimal | None = measure()
    band_thresholds: dict[KpiBand, float] | None = None
    score_cap_pct: Decimal | None = Field(default=None, ge=0, max_digits=7, decimal_places=4)
    valid_from: date | None = None  # default: business today
    reason: str | None = Field(default=None, max_length=5000)


class KpiTargetOut(Out):
    kpi_id: uuid.UUID
    period_key: str
    baseline: float | None
    minimum: float | None
    target: float
    stretch: float | None
    band_thresholds: dict[str, float]
    score_cap_pct: float
    locked_at: datetime | None
    valid_from: date
    valid_to: date | None
    reason: str | None


# ---------- EP-KPI-10 evaluations (R-DEC-53) ----------
class KpiEvaluationOut(Out):
    kpi_id: uuid.UUID
    period_key: str
    kpi_target_id: uuid.UUID
    measurement_id: uuid.UUID
    actual_value: float
    target: float
    achievement_pct: float
    band: KpiBand
    previous_band: KpiBand | None
    gap_value: float
    measured_on_time: bool
    evaluated_at: datetime
    locked_at: datetime | None

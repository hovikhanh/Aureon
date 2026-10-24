"""EP-OKR-01..11 objectives / key results, EP-PRF-01..06 check-ins (10 §7.2.3; 05 §2.6).

10 ↔ 05 renames (DEC-222): check-in filter `owner_id` ↔ column `user_id`. Fields added in M1.4
that land with a later migration (T-626 `strategic_objective_id`, T-627 at-risk columns +
`kr_measurements`) default to `None` / empty until their task fills them. KPI DTOs live in
`schemas/kpi.py`.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.execution.schemas.common import (
    PERIOD,
    AtRiskReason,
    Confidence,
    GoalTargetType,
    LogOut,
    ObjectiveLevel,
    OkrStatus,
    OkrType,
    Out,
    Patch,
    Pillar,
    measure,
    weight,
)

METRIC = r"^METRIC-[A-Z]+-\d{2}$"


# ---------- EP-OKR-01..05 objectives ----------
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
    strategic_objective_id: uuid.UUID | None = None  # root objective only (EP-OKR-02)


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
    strategic_objective_id: uuid.UUID | None = None


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
    strategic_objective_id: uuid.UUID | None = None
    at_risk_kr_count: int = 0


# ---------- EP-OKR-06..11 key results ----------
class KeyResultCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    baseline: Decimal = measure(True)
    target: Decimal = measure(True)
    unit: str = Field(min_length=1, max_length=50)
    owner_id: uuid.UUID
    metric_code: str | None = Field(default=None, pattern=METRIC)
    current_value: Decimal | None = measure()
    status: OkrStatus = "draft"
    weight_pct: Decimal = weight()


class KeyResultUpdate(Patch):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    baseline: Decimal | None = measure()
    target: Decimal | None = measure()
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    owner_id: uuid.UUID | None = None
    metric_code: str | None = Field(default=None, pattern=METRIC)
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
    at_risk: bool = False
    at_risk_since: datetime | None = None
    at_risk_reasons: list[AtRiskReason] = Field(default_factory=list)
    last_checked_in_at: datetime | None = None


class KrMeasurementOut(LogOut):
    """ENT-KRMeasurement (EP-OKR-11, R-DEC-53)."""

    key_result_id: uuid.UUID
    check_in_id: uuid.UUID | None
    period_key: str
    value: float
    progress_pct: float
    previous_progress_pct: float | None
    confidence: Confidence
    measured_at: datetime
    measured_by: uuid.UUID | None


# ---------- EP-PRF-01..06 check-ins ----------
class CheckInCreate(BaseModel):
    """EP-PRF-02 / EP-PRF-04 body — the target is the path (`/key-results/{id}`, `/kpis/{id}`)."""

    value: Decimal = measure(True)
    confidence: Confidence
    note: str | None = Field(default=None, max_length=5000)
    blocker: str | None = Field(default=None, max_length=5000)
    support_needed: str | None = Field(default=None, max_length=5000)
    next_action: str | None = Field(default=None, max_length=5000)


class KrMeasurementBrief(BaseModel):
    value: float
    progress_pct: float
    previous_progress_pct: float | None


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
    target_type: GoalTargetType | None = None
    target_title: str | None = None
    department_id: uuid.UUID | None = None
    kr_measurement: KrMeasurementBrief | None = None


class CheckInDueOut(BaseModel):
    """EP-PRF-06 — one F4 card of the caller; `prefill` stays `null` in M1.4 (M2.4)."""

    target_type: GoalTargetType
    target_id: uuid.UUID
    title: str
    unit: str
    current_value: float | None
    target: float
    confidence: Confidence | None
    last_checked_in_at: datetime | None
    due: bool
    prefill: None = None

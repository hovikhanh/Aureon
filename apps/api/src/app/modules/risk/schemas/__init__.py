"""Risk API DTOs (10 §3.10, §4 EP-101..106). API names follow 10; columns follow 05 (DEC-215).

10 ↔ 05 mapping (in the service, never in the DB): `level` ↔ `severity`; `linked_entities`
is the 05 jsonb object of soft refs `{hiring_plan_id, budget_id, deal_id, product_id,
client_id, …}`; assessment `note` ↔ `rationale`.
"""

import re
import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Category = Literal[
    "financial", "operational", "strategic", "people", "business", "customer", "product",
    "technology", "security", "compliance", "legal", "partner_supplier", "ai",
]  # fmt: skip
Level = Literal["low", "medium", "high", "critical"]
RiskStatus = Literal[
    "proposed", "identified", "assessed", "mitigating", "monitoring", "accepted", "closed",
    "rejected",
]  # fmt: skip
RiskSource = Literal["manual", "event", "ai", "document"]
_LINK_KEY = re.compile(r"^[a-z][a-z_]{1,40}_id$")


def check_links(value: dict[str, uuid.UUID] | None) -> dict[str, uuid.UUID] | None:
    """`linked_entities` keys must be `<entity>_id` soft refs (05 ENT-Risk)."""
    if value is None:
        return None
    bad = sorted(k for k in value if not _LINK_KEY.match(k))
    if bad:
        raise ValueError(f"linked_entities keys must be `<entity>_id`: {bad}")
    return value


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class RiskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    category: Category
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    owner_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    linked_entities: dict[str, uuid.UUID] = Field(default_factory=dict, max_length=20)
    review_date: date | None = None

    _links = field_validator("linked_entities")(check_links)


class RiskUpdate(BaseModel):
    """PATCH: only sent fields; `status` changes go through EP-106 / EP-104."""

    model_config = ConfigDict(extra="forbid")

    version: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    category: Category | None = None
    owner_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    linked_entities: dict[str, uuid.UUID] | None = Field(default=None, max_length=20)
    review_date: date | None = None

    _links = field_validator("linked_entities")(check_links)


class RiskOut(_Out):
    code: str
    title: str
    description: str | None
    category: Category
    likelihood: int
    impact: int
    risk_score: int
    level: Level
    status: RiskStatus
    risk_source: RiskSource
    owner_id: uuid.UUID | None
    department_id: uuid.UUID | None
    linked_entities: dict[str, Any]
    review_date: date | None
    identified_at: datetime
    proposed_at: datetime | None
    confirmed_by: uuid.UUID | None
    confirmed_at: datetime | None
    accepted_by: uuid.UUID | None
    accepted_reason: str | None
    accepted_at: datetime | None
    source_event_id: uuid.UUID | None
    source_document_id: uuid.UUID | None


# ---------- EP-102 ----------
class AssessmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    note: str | None = Field(default=None, max_length=2000)


class AssessmentOut(BaseModel):
    id: uuid.UUID
    risk_id: uuid.UUID
    likelihood: int
    impact: int
    risk_score: int
    level: Level
    note: str | None
    assessed_at: datetime
    assessed_by: uuid.UUID | None


# ---------- EP-104 / EP-106 ----------
class AcceptIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=2000)


class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_status: RiskStatus
    reason: str | None = Field(default=None, max_length=2000)
    owner_id: uuid.UUID | None = None


# ---------- EP-103 mitigations ----------
MitigationStatus = Literal["planned", "in_progress", "done", "cancelled"]


class MitigationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_id: uuid.UUID
    title: str = Field(min_length=1, max_length=300)
    owner_id: uuid.UUID
    due_date: date
    progress_pct: float = Field(default=0, ge=0, le=100)
    status: MitigationStatus = "planned"
    task_id: uuid.UUID | None = None


class MitigationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    owner_id: uuid.UUID | None = None
    due_date: date | None = None
    progress_pct: float | None = Field(default=None, ge=0, le=100)
    status: MitigationStatus | None = None
    task_id: uuid.UUID | None = None


class MitigationOut(_Out):
    risk_id: uuid.UUID
    title: str
    owner_id: uuid.UUID
    due_date: date
    progress_pct: float
    status: MitigationStatus
    completed_at: datetime | None
    task_id: uuid.UUID | None
    overdue: bool


class HeatCell(BaseModel):
    likelihood: int
    impact: int
    count: int


# ---------- EP-105 what-if ----------
DomainStatus = Literal["ok", "unavailable"]


class ScenarioAssumptions(BaseModel):
    """Optional overrides of the default risk → impact heuristics (DEC-219)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=200)
    revenue_change_pct: float | None = Field(default=None, ge=-100, le=100)
    expense_change_pct: float | None = Field(default=None, ge=-100, le=200)
    extra_monthly_cost: int | None = Field(default=None, ge=0)
    headcount_change_pct: float | None = Field(default=None, ge=-100, le=100)


class ScenarioIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_ids: list[uuid.UUID] = Field(min_length=1, max_length=10)
    horizon_months: int = Field(ge=1, le=24)
    assumptions: ScenarioAssumptions | None = None


class FinanceImpact(BaseModel):
    status: DomainStatus
    revenue_delta: int | None = None
    expense_delta: int | None = None
    runway_delta_months: float | None = None


class SalesImpact(BaseModel):
    status: DomainStatus
    pipeline_delta: int | None = None


class HrImpact(BaseModel):
    status: DomainStatus
    headcount_delta: int | None = None


class ProductImpact(BaseModel):
    status: DomainStatus
    roadmap_items_at_risk: int | None = None


class ScenarioImpacts(BaseModel):
    finance: FinanceImpact
    sales: SalesImpact
    hr: HrImpact
    product: ProductImpact


class SourceRef(BaseModel):
    """10 §4.10 SourceRef."""

    type: Literal["metric_value", "record", "document_page", "tool_result"]
    id: str
    label: str
    period_key: str | None = None
    value: float | int | None = None
    lineage_url: str | None = None


class ScenarioOut(BaseModel):
    scenario_id: uuid.UUID
    impacts: ScenarioImpacts
    sources: list[SourceRef]


# ---------- EP-100 dashboard (10 §5) ----------
class PeriodOut(BaseModel):
    key: str
    type: str
    start_date: date
    end_date: date


class RiskSummary(BaseModel):
    open_risks: int
    critical_count: int
    high_count: int
    aggregate_risk_score: float | None
    opened_in_period: int
    closed_in_period: int
    mitigations_active: int
    mitigations_overdue: int
    unacknowledged_alerts: int
    strategy_execution_index: float | None


class RiskScorePoint(BaseModel):
    period_key: str
    aggregate_risk_score: float | None
    open_risks: int


class RiskDashboardOut(BaseModel):
    pillar: Literal["S"] = "S"
    status: Literal["ok", "warning", "critical", "no_data"]
    period: PeriodOut
    summary: RiskSummary
    heatmap: list[HeatCell]
    metrics: list[dict[str, Any]]
    risk_score_trend: list[RiskScorePoint]
    open_alerts: int

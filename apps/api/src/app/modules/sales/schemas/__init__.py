"""Sales API DTOs (10 §4.7). API field names follow 10; columns follow 05 (DEC-190).

10 ↔ 05 renames are handled in the service, never in the DB: client `size`↔`company_size`,
client `contacts[]`↔`contact_person/contact_email/contact_phone` (05 stores one contact →
at most 1 item), deal `owner_id`↔`assigned_to`. Fields beyond the 10 "main fields" column
carry the exact 05 column name.
"""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CompanySize = Literal["startup", "small", "medium", "enterprise"]
ClientStatus = Literal["prospect", "active", "churned"]
DealStage = Literal["lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"]


def currency_field() -> Any:
    return Field(default="VND", pattern=r"^[A-Z]{3}$")


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class _Patch(BaseModel):
    """PATCH bodies: only sent fields are applied (`model_dump(exclude_unset=True)`)."""

    model_config = ConfigDict(extra="forbid")

    version: int | None = None


# ---------- EP-71 clients ----------
class Contact(BaseModel):
    """PII level 3 (02 §6.3) — never in events; replaced by `••••` in audit snapshots."""

    name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=30)


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    tax_code: str | None = Field(default=None, min_length=1, max_length=20)
    industry: str | None = Field(default=None, max_length=200)
    size: CompanySize | None = None
    contacts: list[Contact] = Field(default_factory=list, max_length=1)
    status: ClientStatus = "prospect"
    address: str | None = Field(default=None, max_length=500)
    website: str | None = Field(default=None, max_length=300)
    account_owner_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ClientUpdate(_Patch):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    tax_code: str | None = Field(default=None, min_length=1, max_length=20)
    industry: str | None = Field(default=None, max_length=200)
    size: CompanySize | None = None
    contacts: list[Contact] | None = Field(default=None, max_length=1)
    status: ClientStatus | None = None
    address: str | None = Field(default=None, max_length=500)
    website: str | None = Field(default=None, max_length=300)
    account_owner_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class SimilarClient(BaseModel):
    id: uuid.UUID
    name: str
    score: float


class ClientOut(_Out):
    name: str
    tax_code: str | None
    industry: str | None
    size: str | None
    contacts: list[Contact]
    status: str
    address: str | None
    website: str | None
    account_owner_id: uuid.UUID | None
    merged_into_id: uuid.UUID | None
    notes: str | None
    similar_clients: list[SimilarClient] = Field(default_factory=list)


# ---------- EP-72 deals ----------
class DealCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    client_id: uuid.UUID
    deal_value: int
    currency: str = currency_field()
    probability_pct: float = Field(ge=0, le=100)
    expected_close_date: date
    owner_id: uuid.UUID
    product_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)
    description: str | None = Field(default=None, max_length=2000)


class DealUpdate(_Patch):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    client_id: uuid.UUID | None = None
    deal_value: int | None = None
    probability_pct: float | None = Field(default=None, ge=0, le=100)
    expected_close_date: date | None = None
    owner_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    tags: list[str] | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=2000)


class DealOut(_Out):
    name: str
    client_id: uuid.UUID
    deal_value: int
    currency: str
    stage: str
    probability_pct: float
    weighted_value: int
    expected_close_date: date | None
    closed_at: datetime | None
    lost_reason: str | None
    owner_id: uuid.UUID
    department_id: uuid.UUID | None
    product_id: uuid.UUID | None
    tags: list[str]
    description: str | None


# ---------- EP-73 / EP-74 stage ----------
class StageChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_stage: DealStage
    lost_reason: str | None = Field(default=None, min_length=1, max_length=1000)


class StageHistoryOut(BaseModel):
    """EP-74 row; `changed_by` is null — 05 `deal_stage_history` has no actor column (DEC-191).

    The actor of every transition is in `ENT-AuditLog` (`sales.deal_stage_change`).
    """

    from_stage: str | None
    to_stage: str
    changed_by: uuid.UUID | None
    changed_at: datetime


# ---------- EP-77 targets ----------
TargetPeriodType = Literal["month", "quarter", "year"]
TargetScope = Literal["team", "individual"]


class TargetCreate(BaseModel):
    period_type: TargetPeriodType
    period_key: str = Field(max_length=7)
    scope: TargetScope
    owner_id: uuid.UUID | None = None
    target_amount: int
    currency: str = currency_field()


class TargetUpdate(_Patch):
    target_amount: int | None = None
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")


class TargetOut(_Out):
    period_type: str
    period_key: str
    scope: str
    owner_id: uuid.UUID | None
    target_amount: int
    currency: str


# ---------- EP-75 pipeline / EP-76 performance ----------
class PeriodOut(BaseModel):
    key: str
    type: str
    start_date: date
    end_date: date


class PipelineStage(BaseModel):
    stage: str
    count: int
    value: int
    weighted_value: int
    avg_days_in_stage: float | None


class PipelineOut(BaseModel):
    period: PeriodOut | None
    stages: list[PipelineStage]
    coverage_ratio: float | None
    currency: str = "VND"


GroupBy = Literal["team", "owner"]


class PerformanceRow(BaseModel):
    owner_ref: str
    closed_value: int
    quota: int | None
    attainment_pct: float | None
    win_rate_pct: float | None


# ---------- EP-70 dashboard (10 §5) ----------
class SalesSummary(BaseModel):
    pipeline_value: int
    weighted_pipeline: int
    deals_open: int
    deals_won: int
    deals_lost: int
    win_rate_pct: float | None
    avg_deal_value: int | None
    closed_revenue: int
    quota_attainment_pct: float | None
    avg_sales_cycle_days: float | None
    pipeline_coverage: float | None
    currency: str = "VND"


class PipelineTrendPoint(BaseModel):
    period_key: str
    pipeline_value: int
    weighted_pipeline: int


class WinRateTrendPoint(BaseModel):
    period_key: str
    won: int
    lost: int
    win_rate_pct: float | None


class SalesDashboardOut(BaseModel):
    pillar: Literal["C"] = "C"
    status: Literal["ok", "warning", "critical", "no_data"]
    period: PeriodOut
    summary: SalesSummary
    metrics: list[dict[str, Any]]
    pipeline_trend: list[PipelineTrendPoint]
    win_rate_trend: list[WinRateTrendPoint]

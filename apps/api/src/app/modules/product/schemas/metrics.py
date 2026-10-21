"""EP-95 product metric snapshots + EP-90 dashboard DTOs (10 §4.9, §5).

API `adoption_pct` ↔ column `adoption_rate_pct` (DEC-210). Snapshots are append-only: a second
snapshot for the same period supersedes the current one (05 C5).
"""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


def _pct() -> Any:
    return Field(default=None, ge=0, le=100)


class MetricCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_key: str = Field(pattern=MONTH_PATTERN)
    mau: int = Field(ge=0)
    dau: int | None = Field(default=None, ge=0)
    adoption_pct: float | None = _pct()
    churn_rate_pct: float = Field(ge=0, le=100)
    retention_30d_pct: float | None = _pct()
    nps: float | None = Field(default=None, ge=-100, le=100)
    arpu: int | None = Field(default=None, ge=0)
    currency: str = Field(default="VND", pattern=r"^[A-Z]{3}$")
    source_document_id: uuid.UUID | None = None


class MetricOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    period_key: str
    mau: int
    dau: int | None
    adoption_pct: float | None
    churn_rate_pct: float
    retention_30d_pct: float | None
    nps: float | None
    arpu: int | None
    currency: str
    superseded_by_id: uuid.UUID | None
    source_document_id: uuid.UUID | None
    created_at: datetime


# ---------- EP-90 dashboard (10 §5) ----------
class PeriodOut(BaseModel):
    key: str
    type: str
    start_date: date
    end_date: date


class ProductSummary(BaseModel):
    products_total: int
    products_active: int
    products_in_dev: int
    mau: int | None
    adoption_pct: float | None
    churn_rate_pct: float | None
    retention_30d_pct: float | None
    nps: float | None
    arpu: int | None
    currency: str = "VND"
    features_released: int
    roadmap_on_time_pct: float | None


class MauPoint(BaseModel):
    period_key: str
    mau: int | None


class ChurnPoint(BaseModel):
    period_key: str
    churn_rate_pct: float | None


class ProductDashboardOut(BaseModel):
    pillar: Literal["U"] = "U"
    status: Literal["ok", "warning", "critical", "no_data"]
    period: PeriodOut
    summary: ProductSummary
    metrics: list[dict[str, Any]]
    mau_trend: list[MauPoint]
    churn_trend: list[ChurnPoint]
    open_alerts: int | None = None  # 10 §5; None when the metric store is unavailable

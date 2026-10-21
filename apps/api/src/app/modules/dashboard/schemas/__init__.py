"""Pydantic v2 schemas of `dashboard` (10 §4.2: MetricValueOut, MetricDetail, AlertOut)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Pillar = Literal["F", "O", "C", "U", "S"]
MetricStatus = Literal["ok", "warning", "critical", "no_data"]
PillarState = Literal["ok", "warning", "critical", "no_data", "unavailable"]


class MetricValueOut(BaseModel):
    metric_code: str
    pillar: Pillar | None
    value: float | None
    unit: str
    currency: str | None = None
    status: MetricStatus
    status_reason: str | None = None
    period_key: str
    computed_at: datetime
    freshness: Literal["fresh", "stale"]
    data_quality_pct: float | None = None
    lineage_url: str


class Thresholds(BaseModel):
    warning: float
    critical: float


class TrendPoint(BaseModel):
    period_key: str
    value: float | None


class BreakdownRow(BaseModel):
    key: str
    label: str
    value: float | None
    record_count: int


class DataSource(BaseModel):
    module: str
    entities: list[str]


class AlertOut(BaseModel):
    id: uuid.UUID
    alert_code: str
    metric_code: str
    pillar: Pillar | None
    severity: Literal["warning", "critical"]
    status: Literal["open", "acknowledged", "resolved", "dismissed"]
    scope: dict[str, str] = Field(default_factory=dict)
    value: float | None
    threshold: float
    period_key: str
    raised_at: datetime
    acknowledged_by: uuid.UUID | None = None
    message_key: str
    message_params: dict[str, Any]


class MetricDetail(MetricValueOut):
    name: str
    formula_display: str
    direction: Literal["up", "down"]
    thresholds: Thresholds
    trend: list[TrendPoint]
    breakdown: list[BreakdownRow]
    related_alerts: list[AlertOut]
    data_source: DataSource


class AcknowledgeIn(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class DismissIn(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class PillarCard(BaseModel):
    """Pillar status (03 §4) — used by the 5 domain dashboards and EP-10."""

    pillar: Pillar
    status: PillarState
    metrics_with_data: int
    metrics_total: int
    open_alerts: int

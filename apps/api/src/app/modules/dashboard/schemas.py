"""Pydantic schemas for Dashboard endpoints (10 §4 EP-10..EP-17)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.modules.dashboard.enums import (
    AlertSeverity,
    AlertStatus,
    MetricUnit,
    ThresholdStatus,
)

AccessLevel = Literal["FULL", "AGG"]
MetricValueState = Literal["OK", "NO_DATA", "NOT_COMPUTABLE"]


class SparklinePoint(BaseModel):
    """MetricValueOut.sparkline point (10 §3)."""

    period_key: str
    value: float | None


class OpenAlertRef(BaseModel):
    """Compact alert reference in MetricValueOut.open_alert (10 §3)."""

    id: UUID
    alert_code: str
    severity: AlertSeverity


class MetricValueOut(BaseModel):
    """A single current metric value for display — fields fixed by 10 §3 (EP-10..EP-12)."""

    metric_code: str
    pillar: str
    name_i18n_key: str
    unit: MetricUnit
    chart_type: str
    access_level: AccessLevel = "FULL"
    period_key: str
    value: float | None
    value_state: MetricValueState = "OK"
    not_computable_reason: str | None = None
    display_hint: str | None = None
    target_value: float | None = None
    status_color: ThresholdStatus | None = None
    warning_threshold: float | None = None
    critical_threshold: float | None = None
    sparkline: list[SparklinePoint] = []
    computed_at: datetime | None
    open_alert: OpenAlertRef | None = None


class AlertOut(BaseModel):
    """Alert for dashboard cards and alert list — fields fixed by 10 §3."""

    id: UUID
    alert_code: str
    metric_code: str
    pillar: str
    severity: AlertSeverity
    status: AlertStatus
    period_key: str
    title_i18n_key: str
    message_params: dict[str, Any]
    suggestion_level: Literal["L1"] = "L1"
    suggested_action_i18n_key: str
    triggered_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    dismissed_at: datetime | None = None
    can_acknowledge: bool = False


class PillarOut(BaseModel):
    """One pillar block in EP-10 dashboard response."""

    pillar: str
    access_level: AccessLevel
    health_color: ThresholdStatus
    open_alert_count: int
    headline_metric: MetricValueOut | None
    metrics: list[MetricValueOut]


class SummaryOut(BaseModel):
    """AI read-only summary (template-based, 10 EP-10 `summary`)."""

    i18n_key: str
    params: dict[str, Any]
    suggestion_level: Literal["L1"] = "L1"


class GreetingOut(BaseModel):
    full_name: str
    salutation: str | None = None


class DashboardOut(BaseModel):
    """EP-10 response."""

    role_code: str
    greeting: GreetingOut
    summary: SummaryOut
    pillars: list[PillarOut]
    alerts_top: list[AlertOut]


class LineagePanelOut(BaseModel):
    """P01 panel (10 EP-12 `lineage_panel`)."""

    formula_display: str
    formula_expr: str
    source_record_types: list[str]
    computed_at: datetime | None
    computation: str | None
    source_record_count: int | None = None
    source_documents: list[dict[str, Any]] | None = None


class HistoryPointOut(BaseModel):
    period_key: str
    value: float | None
    target_value: float | None = None
    value_state: MetricValueState = "OK"
    status_color: ThresholdStatus | None = None


class BreakdownRowOut(BaseModel):
    key: str
    label: str
    value: float | None
    share: float | None = None
    record_filter: str | None = None


class BreakdownOut(BaseModel):
    dimension: str
    rows: list[BreakdownRowOut]


class MetricDetailOut(BaseModel):
    """EP-12 response."""

    metric: MetricValueOut
    lineage_panel: LineagePanelOut
    computation_inputs: dict[str, Any] | None = None
    history: list[HistoryPointOut]
    breakdown: BreakdownOut | None = None
    alert: AlertOut | None = None


class RecordOut(BaseModel):
    """One source business record (EP-13)."""

    id: UUID
    record_type: str
    code: str | None = None
    name: str | None = None
    period_key: str | None = None
    issue_date: str | None = None
    total_amount: int | None = None
    amount_due: int | None = None
    status: str | None = None
    source_document_id: UUID | None = None
    attributes: dict[str, Any] = {}


class LineageDocumentOut(BaseModel):
    id: UUID
    original_filename: str | None = None
    doc_type: str | None = None
    page: int | None = None
    source_location: dict[str, Any] | None = None
    restricted: bool = False
    reason: str | None = None


class LineageFieldOut(BaseModel):
    field_key: str
    value: Any | None = None
    confidence: float | None = None
    source_location: dict[str, Any] | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class RecordLineageOut(BaseModel):
    """EP-14 response: lineage of one business record → fields → documents."""

    record: RecordOut
    fields: list[LineageFieldOut]
    documents: list[LineageDocumentOut]


class AlertActionRequest(BaseModel):
    note: str | None = None


class AlertDismissRequest(BaseModel):
    reason: str

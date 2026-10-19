"""SQLAlchemy ORM models for the Dashboard domain.

Matches docs/2.PRODUCT/05-DATA-MODEL.md §4.9 (metrics), §4.10 (metric_values),
§4.11 (alerts).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.dashboard.enums import (
    AlertSeverity,
    AlertStatus,
    MetricUnit,
    MetricValueKind,
    PeriodType,
    ThresholdDirection,
    ThresholdStatus,
    ValueOrigin,
)


class Metric(Base):
    """ENT-Metric: definition of a dashboard KPI (05 §4.9)."""

    __tablename__ = "metrics"
    __table_args__ = (
        UniqueConstraint("code", name="uq_metrics_code"),
        UniqueConstraint("alert_code", name="uq_metrics_alert_code"),
        Index("ix_metrics_pillar", "pillar"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    pillar: Mapped[str] = mapped_column(Text, nullable=False)
    name_i18n_key: Mapped[str] = mapped_column(Text, nullable=False)
    formula_display: Mapped[str] = mapped_column(Text, nullable=False)
    formula_expr: Mapped[str] = mapped_column(Text, nullable=False)
    source_record_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    unit: Mapped[MetricUnit] = mapped_column(
        SQLEnum(MetricUnit, name="metric_unit_enum", native_enum=False), nullable=False
    )
    direction: Mapped[ThresholdDirection] = mapped_column(
        SQLEnum(ThresholdDirection, name="threshold_direction_enum", native_enum=False),
        nullable=False,
    )
    warning_threshold: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    critical_threshold: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    threshold_rule: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    chart_type: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_policy: Mapped[str] = mapped_column(Text, nullable=False)
    alert_code: Mapped[str] = mapped_column(Text, nullable=False)
    alert_recipient_role_codes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    alert_suggestion_i18n_key: Mapped[str] = mapped_column(Text, nullable=False)
    agg_visible_role_codes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    values: Mapped[list[MetricValue]] = relationship(
        "MetricValue", back_populates="metric", foreign_keys="MetricValue.metric_id"
    )
    alerts: Mapped[list[Alert]] = relationship("Alert", back_populates="metric")


class MetricValue(Base):
    """ENT-MetricValue: a metric value for a period, with lineage (05 §4.10)."""

    __tablename__ = "metric_values"
    __table_args__ = (
        Index("ix_metric_values_metric_id", "metric_id"),
        Index("ix_metric_values_superseded_by_id", "superseded_by_id"),
        Index(
            "uq_metric_values_current",
            "metric_id",
            "value_kind",
            "period_key",
            unique=True,
            postgresql_where=text("is_current AND deleted_at IS NULL"),
        ),
        Index(
            "ix_metric_values_source_record_ids",
            "source_record_ids",
            postgresql_using="gin",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    metric_id: Mapped[UUID] = mapped_column(
        ForeignKey("metrics.id", ondelete="CASCADE"), nullable=False
    )
    value_kind: Mapped[MetricValueKind] = mapped_column(
        SQLEnum(MetricValueKind, name="metric_value_kind_enum", native_enum=False),
        nullable=False,
    )
    period_type: Mapped[PeriodType] = mapped_column(
        SQLEnum(PeriodType, name="period_type_enum", native_enum=False), nullable=False
    )
    period_key: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    computation: Mapped[ValueOrigin] = mapped_column(
        SQLEnum(ValueOrigin, name="value_origin_enum", native_enum=False), nullable=False
    )
    source_record_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)), nullable=False, default=list
    )
    source_document_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)), nullable=False, default=list
    )
    status_color: Mapped[ThresholdStatus | None] = mapped_column(
        SQLEnum(ThresholdStatus, name="threshold_status_enum", native_enum=False),
        nullable=True,
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    superseded_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("metric_values.id", ondelete="SET NULL"), nullable=True
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    computed_by_action: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    metric: Mapped[Metric] = relationship(
        "Metric", back_populates="values", foreign_keys=[metric_id]
    )


class Alert(Base):
    """ENT-Alert: a threshold breach alert tied to a metric value (05 §4.11)."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_metric_id", "metric_id"),
        Index("ix_alerts_metric_value_id", "metric_value_id"),
        Index("ix_alerts_acknowledged_by_id", "acknowledged_by_id"),
        Index("ix_alerts_dismissed_by_id", "dismissed_by_id"),
        Index(
            "uq_alerts_open",
            "metric_id",
            "period_key",
            unique=True,
            postgresql_where=text("status IN ('OPEN','ACKNOWLEDGED') AND deleted_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    metric_id: Mapped[UUID] = mapped_column(
        ForeignKey("metrics.id", ondelete="CASCADE"), nullable=False
    )
    metric_value_id: Mapped[UUID] = mapped_column(
        ForeignKey("metric_values.id", ondelete="CASCADE"), nullable=False
    )
    period_key: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        SQLEnum(AlertSeverity, name="alert_severity_enum", native_enum=False), nullable=False
    )
    status: Mapped[AlertStatus] = mapped_column(
        SQLEnum(AlertStatus, name="alert_status_enum", native_enum=False),
        nullable=False,
        default=AlertStatus.OPEN,
    )
    message_params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    suggestion_level: Mapped[str] = mapped_column(Text, nullable=False, default="L1")
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    acknowledged_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    metric: Mapped[Metric] = relationship("Metric", back_populates="alerts")

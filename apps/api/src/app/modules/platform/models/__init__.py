"""Schema `platform` — 12 tables (05 §4.10, §5). Column groups follow 05 §2.1."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, ORMExecuteState, Session, mapped_column

from app.core.base_model import (
    DEFAULT_TENANT_ID,
    BusinessModel,
    ConfigModel,
    LogModel,
    TenantMixin,
)
from app.core.columns import currency, fk, measure, money, schema_args, sr, txt
from app.core.enums import (
    ACTOR_TYPE,
    ALERT_SEVERITY,
    ALERT_STATUS,
    APPROVAL_STATUS,
    AUTONOMY_LEVEL,
    EMAIL_STATUS,
    LINEAGE_KIND,
    METRIC_UNIT,
    METRIC_VALUE_KIND,
    NOTIFICATION_KIND,
    OUTBOX_STATUS,
    PERIOD_TYPE,
    PILLAR,
    PROCESSING_STATUS,
    REPORT_FORMAT,
    REPORT_KIND,
    REPORT_STATUS,
    ROLE_CODE,
    SCOPE_TYPE,
    THRESHOLD_DIRECTION,
    THRESHOLD_STATUS,
    VALUE_ORIGIN,
)

S = "platform"
TS = DateTime(timezone=True)
ZERO_UUID = "'00000000-0000-0000-0000-000000000000'::uuid"


# ---------- config / catalog ----------
class Metric(ConfigModel):
    __tablename__ = "metrics"
    __table_args__ = schema_args(S)

    code: Mapped[str] = txt(unique=True)
    alert_code: Mapped[str] = txt(unique=True)
    pillar: Mapped[str | None] = mapped_column(PILLAR, nullable=True)
    name_vi: Mapped[str] = txt()
    name_en: Mapped[str] = txt()
    unit: Mapped[str] = mapped_column(METRIC_UNIT, nullable=False)
    direction: Mapped[str] = mapped_column(THRESHOLD_DIRECTION, nullable=False)
    warning_threshold: Mapped[Any] = measure(nullable=False)
    critical_threshold: Mapped[Any] = measure(nullable=False)
    source_module: Mapped[str] = txt()
    formula_ref: Mapped[str] = txt()
    refresh_events: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)


class ApprovalRule(ConfigModel):
    __tablename__ = "approval_rules"
    __table_args__ = (
        CheckConstraint("sla_hours > 0", name="sla_hours_positive"),
        {"schema": S},
    )

    code: Mapped[str] = txt(unique=True)
    target_kind: Mapped[str] = txt()
    condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    approver_role_codes: Mapped[list[str]] = mapped_column(ARRAY(ROLE_CODE), nullable=False)
    second_approver_role_codes: Mapped[list[str] | None] = mapped_column(
        ARRAY(ROLE_CODE), nullable=True
    )
    sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("8"))
    escalate_to_role_code: Mapped[str | None] = mapped_column(ROLE_CODE, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("100"))


class SystemSetting(ConfigModel):
    __tablename__ = "system_settings"
    __table_args__ = (
        CheckConstraint("is_secret = false", name="no_secrets_in_db"),
        {"schema": S},
    )

    key: Mapped[str] = txt(unique=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    updated_reason: Mapped[str | None] = txt(nullable=True)


# ---------- business ----------
class MetricValue(BusinessModel):
    __tablename__ = "metric_values"
    __table_args__ = (
        Index(
            "uq_metric_values_current",
            "metric_id",
            "kind",
            "period_key",
            "scope_type",
            text(f"COALESCE(scope_id, {ZERO_UUID})"),
            unique=True,
            postgresql_where=text("is_current"),
        ),
        Index("ix_metric_values_metric_id_period_key", "metric_id", "period_key"),
        {"schema": S},
    )

    metric_id: Mapped[uuid.UUID] = fk(f"{S}.metrics.id")
    kind: Mapped[str] = mapped_column(METRIC_VALUE_KIND, nullable=False)
    period_type: Mapped[str] = mapped_column(PERIOD_TYPE, nullable=False)
    period_key: Mapped[str] = txt()
    scope_type: Mapped[str] = mapped_column(SCOPE_TYPE, nullable=False)
    scope_id: Mapped[uuid.UUID | None] = sr(index=False)
    value: Mapped[Any] = measure()
    threshold_status: Mapped[str | None] = mapped_column(THRESHOLD_STATUS, nullable=True)
    origin: Mapped[str] = mapped_column(VALUE_ORIGIN, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    data_quality_score: Mapped[Any] = mapped_column(Numeric(5, 2), nullable=True)


class Alert(BusinessModel):
    __tablename__ = "alerts"
    __table_args__ = (
        Index(
            "uq_alerts_open_per_period",
            "metric_id",
            "period_key",
            unique=True,
            postgresql_where=text("status IN ('OPEN','ACKNOWLEDGED') AND deleted_at IS NULL"),
        ),
        {"schema": S},
    )

    metric_id: Mapped[uuid.UUID] = fk(f"{S}.metrics.id")
    metric_value_id: Mapped[uuid.UUID] = fk(f"{S}.metric_values.id")
    severity: Mapped[str] = mapped_column(ALERT_SEVERITY, nullable=False)
    status: Mapped[str] = mapped_column(ALERT_STATUS, nullable=False)
    period_key: Mapped[str] = txt()
    message_vi: Mapped[str] = txt()
    message_en: Mapped[str] = txt()
    raised_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    acknowledged_by: Mapped[uuid.UUID | None] = sr()
    acknowledged_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    dismissed_by: Mapped[uuid.UUID | None] = sr()
    dismissed_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    dismiss_reason: Mapped[str | None] = txt(nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class ApprovalRequest(BusinessModel):
    __tablename__ = "approval_requests"
    __table_args__ = (
        CheckConstraint("step IN (1, 2)", name="step_1_or_2"),
        CheckConstraint(
            "second_decided_by IS NULL OR (second_decided_by <> first_decided_by "
            "AND second_decided_by <> requested_by)",
            name="distinct_approvers",
        ),
        Index("ix_approval_requests_status_due_at", "status", "due_at"),
        Index("ix_approval_requests_target", "target_table", "target_id"),
        Index(
            "ix_approval_requests_tenant_id_status_department_id",
            "tenant_id",
            "status",
            "department_id",
        ),
        {"schema": S},
    )

    rule_id: Mapped[uuid.UUID] = fk(f"{S}.approval_rules.id")
    target_kind: Mapped[str] = txt()  # 0015 — stored, from the rule (R-DEC-45)
    department_id: Mapped[uuid.UUID | None] = sr(index=False)  # 0015 — MGR `d` inbox scope
    target_schema: Mapped[str | None] = txt(nullable=True)
    target_table: Mapped[str | None] = txt(nullable=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ai_action_id: Mapped[uuid.UUID | None] = sr()
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    amount: Mapped[int | None] = money(nullable=True)
    currency: Mapped[str] = currency()
    requested_by: Mapped[uuid.UUID] = sr(nullable=False)
    status: Mapped[str] = mapped_column(APPROVAL_STATUS, nullable=False)
    step: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    first_decided_by: Mapped[uuid.UUID | None] = sr()
    first_decided_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    second_decided_by: Mapped[uuid.UUID | None] = sr()
    second_decided_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    decision_reason: Mapped[str | None] = txt(nullable=True)
    due_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    escalated_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class Report(BusinessModel):
    __tablename__ = "reports"
    __table_args__ = (
        Index(
            "uq_reports_period_scope_format",
            "kind",
            "period_key",
            "scope_type",
            text(f"COALESCE(scope_id, {ZERO_UUID})"),
            "format",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": S},
    )

    kind: Mapped[str] = mapped_column(REPORT_KIND, nullable=False)
    period_key: Mapped[str] = txt()
    scope_type: Mapped[str] = mapped_column(SCOPE_TYPE, nullable=False)
    scope_id: Mapped[uuid.UUID | None] = sr(index=False)
    format: Mapped[str] = mapped_column(REPORT_FORMAT, nullable=False)
    status: Mapped[str] = mapped_column(REPORT_STATUS, nullable=False)
    storage_key: Mapped[str | None] = txt(nullable=True)
    requested_by: Mapped[uuid.UUID | None] = sr()
    generated_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    metric_snapshot: Mapped[Any] = mapped_column(JSONB, nullable=True)
    ai_summary_insight_id: Mapped[uuid.UUID | None] = sr()


# ---------- append-only / technical ----------
class DataLineage(LogModel, TenantMixin):
    """ENT-DataLineage — append-only; M1.5 (05 §2.7, R-DEC-64): `tenant_id`, the
    `idp.document_actions` row that wrote it (logical ref, no cross-schema FK) and `row_index`."""

    __tablename__ = "data_lineage"
    __table_args__ = (
        Index("ix_data_lineage_target", "target_schema", "target_table", "target_id"),
        Index(
            "ix_data_lineage_target_live",
            "target_schema",
            "target_table",
            "target_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        {"schema": S},
    )

    link_kind: Mapped[str] = mapped_column(LINEAGE_KIND, nullable=False)
    metric_value_id: Mapped[uuid.UUID | None] = fk(f"{S}.metric_values.id", nullable=True)
    target_schema: Mapped[str | None] = txt(nullable=True)
    target_table: Mapped[str | None] = txt(nullable=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    extracted_field_id: Mapped[uuid.UUID | None] = sr()
    document_page_id: Mapped[uuid.UUID | None] = sr()
    source_document_id: Mapped[uuid.UUID | None] = sr()
    target_column: Mapped[str | None] = txt(nullable=True)
    contribution: Mapped[Any] = measure()
    action_name: Mapped[str | None] = txt(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    document_action_id: Mapped[uuid.UUID | None] = sr(index=False)
    row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AuditLog(LogModel):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_target", "target_table", "target_id"),
        {"schema": S},
    )

    occurred_at: Mapped[datetime] = mapped_column(
        TS, nullable=False, server_default=text("now()"), index=True
    )
    actor_type: Mapped[str] = mapped_column(ACTOR_TYPE, nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = sr()
    on_behalf_of: Mapped[uuid.UUID | None] = sr()
    actor_role: Mapped[str | None] = mapped_column(ROLE_CODE, nullable=True)
    action: Mapped[str] = txt()
    target_schema: Mapped[str | None] = txt(nullable=True)
    target_table: Mapped[str | None] = txt(nullable=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()
    before: Mapped[Any] = mapped_column(JSONB, nullable=True)
    after: Mapped[Any] = mapped_column(JSONB, nullable=True)
    why: Mapped[str | None] = txt(nullable=True)
    approval_request_id: Mapped[uuid.UUID | None] = fk(f"{S}.approval_requests.id", nullable=True)
    agent_profile_code: Mapped[str | None] = txt(nullable=True)
    autonomy_level: Mapped[str | None] = mapped_column(AUTONOMY_LEVEL, nullable=True)
    confidence: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=True)
    metadata_: Mapped[Any] = mapped_column("metadata", JSONB, nullable=True)


class Notification(LogModel):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_id_read_at", "recipient_id", "read_at"),
        Index("ix_notifications_email_status_created_at", "email_status", "created_at"),
        {"schema": S},
    )

    # M1.2 (05 §2.4, R-DEC-33): LogModel has no TenantMixin → own column (like outbox_events);
    # EP-NTF filters tenant + recipient explicitly.
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
        server_default=text(f"'{DEFAULT_TENANT_ID}'"),
    )  # fmt: skip
    email_status: Mapped[str] = mapped_column(
        EMAIL_STATUS, nullable=False, server_default=text("'NOT_REQUIRED'")
    )
    email_sent_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    email_attempts: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )

    recipient_id: Mapped[uuid.UUID] = sr(nullable=False, index=False)
    kind: Mapped[str] = mapped_column(NOTIFICATION_KIND, nullable=False)
    title: Mapped[str] = txt()
    body: Mapped[str] = txt()
    link: Mapped[str | None] = txt(nullable=True)
    ref_schema: Mapped[str | None] = txt(nullable=True)
    ref_table: Mapped[str | None] = txt(nullable=True)
    ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class NotificationPreference(ConfigModel, TenantMixin):
    """ENT-NotificationPreference (05 §2.4, R-DEC-32) — no row = code default."""

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", name="uq_notification_preferences_user_id_kind"),
        {"schema": S},
    )

    user_id: Mapped[uuid.UUID] = sr(nullable=False)
    kind: Mapped[str] = mapped_column(NOTIFICATION_KIND, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)


class OutboxEvent(LogModel):
    """05 §5.1 — `id` = envelope `event_id`."""

    __tablename__ = "outbox_events"
    __table_args__ = (
        Index(
            "ix_outbox_events_pending",
            "status",
            "occurred_at",
            postgresql_where=text("status = 'PENDING'"),
        ),
        {"schema": S},
    )

    event_type: Mapped[str] = txt()
    version: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    aggregate_schema: Mapped[str] = txt()
    aggregate_table: Mapped[str] = txt()
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # R-DEC-21 / 05 §2.3: LogModel has no TenantMixin → own column; relay copies it into the
    # envelope. Not filtered by the session guard (system table read by relay across tenants).
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        server_default=text(f"'{DEFAULT_TENANT_ID}'"),
    )
    status: Mapped[str] = mapped_column(
        OUTBOX_STATUS, nullable=False, server_default=text("'PENDING'")
    )
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    published_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    last_error: Mapped[str | None] = txt(nullable=True)


class ProcessedEvent(LogModel):
    __tablename__ = "processed_events"
    __table_args__ = (
        Index("uq_processed_events_event_id_consumer", "event_id", "consumer", unique=True),
        {"schema": S},
    )

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    consumer: Mapped[str] = txt()
    processed_at: Mapped[datetime] = mapped_column(TS, nullable=False, server_default=text("now()"))
    status: Mapped[str] = mapped_column(PROCESSING_STATUS, nullable=False)
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    last_error: Mapped[str | None] = txt(nullable=True)


class AuditLogImmutableError(RuntimeError):
    """ORM-level guard: `platform.audit_logs` is append-only (05, 10 §1.8)."""


@event.listens_for(AuditLog, "before_update")
def _audit_no_update(_mapper: Any, _conn: Any, target: AuditLog) -> None:
    raise AuditLogImmutableError(f"audit log {target.id} is append-only (UPDATE blocked)")


@event.listens_for(AuditLog, "before_delete")
def _audit_no_delete(_mapper: Any, _conn: Any, target: AuditLog) -> None:
    raise AuditLogImmutableError(f"audit log {target.id} is append-only (DELETE blocked)")


@event.listens_for(Session, "do_orm_execute")
def _audit_no_bulk(state: ORMExecuteState) -> None:
    """Block `update(AuditLog)` / `delete(AuditLog)` statements executed through the ORM."""
    if not (state.is_update or state.is_delete):
        return
    mapper = state.bind_mapper
    if mapper is not None and mapper.class_ is AuditLog:
        raise AuditLogImmutableError("platform.audit_logs is append-only (bulk UPDATE/DELETE)")

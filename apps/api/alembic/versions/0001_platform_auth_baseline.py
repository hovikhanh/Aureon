"""platform and auth baseline

Revision ID: 0001_platform_auth_baseline
Revises:
Create Date: 2026-10-21 08:13:06.457642+00:00

Every migration must be reversible (05 §12.1 G3): implement both upgrade() and downgrade().
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_platform_auth_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Frozen snapshot of the shared enums at this revision (05 §6). Later enum changes need a new
# migration; never edit this list in place.
EXTENSIONS = ("pgcrypto", "vector", "pg_trgm", "citext")
# All 10 module schemas are created here because shared enums live in `auth` and `ai`
# (auth.role_code, ai.autonomy_level are referenced by platform tables). 05 §12.1 G2.
SCHEMAS = (
    "platform",
    "auth",
    "hr",
    "finance",
    "sales",
    "product",
    "risk",
    "execution",
    "idp",
    "ai",
)
SHARED_ENUMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "platform",
        "pillar",
        (
            "F",
            "O",
            "C",
            "U",
            "S",
        ),
    ),
    (
        "platform",
        "actor_type",
        (
            "USER",
            "AI",
            "SYSTEM",
        ),
    ),
    (
        "platform",
        "confidence_band",
        (
            "HIGH",
            "MEDIUM",
            "LOW",
        ),
    ),
    (
        "platform",
        "period_type",
        (
            "MONTH",
            "QUARTER",
            "YEAR",
            "ROLLING_12M",
        ),
    ),
    (
        "platform",
        "metric_unit",
        (
            "VND",
            "PERCENT",
            "DAYS",
            "MONTHS",
            "RATIO",
            "COUNT",
            "SCORE",
            "INDEX",
            "VND_PER_PERSON",
        ),
    ),
    (
        "platform",
        "threshold_direction",
        (
            "LOWER_IS_BAD",
            "HIGHER_IS_BAD",
        ),
    ),
    (
        "platform",
        "metric_value_kind",
        (
            "ACTUAL",
            "TARGET",
            "FORECAST",
        ),
    ),
    (
        "platform",
        "scope_type",
        (
            "company",
            "department",
            "product",
        ),
    ),
    (
        "platform",
        "value_origin",
        (
            "COMPUTED",
            "EXTRACTED",
            "MANUAL",
            "SEED",
        ),
    ),
    (
        "platform",
        "threshold_status",
        (
            "GREEN",
            "YELLOW",
            "RED",
        ),
    ),
    (
        "platform",
        "alert_severity",
        (
            "WARNING",
            "CRITICAL",
        ),
    ),
    (
        "platform",
        "alert_status",
        (
            "OPEN",
            "ACKNOWLEDGED",
            "RESOLVED",
            "DISMISSED",
        ),
    ),
    (
        "platform",
        "lineage_kind",
        (
            "RECORD_FROM_FIELD",
            "METRIC_FROM_RECORD",
            "METRIC_FROM_FIELD",
        ),
    ),
    (
        "platform",
        "notification_kind",
        (
            "alert",
            "review_assigned",
            "review_escalated",
            "task_assigned",
            "approval_requested",
            "approval_decided",
            "report_ready",
            "ai_action",
            "document_ready",
            "reminder",
            "system",
        ),
    ),
    (
        "platform",
        "record_source",
        (
            "MANUAL",
            "IDP",
            "IMPORT",
            "AI",
            "EVENT",
            "SEED",
        ),
    ),
    (
        "platform",
        "data_classification",
        (
            "PUBLIC",
            "INTERNAL",
            "CONFIDENTIAL",
            "SECRET",
        ),
    ),
    (
        "platform",
        "approval_status",
        (
            "PENDING",
            "APPROVED",
            "REJECTED",
            "CANCELLED",
            "EXPIRED",
        ),
    ),
    (
        "platform",
        "report_kind",
        (
            "WEEKLY",
            "MONTHLY",
        ),
    ),
    (
        "platform",
        "report_format",
        (
            "PDF",
            "XLSX",
        ),
    ),
    (
        "platform",
        "report_status",
        (
            "QUEUED",
            "GENERATING",
            "READY",
            "FAILED",
        ),
    ),
    (
        "platform",
        "outbox_status",
        (
            "PENDING",
            "PUBLISHED",
            "FAILED",
        ),
    ),
    (
        "platform",
        "processing_status",
        (
            "DONE",
            "DLQ",
        ),
    ),
    (
        "auth",
        "role_code",
        (
            "CEO",
            "CFO",
            "VP_SALES",
            "HR_MANAGER",
            "REVIEWER",
            "CPO",
            "RISK_MANAGER",
            "MANAGER",
            "EMPLOYEE",
            "ADMIN",
        ),
    ),
    (
        "ai",
        "autonomy_level",
        (
            "L0",
            "L1",
            "L2",
            "L3",
        ),
    ),
)


def _create_foundation() -> None:
    for ext in EXTENSIONS:
        op.execute(f"CREATE EXTENSION IF NOT EXISTS {ext}")
    for schema in SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    for schema, name, values in SHARED_ENUMS:
        postgresql.ENUM(*values, name=name, schema=schema).create(op.get_bind())


def _drop_foundation() -> None:
    for schema, name, values in reversed(SHARED_ENUMS):
        postgresql.ENUM(*values, name=name, schema=schema).drop(op.get_bind())
    # `platform` keeps Alembic's version table, so it is left in place; extensions are shared
    # with the cluster and pre-date this revision, so they are not dropped either.
    for schema in reversed(SCHEMAS):
        if schema != "platform":
            op.execute(f"DROP SCHEMA IF EXISTS {schema} RESTRICT")


AUDIT_IMMUTABLE_FN = """
CREATE FUNCTION platform.audit_logs_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'platform.audit_logs is append-only (% blocked)', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$
"""
AUDIT_IMMUTABLE_TRIGGER = """
CREATE TRIGGER trg_audit_logs_immutable
BEFORE UPDATE OR DELETE ON platform.audit_logs
FOR EACH ROW EXECUTE FUNCTION platform.audit_logs_immutable()
"""


def upgrade() -> None:
    _create_foundation()
    op.create_table(
        "roles",
        sa.Column(
            "code",
            postgresql.ENUM(
                "CEO",
                "CFO",
                "VP_SALES",
                "HR_MANAGER",
                "REVIEWER",
                "CPO",
                "RISK_MANAGER",
                "MANAGER",
                "EMPLOYEE",
                "ADMIN",
                name="role_code",
                create_type=False,
                schema="auth",
            ),
            nullable=False,
        ),
        sa.Column("role_ref", sa.Text(), nullable=False),
        sa.Column("name_vi", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=False),
        sa.Column("permissions", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("scope_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "pillars",
            sa.ARRAY(
                postgresql.ENUM(
                    "F", "O", "C", "U", "S", name="pillar", create_type=False, schema="platform"
                )
            ),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "data_classification",
            postgresql.ENUM(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "SECRET",
                name="data_classification",
                create_type=False,
                schema="platform",
            ),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("code", name=op.f("uq_roles_code")),
        sa.UniqueConstraint("role_ref", name=op.f("uq_roles_role_ref")),
        schema="auth",
    )
    op.create_table(
        "approval_rules",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("target_kind", sa.Text(), nullable=False),
        sa.Column("condition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "approver_role_codes",
            sa.ARRAY(
                postgresql.ENUM(
                    "CEO",
                    "CFO",
                    "VP_SALES",
                    "HR_MANAGER",
                    "REVIEWER",
                    "CPO",
                    "RISK_MANAGER",
                    "MANAGER",
                    "EMPLOYEE",
                    "ADMIN",
                    name="role_code",
                    create_type=False,
                    schema="auth",
                )
            ),
            nullable=False,
        ),
        sa.Column(
            "second_approver_role_codes",
            sa.ARRAY(
                postgresql.ENUM(
                    "CEO",
                    "CFO",
                    "VP_SALES",
                    "HR_MANAGER",
                    "REVIEWER",
                    "CPO",
                    "RISK_MANAGER",
                    "MANAGER",
                    "EMPLOYEE",
                    "ADMIN",
                    name="role_code",
                    create_type=False,
                    schema="auth",
                )
            ),
            nullable=True,
        ),
        sa.Column("sla_hours", sa.Integer(), server_default=sa.text("8"), nullable=False),
        sa.Column(
            "escalate_to_role_code",
            postgresql.ENUM(
                "CEO",
                "CFO",
                "VP_SALES",
                "HR_MANAGER",
                "REVIEWER",
                "CPO",
                "RISK_MANAGER",
                "MANAGER",
                "EMPLOYEE",
                "ADMIN",
                name="role_code",
                create_type=False,
                schema="auth",
            ),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("priority", sa.SmallInteger(), server_default=sa.text("100"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "data_classification",
            postgresql.ENUM(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "SECRET",
                name="data_classification",
                create_type=False,
                schema="platform",
            ),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.CheckConstraint("sla_hours > 0", name=op.f("ck_approval_rules_sla_hours_positive")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_rules")),
        sa.UniqueConstraint("code", name=op.f("uq_approval_rules_code")),
        schema="platform",
    )
    op.create_table(
        "metrics",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("alert_code", sa.Text(), nullable=False),
        sa.Column(
            "pillar",
            postgresql.ENUM(
                "F", "O", "C", "U", "S", name="pillar", create_type=False, schema="platform"
            ),
            nullable=True,
        ),
        sa.Column("name_vi", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=False),
        sa.Column(
            "unit",
            postgresql.ENUM(
                "VND",
                "PERCENT",
                "DAYS",
                "MONTHS",
                "RATIO",
                "COUNT",
                "SCORE",
                "INDEX",
                "VND_PER_PERSON",
                name="metric_unit",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column(
            "direction",
            postgresql.ENUM(
                "LOWER_IS_BAD",
                "HIGHER_IS_BAD",
                name="threshold_direction",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column("warning_threshold", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("critical_threshold", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("source_module", sa.Text(), nullable=False),
        sa.Column("formula_ref", sa.Text(), nullable=False),
        sa.Column("refresh_events", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "data_classification",
            postgresql.ENUM(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "SECRET",
                name="data_classification",
                create_type=False,
                schema="platform",
            ),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_metrics")),
        sa.UniqueConstraint("alert_code", name=op.f("uq_metrics_alert_code")),
        sa.UniqueConstraint("code", name=op.f("uq_metrics_code")),
        schema="platform",
    )
    op.create_table(
        "notifications",
        sa.Column("recipient_id", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(
                "alert",
                "review_assigned",
                "review_escalated",
                "task_assigned",
                "approval_requested",
                "approval_decided",
                "report_ready",
                "ai_action",
                "document_ready",
                "reminder",
                "system",
                name="notification_kind",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("ref_schema", sa.Text(), nullable=True),
        sa.Column("ref_table", sa.Text(), nullable=True),
        sa.Column("ref_id", sa.UUID(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
        schema="platform",
    )
    op.create_index(
        "ix_notifications_recipient_id_read_at",
        "notifications",
        ["recipient_id", "read_at"],
        unique=False,
        schema="platform",
    )
    op.create_table(
        "outbox_events",
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("version", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("aggregate_schema", sa.Text(), nullable=False),
        sa.Column("aggregate_table", sa.Text(), nullable=False),
        sa.Column("aggregate_id", sa.UUID(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "PUBLISHED",
                "FAILED",
                name="outbox_status",
                create_type=False,
                schema="platform",
            ),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("attempts", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
        schema="platform",
    )
    op.create_index(
        "ix_outbox_events_pending",
        "outbox_events",
        ["status", "occurred_at"],
        unique=False,
        schema="platform",
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.create_table(
        "processed_events",
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("consumer", sa.Text(), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "DONE", "DLQ", name="processing_status", create_type=False, schema="platform"
            ),
            nullable=False,
        ),
        sa.Column("attempts", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_processed_events")),
        schema="platform",
    )
    op.create_index(
        "uq_processed_events_event_id_consumer",
        "processed_events",
        ["event_id", "consumer"],
        unique=True,
        schema="platform",
    )
    op.create_table(
        "reports",
        sa.Column(
            "kind",
            postgresql.ENUM(
                "WEEKLY", "MONTHLY", name="report_kind", create_type=False, schema="platform"
            ),
            nullable=False,
        ),
        sa.Column("period_key", sa.Text(), nullable=False),
        sa.Column(
            "scope_type",
            postgresql.ENUM(
                "company",
                "department",
                "product",
                name="scope_type",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column("scope_id", sa.UUID(), nullable=True),
        sa.Column(
            "format",
            postgresql.ENUM(
                "PDF", "XLSX", name="report_format", create_type=False, schema="platform"
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "QUEUED",
                "GENERATING",
                "READY",
                "FAILED",
                name="report_status",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.UUID(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metric_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_summary_insight_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "source",
            postgresql.ENUM(
                "MANUAL",
                "IDP",
                "IMPORT",
                "AI",
                "EVENT",
                "SEED",
                name="record_source",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column(
            "data_classification",
            postgresql.ENUM(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "SECRET",
                name="data_classification",
                create_type=False,
                schema="platform",
            ),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
        schema="platform",
    )
    op.create_index(
        op.f("ix_reports_ai_summary_insight_id"),
        "reports",
        ["ai_summary_insight_id"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        op.f("ix_reports_requested_by"),
        "reports",
        ["requested_by"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        "uq_reports_period_scope_format",
        "reports",
        [
            "kind",
            "period_key",
            "scope_type",
            sa.literal_column("COALESCE(scope_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
            "format",
        ],
        unique=True,
        schema="platform",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "system_settings",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_secret", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("updated_reason", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "data_classification",
            postgresql.ENUM(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "SECRET",
                name="data_classification",
                create_type=False,
                schema="platform",
            ),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.CheckConstraint("is_secret = false", name=op.f("ck_system_settings_no_secrets_in_db")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_system_settings")),
        sa.UniqueConstraint("key", name=op.f("uq_system_settings_key")),
        schema="platform",
    )
    op.create_table(
        "users",
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("employee_id", sa.UUID(), nullable=True),
        sa.Column("locale", sa.Text(), server_default=sa.text("'vi'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "is_service_account", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "failed_login_count", sa.SmallInteger(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "data_classification",
            postgresql.ENUM(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "SECRET",
                name="data_classification",
                create_type=False,
                schema="platform",
            ),
            server_default="CONFIDENTIAL",
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("locale IN ('vi', 'en')", name=op.f("ck_users_locale_vi_en")),
        sa.ForeignKeyConstraint(
            ["role_id"], ["auth.roles.id"], name=op.f("fk_users_role_id_roles"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        schema="auth",
    )
    op.create_index(
        op.f("ix_users_department_id"), "users", ["department_id"], unique=False, schema="auth"
    )
    op.create_index(
        op.f("ix_users_employee_id"), "users", ["employee_id"], unique=True, schema="auth"
    )
    op.create_index(op.f("ix_users_role_id"), "users", ["role_id"], unique=False, schema="auth")
    op.create_table(
        "approval_requests",
        sa.Column("rule_id", sa.UUID(), nullable=False),
        sa.Column("target_schema", sa.Text(), nullable=True),
        sa.Column("target_table", sa.Text(), nullable=True),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column("ai_action_id", sa.UUID(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column("requested_by", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "APPROVED",
                "REJECTED",
                "CANCELLED",
                "EXPIRED",
                name="approval_status",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column("step", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("first_decided_by", sa.UUID(), nullable=True),
        sa.Column("first_decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("second_decided_by", sa.UUID(), nullable=True),
        sa.Column("second_decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "source",
            postgresql.ENUM(
                "MANUAL",
                "IDP",
                "IMPORT",
                "AI",
                "EVENT",
                "SEED",
                name="record_source",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column(
            "data_classification",
            postgresql.ENUM(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "SECRET",
                name="data_classification",
                create_type=False,
                schema="platform",
            ),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "second_decided_by IS NULL OR (second_decided_by <> first_decided_by AND second_decided_by <> requested_by)",
            name=op.f("ck_approval_requests_distinct_approvers"),
        ),
        sa.CheckConstraint("step IN (1, 2)", name=op.f("ck_approval_requests_step_1_or_2")),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["platform.approval_rules.id"],
            name=op.f("fk_approval_requests_rule_id_approval_rules"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_requests")),
        schema="platform",
    )
    op.create_index(
        op.f("ix_approval_requests_ai_action_id"),
        "approval_requests",
        ["ai_action_id"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        op.f("ix_approval_requests_first_decided_by"),
        "approval_requests",
        ["first_decided_by"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        op.f("ix_approval_requests_requested_by"),
        "approval_requests",
        ["requested_by"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        op.f("ix_approval_requests_rule_id"),
        "approval_requests",
        ["rule_id"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        op.f("ix_approval_requests_second_decided_by"),
        "approval_requests",
        ["second_decided_by"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        "ix_approval_requests_status_due_at",
        "approval_requests",
        ["status", "due_at"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        "ix_approval_requests_target",
        "approval_requests",
        ["target_table", "target_id"],
        unique=False,
        schema="platform",
    )
    op.create_table(
        "metric_values",
        sa.Column("metric_id", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(
                "ACTUAL",
                "TARGET",
                "FORECAST",
                name="metric_value_kind",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column(
            "period_type",
            postgresql.ENUM(
                "MONTH",
                "QUARTER",
                "YEAR",
                "ROLLING_12M",
                name="period_type",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column("period_key", sa.Text(), nullable=False),
        sa.Column(
            "scope_type",
            postgresql.ENUM(
                "company",
                "department",
                "product",
                name="scope_type",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column("scope_id", sa.UUID(), nullable=True),
        sa.Column("value", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column(
            "threshold_status",
            postgresql.ENUM(
                "GREEN",
                "YELLOW",
                "RED",
                name="threshold_status",
                create_type=False,
                schema="platform",
            ),
            nullable=True,
        ),
        sa.Column(
            "origin",
            postgresql.ENUM(
                "COMPUTED",
                "EXTRACTED",
                "MANUAL",
                "SEED",
                name="value_origin",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("data_quality_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "source",
            postgresql.ENUM(
                "MANUAL",
                "IDP",
                "IMPORT",
                "AI",
                "EVENT",
                "SEED",
                name="record_source",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column(
            "data_classification",
            postgresql.ENUM(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "SECRET",
                name="data_classification",
                create_type=False,
                schema="platform",
            ),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(
            ["metric_id"],
            ["platform.metrics.id"],
            name=op.f("fk_metric_values_metric_id_metrics"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_metric_values")),
        schema="platform",
    )
    op.create_index(
        op.f("ix_metric_values_metric_id"),
        "metric_values",
        ["metric_id"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        "ix_metric_values_metric_id_period_key",
        "metric_values",
        ["metric_id", "period_key"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        "uq_metric_values_current",
        "metric_values",
        [
            "metric_id",
            "kind",
            "period_key",
            "scope_type",
            sa.literal_column("COALESCE(scope_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
        ],
        unique=True,
        schema="platform",
        postgresql_where=sa.text("is_current"),
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("family_id", sa.UUID(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth.users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
        schema="auth",
    )
    op.create_index(
        op.f("ix_refresh_tokens_family_id"),
        "refresh_tokens",
        ["family_id"],
        unique=False,
        schema="auth",
    )
    op.create_index(
        op.f("ix_refresh_tokens_user_id"),
        "refresh_tokens",
        ["user_id"],
        unique=False,
        schema="auth",
    )
    op.create_table(
        "alerts",
        sa.Column("metric_id", sa.UUID(), nullable=False),
        sa.Column("metric_value_id", sa.UUID(), nullable=False),
        sa.Column(
            "severity",
            postgresql.ENUM(
                "WARNING", "CRITICAL", name="alert_severity", create_type=False, schema="platform"
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "OPEN",
                "ACKNOWLEDGED",
                "RESOLVED",
                "DISMISSED",
                name="alert_status",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column("period_key", sa.Text(), nullable=False),
        sa.Column("message_vi", sa.Text(), nullable=False),
        sa.Column("message_en", sa.Text(), nullable=False),
        sa.Column("raised_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_by", sa.UUID(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_by", sa.UUID(), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismiss_reason", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "source",
            postgresql.ENUM(
                "MANUAL",
                "IDP",
                "IMPORT",
                "AI",
                "EVENT",
                "SEED",
                name="record_source",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column(
            "data_classification",
            postgresql.ENUM(
                "PUBLIC",
                "INTERNAL",
                "CONFIDENTIAL",
                "SECRET",
                name="data_classification",
                create_type=False,
                schema="platform",
            ),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(
            ["metric_id"],
            ["platform.metrics.id"],
            name=op.f("fk_alerts_metric_id_metrics"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["metric_value_id"],
            ["platform.metric_values.id"],
            name=op.f("fk_alerts_metric_value_id_metric_values"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
        schema="platform",
    )
    op.create_index(
        op.f("ix_alerts_acknowledged_by"),
        "alerts",
        ["acknowledged_by"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        op.f("ix_alerts_dismissed_by"), "alerts", ["dismissed_by"], unique=False, schema="platform"
    )
    op.create_index(
        op.f("ix_alerts_metric_id"), "alerts", ["metric_id"], unique=False, schema="platform"
    )
    op.create_index(
        op.f("ix_alerts_metric_value_id"),
        "alerts",
        ["metric_value_id"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        "uq_alerts_open_per_period",
        "alerts",
        ["metric_id", "period_key"],
        unique=True,
        schema="platform",
        postgresql_where=sa.text("status IN ('OPEN','ACKNOWLEDGED') AND deleted_at IS NULL"),
    )
    op.create_table(
        "audit_logs",
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actor_type",
            postgresql.ENUM(
                "USER", "AI", "SYSTEM", name="actor_type", create_type=False, schema="platform"
            ),
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("on_behalf_of", sa.UUID(), nullable=True),
        sa.Column(
            "actor_role",
            postgresql.ENUM(
                "CEO",
                "CFO",
                "VP_SALES",
                "HR_MANAGER",
                "REVIEWER",
                "CPO",
                "RISK_MANAGER",
                "MANAGER",
                "EMPLOYEE",
                "ADMIN",
                name="role_code",
                create_type=False,
                schema="auth",
            ),
            nullable=True,
        ),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_schema", sa.Text(), nullable=True),
        sa.Column("target_table", sa.Text(), nullable=True),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column("source_document_id", sa.UUID(), nullable=True),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("why", sa.Text(), nullable=True),
        sa.Column("approval_request_id", sa.UUID(), nullable=True),
        sa.Column("agent_profile_code", sa.Text(), nullable=True),
        sa.Column(
            "autonomy_level",
            postgresql.ENUM(
                "L0", "L1", "L2", "L3", name="autonomy_level", create_type=False, schema="ai"
            ),
            nullable=True,
        ),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["approval_request_id"],
            ["platform.approval_requests.id"],
            name=op.f("fk_audit_logs_approval_request_id_approval_requests"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
        schema="platform",
    )
    op.create_index(
        op.f("ix_audit_logs_actor_user_id"),
        "audit_logs",
        ["actor_user_id"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        op.f("ix_audit_logs_approval_request_id"),
        "audit_logs",
        ["approval_request_id"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        op.f("ix_audit_logs_occurred_at"),
        "audit_logs",
        ["occurred_at"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        op.f("ix_audit_logs_on_behalf_of"),
        "audit_logs",
        ["on_behalf_of"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        op.f("ix_audit_logs_source_document_id"),
        "audit_logs",
        ["source_document_id"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        "ix_audit_logs_target",
        "audit_logs",
        ["target_table", "target_id"],
        unique=False,
        schema="platform",
    )
    op.create_table(
        "data_lineage",
        sa.Column(
            "link_kind",
            postgresql.ENUM(
                "RECORD_FROM_FIELD",
                "METRIC_FROM_RECORD",
                "METRIC_FROM_FIELD",
                name="lineage_kind",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column("metric_value_id", sa.UUID(), nullable=True),
        sa.Column("target_schema", sa.Text(), nullable=True),
        sa.Column("target_table", sa.Text(), nullable=True),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column("extracted_field_id", sa.UUID(), nullable=True),
        sa.Column("document_page_id", sa.UUID(), nullable=True),
        sa.Column("source_document_id", sa.UUID(), nullable=True),
        sa.Column("target_column", sa.Text(), nullable=True),
        sa.Column("contribution", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("action_name", sa.Text(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["metric_value_id"],
            ["platform.metric_values.id"],
            name=op.f("fk_data_lineage_metric_value_id_metric_values"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_lineage")),
        schema="platform",
    )
    op.create_index(
        op.f("ix_data_lineage_document_page_id"),
        "data_lineage",
        ["document_page_id"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        op.f("ix_data_lineage_extracted_field_id"),
        "data_lineage",
        ["extracted_field_id"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        op.f("ix_data_lineage_metric_value_id"),
        "data_lineage",
        ["metric_value_id"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        op.f("ix_data_lineage_source_document_id"),
        "data_lineage",
        ["source_document_id"],
        unique=False,
        schema="platform",
    )
    op.create_index(
        "ix_data_lineage_target",
        "data_lineage",
        ["target_schema", "target_table", "target_id"],
        unique=False,
        schema="platform",
    )

    # 05 §4.10 ENT-AuditLog: append-only, trigger blocks UPDATE/DELETE.
    op.execute(AUDIT_IMMUTABLE_FN)
    op.execute(AUDIT_IMMUTABLE_TRIGGER)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON platform.audit_logs")
    op.execute("DROP FUNCTION IF EXISTS platform.audit_logs_immutable()")
    op.drop_index("ix_data_lineage_target", table_name="data_lineage", schema="platform")
    op.drop_index(
        op.f("ix_data_lineage_source_document_id"), table_name="data_lineage", schema="platform"
    )
    op.drop_index(
        op.f("ix_data_lineage_metric_value_id"), table_name="data_lineage", schema="platform"
    )
    op.drop_index(
        op.f("ix_data_lineage_extracted_field_id"), table_name="data_lineage", schema="platform"
    )
    op.drop_index(
        op.f("ix_data_lineage_document_page_id"), table_name="data_lineage", schema="platform"
    )
    op.drop_table("data_lineage", schema="platform")
    op.drop_index("ix_audit_logs_target", table_name="audit_logs", schema="platform")
    op.drop_index(
        op.f("ix_audit_logs_source_document_id"), table_name="audit_logs", schema="platform"
    )
    op.drop_index(op.f("ix_audit_logs_on_behalf_of"), table_name="audit_logs", schema="platform")
    op.drop_index(op.f("ix_audit_logs_occurred_at"), table_name="audit_logs", schema="platform")
    op.drop_index(
        op.f("ix_audit_logs_approval_request_id"), table_name="audit_logs", schema="platform"
    )
    op.drop_index(op.f("ix_audit_logs_actor_user_id"), table_name="audit_logs", schema="platform")
    op.drop_table("audit_logs", schema="platform")
    op.drop_index(
        "uq_alerts_open_per_period",
        table_name="alerts",
        schema="platform",
        postgresql_where=sa.text("status IN ('OPEN','ACKNOWLEDGED') AND deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_alerts_metric_value_id"), table_name="alerts", schema="platform")
    op.drop_index(op.f("ix_alerts_metric_id"), table_name="alerts", schema="platform")
    op.drop_index(op.f("ix_alerts_dismissed_by"), table_name="alerts", schema="platform")
    op.drop_index(op.f("ix_alerts_acknowledged_by"), table_name="alerts", schema="platform")
    op.drop_table("alerts", schema="platform")
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens", schema="auth")
    op.drop_index(op.f("ix_refresh_tokens_family_id"), table_name="refresh_tokens", schema="auth")
    op.drop_table("refresh_tokens", schema="auth")
    op.drop_index(
        "uq_metric_values_current",
        table_name="metric_values",
        schema="platform",
        postgresql_where=sa.text("is_current"),
    )
    op.drop_index(
        "ix_metric_values_metric_id_period_key", table_name="metric_values", schema="platform"
    )
    op.drop_index(op.f("ix_metric_values_metric_id"), table_name="metric_values", schema="platform")
    op.drop_table("metric_values", schema="platform")
    op.drop_index("ix_approval_requests_target", table_name="approval_requests", schema="platform")
    op.drop_index(
        "ix_approval_requests_status_due_at", table_name="approval_requests", schema="platform"
    )
    op.drop_index(
        op.f("ix_approval_requests_second_decided_by"),
        table_name="approval_requests",
        schema="platform",
    )
    op.drop_index(
        op.f("ix_approval_requests_rule_id"), table_name="approval_requests", schema="platform"
    )
    op.drop_index(
        op.f("ix_approval_requests_requested_by"), table_name="approval_requests", schema="platform"
    )
    op.drop_index(
        op.f("ix_approval_requests_first_decided_by"),
        table_name="approval_requests",
        schema="platform",
    )
    op.drop_index(
        op.f("ix_approval_requests_ai_action_id"), table_name="approval_requests", schema="platform"
    )
    op.drop_table("approval_requests", schema="platform")
    op.drop_index(op.f("ix_users_role_id"), table_name="users", schema="auth")
    op.drop_index(op.f("ix_users_employee_id"), table_name="users", schema="auth")
    op.drop_index(op.f("ix_users_department_id"), table_name="users", schema="auth")
    op.drop_table("users", schema="auth")
    op.drop_table("system_settings", schema="platform")
    op.drop_index(
        "uq_reports_period_scope_format",
        table_name="reports",
        schema="platform",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_reports_requested_by"), table_name="reports", schema="platform")
    op.drop_index(op.f("ix_reports_ai_summary_insight_id"), table_name="reports", schema="platform")
    op.drop_table("reports", schema="platform")
    op.drop_index(
        "uq_processed_events_event_id_consumer", table_name="processed_events", schema="platform"
    )
    op.drop_table("processed_events", schema="platform")
    op.drop_index(
        "ix_outbox_events_pending",
        table_name="outbox_events",
        schema="platform",
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.drop_table("outbox_events", schema="platform")
    op.drop_index(
        "ix_notifications_recipient_id_read_at", table_name="notifications", schema="platform"
    )
    op.drop_table("notifications", schema="platform")
    op.drop_table("metrics", schema="platform")
    op.drop_table("approval_rules", schema="platform")
    op.drop_table("roles", schema="auth")
    _drop_foundation()

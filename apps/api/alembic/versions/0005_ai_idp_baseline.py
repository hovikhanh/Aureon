"""ai and idp baseline

Revision ID: 0005_ai_idp_baseline
Revises: 0004_risk_execution_baseline
Create Date: 2026-10-21 08:22:53.461181+00:00

Every migration must be reversible (05 §12.1 G3): implement both upgrade() and downgrade().
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType[object]):
    """Frozen copy of the pgvector column type (05 §11) — migrations never import app code."""

    cache_ok = True

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def get_col_spec(self, **kw: object) -> str:
        return f"vector({self.dim})"


revision: str = "0005_ai_idp_baseline"
down_revision: str | Sequence[str] | None = "0004_risk_execution_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Frozen snapshot of module-owned enums at this revision (05 §6). Enum changes need a new
# migration; never edit this list in place.
MODULE_ENUMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "ai",
        "message_sender",
        (
            "user",
            "assistant",
            "system",
        ),
    ),
    (
        "ai",
        "tool_call_status",
        (
            "ok",
            "error",
            "forbidden",
            "timeout",
        ),
    ),
    (
        "ai",
        "feedback_rating",
        (
            "up",
            "down",
        ),
    ),
    (
        "ai",
        "insight_kind",
        (
            "anomaly",
            "trend",
            "risk",
            "recommendation",
            "briefing",
        ),
    ),
    (
        "ai",
        "insight_status",
        (
            "active",
            "dismissed",
            "expired",
        ),
    ),
    (
        "ai",
        "ai_action_status",
        (
            "proposed",
            "confirmed",
            "executed",
            "rejected",
            "undone",
            "failed",
        ),
    ),
    (
        "idp",
        "input_channel",
        (
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",
            "C7",
            "C8",
            "C9",
            "C10",
        ),
    ),
    (
        "idp",
        "document_kind",
        (
            "FILE",
            "MANUAL",
            "TRANSCRIPT",
        ),
    ),
    (
        "idp",
        "document_status",
        (
            "UPLOADED",
            "PREPROCESSING",
            "CLASSIFYING",
            "EXTRACTING",
            "VALIDATING",
            "NEEDS_REVIEW",
            "IN_REVIEW",
            "AUTO_APPROVED",
            "APPROVED",
            "COMMITTED",
            "REJECTED",
            "FAILED",
            "DUPLICATE",
            "ROLLED_BACK",
            "SPLIT",
            "SUPERSEDED",
        ),
    ),
    (
        "idp",
        "scan_status",
        (
            "PENDING",
            "CLEAN",
            "INFECTED",
            "SKIPPED",
        ),
    ),
    (
        "idp",
        "job_status",
        (
            "QUEUED",
            "RUNNING",
            "SUCCEEDED",
            "FAILED",
        ),
    ),
    (
        "idp",
        "routing_decision",
        (
            "STP",
            "REVIEW",
        ),
    ),
    (
        "idp",
        "field_value_type",
        (
            "date",
            "money",
            "percent",
            "tax_code",
            "phone",
            "text",
            "person_name",
            "org_name",
            "enum",
            "period",
            "number",
            "checkbox",
            "signature_present",
            "stamp_present",
        ),
    ),
    (
        "idp",
        "assignment_kind",
        (
            "ASSIGN",
            "REASSIGN",
            "ESCALATE",
        ),
    ),
    (
        "idp",
        "review_decision",
        (
            "APPROVED",
            "REJECTED",
            "ABANDONED",
        ),
    ),
    (
        "idp",
        "schema_status",
        (
            "draft",
            "published",
            "retired",
        ),
    ),
    (
        "idp",
        "rule_kind",
        (
            "field",
            "cross_field",
            "cross_document",
            "master_data",
        ),
    ),
    (
        "idp",
        "rule_severity",
        (
            "warn",
            "fail",
            "blocking",
        ),
    ),
    (
        "idp",
        "batch_kind",
        (
            "multi_upload",
            "excel_import",
            "onboarding",
        ),
    ),
    (
        "idp",
        "batch_status",
        (
            "open",
            "processing",
            "completed",
            "partially_failed",
        ),
    ),
)


def upgrade() -> None:
    for schema, name, values in MODULE_ENUMS:
        postgresql.ENUM(*values, name=name, schema=schema).create(op.get_bind())
    op.create_table(
        "agent_profiles",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name_vi", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=False),
        sa.Column("allowed_tools", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column(
            "max_autonomy_level",
            postgresql.ENUM(
                "L0", "L1", "L2", "L3", name="autonomy_level", create_type=False, schema="ai"
            ),
            nullable=False,
        ),
        sa.Column("model_task", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("monthly_budget_usd", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_profiles")),
        sa.UniqueConstraint("code", name=op.f("uq_agent_profiles_code")),
        schema="ai",
    )
    op.create_table(
        "autonomy_policies",
        sa.Column("action_name", sa.Text(), nullable=False),
        sa.Column(
            "role_code",
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
        sa.Column("max_amount", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.CHAR(length=3), nullable=True),
        sa.Column(
            "level",
            postgresql.ENUM(
                "L0", "L1", "L2", "L3", name="autonomy_level", create_type=False, schema="ai"
            ),
            nullable=False,
        ),
        sa.Column(
            "max_level",
            postgresql.ENUM(
                "L0", "L1", "L2", "L3", name="autonomy_level", create_type=False, schema="ai"
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_autonomy_policies")),
        schema="ai",
    )
    op.create_index(
        "uq_autonomy_policies_action_role_amount",
        "autonomy_policies",
        ["action_name", "role_code", "max_amount"],
        unique=True,
        schema="ai",
        postgresql_nulls_not_distinct=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "conversations",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "role_code",
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
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
        schema="ai",
    )
    op.create_index(
        op.f("ix_conversations_user_id"), "conversations", ["user_id"], unique=False, schema="ai"
    )
    op.create_table(
        "insights",
        sa.Column(
            "kind",
            postgresql.ENUM(
                "anomaly",
                "trend",
                "risk",
                "recommendation",
                "briefing",
                name="insight_kind",
                create_type=False,
                schema="ai",
            ),
            nullable=False,
        ),
        sa.Column(
            "pillar",
            postgresql.ENUM(
                "F", "O", "C", "U", "S", name="pillar", create_type=False, schema="platform"
            ),
            nullable=True,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            postgresql.ENUM(
                "WARNING", "CRITICAL", name="alert_severity", create_type=False, schema="platform"
            ),
            nullable=True,
        ),
        sa.Column(
            "confidence",
            postgresql.ENUM(
                "HIGH",
                "MEDIUM",
                "LOW",
                name="confidence_band",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("structured", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("decision_id", sa.UUID(), nullable=True),
        sa.Column("trigger_event_id", sa.UUID(), nullable=True),
        sa.Column(
            "audience_roles",
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
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active",
                "dismissed",
                "expired",
                name="insight_status",
                create_type=False,
                schema="ai",
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_insights")),
        schema="ai",
    )
    op.create_index(
        op.f("ix_insights_decision_id"), "insights", ["decision_id"], unique=False, schema="ai"
    )
    op.create_table(
        "document_types",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name_vi", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=False),
        sa.Column(
            "pillars",
            sa.ARRAY(
                postgresql.ENUM(
                    "F", "O", "C", "U", "S", name="pillar", create_type=False, schema="platform"
                )
            ),
            nullable=False,
        ),
        sa.Column("current_schema_id", sa.UUID(), nullable=True),
        sa.Column("sensitivity_level", sa.SmallInteger(), nullable=False),
        sa.Column("retention_years", sa.SmallInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint(
            "sensitivity_level BETWEEN 1 AND 4",
            name=op.f("ck_document_types_sensitivity_level_1_4"),
        ),
        sa.ForeignKeyConstraint(
            ["current_schema_id"],
            ["idp.extraction_schemas.id"],
            name=op.f("fk_document_types_current_schema_id_extraction_schemas"),
            ondelete="RESTRICT",
            use_alter=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_types")),
        sa.UniqueConstraint("code", name=op.f("uq_document_types_code")),
        schema="idp",
    )
    op.create_index(
        op.f("ix_document_types_current_schema_id"),
        "document_types",
        ["current_schema_id"],
        unique=False,
        schema="idp",
    )
    op.create_table(
        "import_batches",
        sa.Column(
            "kind",
            postgresql.ENUM(
                "multi_upload",
                "excel_import",
                "onboarding",
                name="batch_kind",
                create_type=False,
                schema="idp",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("submitted_by", sa.UUID(), nullable=False),
        sa.Column("total_documents", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("completed_documents", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed_documents", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("column_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "open",
                "processing",
                "completed",
                "partially_failed",
                name="batch_status",
                create_type=False,
                schema="idp",
            ),
            nullable=False,
        ),
        sa.Column("quality_score", sa.Numeric(precision=5, scale=2), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_batches")),
        schema="idp",
    )
    op.create_index(
        op.f("ix_import_batches_submitted_by"),
        "import_batches",
        ["submitted_by"],
        unique=False,
        schema="idp",
    )
    op.create_table(
        "messages",
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column(
            "sender",
            postgresql.ENUM(
                "user", "assistant", "system", name="message_sender", create_type=False, schema="ai"
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("function_calls", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("truncated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
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
            ["conversation_id"],
            ["ai.conversations.id"],
            name=op.f("fk_messages_conversation_id_conversations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
        schema="ai",
    )
    op.create_index(
        op.f("ix_messages_conversation_id"),
        "messages",
        ["conversation_id"],
        unique=False,
        schema="ai",
    )
    op.create_table(
        "extraction_schemas",
        sa.Column("document_type_id", sa.UUID(), nullable=False),
        sa.Column("fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("thresholds", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("action_names", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "published",
                "retired",
                name="schema_status",
                create_type=False,
                schema="idp",
            ),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["document_type_id"],
            ["idp.document_types.id"],
            name=op.f("fk_extraction_schemas_document_type_id_document_types"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_extraction_schemas")),
        schema="idp",
    )
    op.create_index(
        op.f("ix_extraction_schemas_document_type_id"),
        "extraction_schemas",
        ["document_type_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        "uq_extraction_schemas_document_type_id_version",
        "extraction_schemas",
        ["document_type_id", "version"],
        unique=True,
        schema="idp",
    )
    op.create_table(
        "source_documents",
        sa.Column("import_batch_id", sa.UUID(), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("page_from", sa.Integer(), nullable=True),
        sa.Column("page_to", sa.Integer(), nullable=True),
        sa.Column(
            "channel",
            postgresql.ENUM(
                "C1",
                "C2",
                "C3",
                "C4",
                "C5",
                "C6",
                "C7",
                "C8",
                "C9",
                "C10",
                name="input_channel",
                create_type=False,
                schema="idp",
            ),
            nullable=False,
        ),
        sa.Column(
            "kind",
            postgresql.ENUM(
                "FILE",
                "MANUAL",
                "TRANSCRIPT",
                name="document_kind",
                create_type=False,
                schema="idp",
            ),
            nullable=False,
        ),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("sha256", sa.CHAR(length=64), nullable=True),
        sa.Column("duplicate_of_id", sa.UUID(), nullable=True),
        sa.Column("superseded_by_id", sa.UUID(), nullable=True),
        sa.Column(
            "scan_status",
            postgresql.ENUM(
                "PENDING",
                "CLEAN",
                "INFECTED",
                "SKIPPED",
                name="scan_status",
                create_type=False,
                schema="idp",
            ),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("manual_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("document_type_id", sa.UUID(), nullable=True),
        sa.Column("classification_confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "type_preselected", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "pillars",
            sa.ARRAY(
                postgresql.ENUM(
                    "F", "O", "C", "U", "S", name="pillar", create_type=False, schema="platform"
                )
            ),
            nullable=False,
        ),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "UPLOADED",
                "PREPROCESSING",
                "CLASSIFYING",
                "EXTRACTING",
                "VALIDATING",
                "NEEDS_REVIEW",
                "IN_REVIEW",
                "AUTO_APPROVED",
                "APPROVED",
                "COMMITTED",
                "REJECTED",
                "FAILED",
                "DUPLICATE",
                "ROLLED_BACK",
                "SPLIT",
                "SUPERSEDED",
                name="document_status",
                create_type=False,
                schema="idp",
            ),
            nullable=False,
        ),
        sa.Column("status_reason", sa.Text(), nullable=True),
        sa.Column("routing_reason", sa.Text(), nullable=True),
        sa.Column(
            "autonomy_level",
            postgresql.ENUM(
                "L0", "L1", "L2", "L3", name="autonomy_level", create_type=False, schema="ai"
            ),
            nullable=True,
        ),
        sa.Column("sensitivity_level", sa.SmallInteger(), nullable=False),
        sa.Column(
            "suspicious_content", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("submitted_by", sa.UUID(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_by", sa.UUID(), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("undo_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("retention_until", sa.Date(), nullable=True),
        sa.Column("embedding", Vector(1024), nullable=True),
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
            "page_count <= 300", name=op.f("ck_source_documents_page_count_max_300")
        ),
        sa.CheckConstraint("retry_count <= 3", name=op.f("ck_source_documents_retry_count_max_3")),
        sa.CheckConstraint(
            "sensitivity_level BETWEEN 1 AND 4",
            name=op.f("ck_source_documents_sensitivity_level_1_4"),
        ),
        sa.CheckConstraint(
            "size_bytes <= 52428800", name=op.f("ck_source_documents_size_max_50mb")
        ),
        sa.ForeignKeyConstraint(
            ["document_type_id"],
            ["idp.document_types.id"],
            name=op.f("fk_source_documents_document_type_id_document_types"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_of_id"],
            ["idp.source_documents.id"],
            name=op.f("fk_source_documents_duplicate_of_id_source_documents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["idp.import_batches.id"],
            name=op.f("fk_source_documents_import_batch_id_import_batches"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["idp.source_documents.id"],
            name=op.f("fk_source_documents_parent_id_source_documents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"],
            ["idp.source_documents.id"],
            name=op.f("fk_source_documents_superseded_by_id_source_documents"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_documents")),
        schema="idp",
    )
    op.create_index(
        op.f("ix_source_documents_department_id"),
        "source_documents",
        ["department_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        op.f("ix_source_documents_document_type_id"),
        "source_documents",
        ["document_type_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        op.f("ix_source_documents_duplicate_of_id"),
        "source_documents",
        ["duplicate_of_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        "ix_source_documents_embedding",
        "source_documents",
        ["embedding"],
        unique=False,
        schema="idp",
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        op.f("ix_source_documents_import_batch_id"),
        "source_documents",
        ["import_batch_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        op.f("ix_source_documents_locked_by"),
        "source_documents",
        ["locked_by"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        op.f("ix_source_documents_parent_id"),
        "source_documents",
        ["parent_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        "ix_source_documents_pillars",
        "source_documents",
        ["pillars"],
        unique=False,
        schema="idp",
        postgresql_using="gin",
    )
    op.create_index(
        op.f("ix_source_documents_sha256"),
        "source_documents",
        ["sha256"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        "ix_source_documents_status_submitted_at",
        "source_documents",
        ["status", "submitted_at"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        op.f("ix_source_documents_submitted_by"),
        "source_documents",
        ["submitted_by"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        op.f("ix_source_documents_superseded_by_id"),
        "source_documents",
        ["superseded_by_id"],
        unique=False,
        schema="idp",
    )
    op.create_table(
        "ai_actions",
        sa.Column("action_name", sa.Text(), nullable=False),
        sa.Column("tool_name", sa.Text(), nullable=True),
        sa.Column("agent_profile_code", sa.Text(), nullable=False),
        sa.Column(
            "autonomy_level",
            postgresql.ENUM(
                "L0", "L1", "L2", "L3", name="autonomy_level", create_type=False, schema="ai"
            ),
            nullable=False,
        ),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("why", sa.Text(), nullable=True),
        sa.Column("approval_request_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "proposed",
                "confirmed",
                "executed",
                "rejected",
                "undone",
                "failed",
                name="ai_action_status",
                create_type=False,
                schema="ai",
            ),
            nullable=False,
        ),
        sa.Column("on_behalf_of", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=True),
        sa.Column("insight_id", sa.UUID(), nullable=True),
        sa.Column("source_document_id", sa.UUID(), nullable=True),
        sa.Column("input", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("undo_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("undone_by", sa.UUID(), nullable=True),
        sa.Column("verification", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            ["insight_id"],
            ["ai.insights.id"],
            name=op.f("fk_ai_actions_insight_id_insights"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["ai.messages.id"],
            name=op.f("fk_ai_actions_message_id_messages"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_actions")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_ai_actions_idempotency_key")),
        schema="ai",
    )
    op.create_index(
        op.f("ix_ai_actions_approval_request_id"),
        "ai_actions",
        ["approval_request_id"],
        unique=False,
        schema="ai",
    )
    op.create_index(
        op.f("ix_ai_actions_insight_id"), "ai_actions", ["insight_id"], unique=False, schema="ai"
    )
    op.create_index(
        op.f("ix_ai_actions_message_id"), "ai_actions", ["message_id"], unique=False, schema="ai"
    )
    op.create_index(
        op.f("ix_ai_actions_on_behalf_of"),
        "ai_actions",
        ["on_behalf_of"],
        unique=False,
        schema="ai",
    )
    op.create_index(
        op.f("ix_ai_actions_source_document_id"),
        "ai_actions",
        ["source_document_id"],
        unique=False,
        schema="ai",
    )
    op.create_index(
        "ix_ai_actions_status_undo_deadline",
        "ai_actions",
        ["status", "undo_deadline"],
        unique=False,
        schema="ai",
    )
    op.create_index(
        op.f("ix_ai_actions_undone_by"), "ai_actions", ["undone_by"], unique=False, schema="ai"
    )
    op.create_table(
        "feedback",
        sa.Column("message_id", sa.UUID(), nullable=True),
        sa.Column("insight_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "rating",
            postgresql.ENUM("up", "down", name="feedback_rating", create_type=False, schema="ai"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "num_nonnulls(message_id, insight_id) >= 1", name=op.f("ck_feedback_has_target")
        ),
        sa.ForeignKeyConstraint(
            ["insight_id"],
            ["ai.insights.id"],
            name=op.f("fk_feedback_insight_id_insights"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["ai.messages.id"],
            name=op.f("fk_feedback_message_id_messages"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feedback")),
        schema="ai",
    )
    op.create_index(
        op.f("ix_feedback_insight_id"), "feedback", ["insight_id"], unique=False, schema="ai"
    )
    op.create_index(
        op.f("ix_feedback_message_id"), "feedback", ["message_id"], unique=False, schema="ai"
    )
    op.create_index(op.f("ix_feedback_user_id"), "feedback", ["user_id"], unique=False, schema="ai")
    op.create_table(
        "model_call_logs",
        sa.Column("caller_module", sa.Text(), nullable=False),
        sa.Column("task_kind", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("fallback_from", sa.Text(), nullable=True),
        sa.Column("message_id", sa.UUID(), nullable=True),
        sa.Column("source_document_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_micro_usd", sa.BigInteger(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "ok",
                "error",
                "forbidden",
                "timeout",
                name="tool_call_status",
                create_type=False,
                schema="ai",
            ),
            nullable=False,
        ),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("prompt_sha256", sa.CHAR(length=64), nullable=True),
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
            ["message_id"],
            ["ai.messages.id"],
            name=op.f("fk_model_call_logs_message_id_messages"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_call_logs")),
        schema="ai",
    )
    op.create_index(
        op.f("ix_model_call_logs_message_id"),
        "model_call_logs",
        ["message_id"],
        unique=False,
        schema="ai",
    )
    op.create_index(
        op.f("ix_model_call_logs_source_document_id"),
        "model_call_logs",
        ["source_document_id"],
        unique=False,
        schema="ai",
    )
    op.create_index(
        op.f("ix_model_call_logs_user_id"),
        "model_call_logs",
        ["user_id"],
        unique=False,
        schema="ai",
    )
    op.create_table(
        "tool_call_logs",
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("tool_name", sa.Text(), nullable=False),
        sa.Column("arguments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "ok",
                "error",
                "forbidden",
                "timeout",
                name="tool_call_status",
                create_type=False,
                schema="ai",
            ),
            nullable=False,
        ),
        sa.Column("http_status", sa.SmallInteger(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("agent_profile_code", sa.Text(), nullable=False),
        sa.Column(
            "autonomy_level",
            postgresql.ENUM(
                "L0", "L1", "L2", "L3", name="autonomy_level", create_type=False, schema="ai"
            ),
            nullable=True,
        ),
        sa.Column("why", sa.Text(), nullable=True),
        sa.Column("approval_request_id", sa.UUID(), nullable=True),
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
            ["message_id"],
            ["ai.messages.id"],
            name=op.f("fk_tool_call_logs_message_id_messages"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_call_logs")),
        schema="ai",
    )
    op.create_index(
        op.f("ix_tool_call_logs_approval_request_id"),
        "tool_call_logs",
        ["approval_request_id"],
        unique=False,
        schema="ai",
    )
    op.create_index(
        op.f("ix_tool_call_logs_message_id"),
        "tool_call_logs",
        ["message_id"],
        unique=False,
        schema="ai",
    )
    op.create_table(
        "document_pages",
        sa.Column("source_document_id", sa.UUID(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("sheet_name", sa.Text(), nullable=True),
        sa.Column("text_layer_exists", sa.Boolean(), nullable=False),
        sa.Column("text_layer_quality", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("ocr_used", sa.Boolean(), nullable=False),
        sa.Column("ocr_confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("image_storage_key", sa.Text(), nullable=True),
        sa.Column("width_px", sa.Integer(), nullable=True),
        sa.Column("height_px", sa.Integer(), nullable=True),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=True),
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
            ["source_document_id"],
            ["idp.source_documents.id"],
            name=op.f("fk_document_pages_source_document_id_source_documents"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_pages")),
        schema="idp",
    )
    op.create_index(
        "ix_document_pages_embedding",
        "document_pages",
        ["embedding"],
        unique=False,
        schema="idp",
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        op.f("ix_document_pages_source_document_id"),
        "document_pages",
        ["source_document_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        "uq_document_pages_source_document_id_page_number",
        "document_pages",
        ["source_document_id", "page_number"],
        unique=True,
        schema="idp",
    )
    op.create_table(
        "extraction_jobs",
        sa.Column("source_document_id", sa.UUID(), nullable=False),
        sa.Column("extraction_schema_id", sa.UUID(), nullable=False),
        sa.Column("attempt_no", sa.SmallInteger(), nullable=False),
        sa.Column("celery_task_id", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "QUEUED",
                "RUNNING",
                "SUCCEEDED",
                "FAILED",
                name="job_status",
                create_type=False,
                schema="idp",
            ),
            nullable=False,
        ),
        sa.Column("model_provider", sa.Text(), nullable=True),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column("document_confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "routing_decision",
            postgresql.ENUM(
                "STP", "REVIEW", name="routing_decision", create_type=False, schema="idp"
            ),
            nullable=True,
        ),
        sa.Column("routing_reasons", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("xd_results", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
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
            ["extraction_schema_id"],
            ["idp.extraction_schemas.id"],
            name=op.f("fk_extraction_jobs_extraction_schema_id_extraction_schemas"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["idp.source_documents.id"],
            name=op.f("fk_extraction_jobs_source_document_id_source_documents"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_extraction_jobs")),
        schema="idp",
    )
    op.create_index(
        op.f("ix_extraction_jobs_extraction_schema_id"),
        "extraction_jobs",
        ["extraction_schema_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        op.f("ix_extraction_jobs_source_document_id"),
        "extraction_jobs",
        ["source_document_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        "uq_extraction_jobs_source_document_id_attempt_no",
        "extraction_jobs",
        ["source_document_id", "attempt_no"],
        unique=True,
        schema="idp",
    )
    op.create_table(
        "review_assignments",
        sa.Column("source_document_id", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(
                "ASSIGN",
                "REASSIGN",
                "ESCALATE",
                name="assignment_kind",
                create_type=False,
                schema="idp",
            ),
            nullable=False,
        ),
        sa.Column("from_user_id", sa.UUID(), nullable=True),
        sa.Column("to_user_id", sa.UUID(), nullable=True),
        sa.Column(
            "to_role_code",
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
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            ["source_document_id"],
            ["idp.source_documents.id"],
            name=op.f("fk_review_assignments_source_document_id_source_documents"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_assignments")),
        schema="idp",
    )
    op.create_index(
        op.f("ix_review_assignments_from_user_id"),
        "review_assignments",
        ["from_user_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        op.f("ix_review_assignments_source_document_id"),
        "review_assignments",
        ["source_document_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        "ix_review_assignments_source_document_id_is_current",
        "review_assignments",
        ["source_document_id", "is_current"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        op.f("ix_review_assignments_to_user_id"),
        "review_assignments",
        ["to_user_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        "ix_review_assignments_to_user_id_due_at",
        "review_assignments",
        ["to_user_id", "due_at"],
        unique=False,
        schema="idp",
        postgresql_where=sa.text("is_current"),
    )
    op.create_index(
        "uq_review_assignments_current",
        "review_assignments",
        ["source_document_id"],
        unique=True,
        schema="idp",
        postgresql_where=sa.text("is_current"),
    )
    op.create_table(
        "validation_rules",
        sa.Column("extraction_schema_id", sa.UUID(), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(
                "field",
                "cross_field",
                "cross_document",
                "master_data",
                name="rule_kind",
                create_type=False,
                schema="idp",
            ),
            nullable=False,
        ),
        sa.Column("expression", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "severity",
            postgresql.ENUM(
                "warn", "fail", "blocking", name="rule_severity", create_type=False, schema="idp"
            ),
            nullable=False,
        ),
        sa.Column("tolerance", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["extraction_schema_id"],
            ["idp.extraction_schemas.id"],
            name=op.f("fk_validation_rules_extraction_schema_id_extraction_schemas"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_validation_rules")),
        schema="idp",
    )
    op.create_index(
        op.f("ix_validation_rules_extraction_schema_id"),
        "validation_rules",
        ["extraction_schema_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        "uq_validation_rules_schema_code",
        "validation_rules",
        [
            sa.literal_column(
                "COALESCE(extraction_schema_id, '00000000-0000-0000-0000-000000000000'::uuid)"
            ),
            "code",
        ],
        unique=True,
        schema="idp",
    )
    op.create_table(
        "extracted_fields",
        sa.Column("extraction_job_id", sa.UUID(), nullable=False),
        sa.Column("document_page_id", sa.UUID(), nullable=True),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=True),
        sa.Column(
            "value_type",
            postgresql.ENUM(
                "date",
                "money",
                "percent",
                "tax_code",
                "phone",
                "text",
                "person_name",
                "org_name",
                "enum",
                "period",
                "number",
                "checkbox",
                "signature_present",
                "stamp_present",
                name="field_value_type",
                create_type=False,
                schema="idp",
            ),
            nullable=False,
        ),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column(
            "confidence_band",
            postgresql.ENUM(
                "HIGH",
                "MEDIUM",
                "LOW",
                name="confidence_band",
                create_type=False,
                schema="platform",
            ),
            nullable=False,
        ),
        sa.Column("is_critical", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("sensitivity_level", sa.SmallInteger(), nullable=False),
        sa.Column("source_location", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("master_match", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("corrected_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("corrected_by", sa.UUID(), nullable=True),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correction_reason", sa.Text(), nullable=True),
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
            "sensitivity_level BETWEEN 1 AND 4",
            name=op.f("ck_extracted_fields_sensitivity_level_1_4"),
        ),
        sa.ForeignKeyConstraint(
            ["document_page_id"],
            ["idp.document_pages.id"],
            name=op.f("fk_extracted_fields_document_page_id_document_pages"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_job_id"],
            ["idp.extraction_jobs.id"],
            name=op.f("fk_extracted_fields_extraction_job_id_extraction_jobs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_extracted_fields")),
        schema="idp",
    )
    op.create_index(
        op.f("ix_extracted_fields_corrected_by"),
        "extracted_fields",
        ["corrected_by"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        op.f("ix_extracted_fields_document_page_id"),
        "extracted_fields",
        ["document_page_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        op.f("ix_extracted_fields_extraction_job_id"),
        "extracted_fields",
        ["extraction_job_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        "uq_extracted_fields_job_field_row",
        "extracted_fields",
        ["extraction_job_id", "field_name", "row_index"],
        unique=True,
        schema="idp",
        postgresql_nulls_not_distinct=True,
    )
    op.create_table(
        "extraction_reviews",
        sa.Column("source_document_id", sa.UUID(), nullable=False),
        sa.Column("extraction_job_id", sa.UUID(), nullable=False),
        sa.Column("reviewer_id", sa.UUID(), nullable=False),
        sa.Column(
            "reviewer_role",
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
        sa.Column(
            "decision",
            postgresql.ENUM(
                "APPROVED",
                "REJECTED",
                "ABANDONED",
                name="review_decision",
                create_type=False,
                schema="idp",
            ),
            nullable=True,
        ),
        sa.Column("reject_reason_code", sa.Text(), nullable=True),
        sa.Column("reject_note", sa.Text(), nullable=True),
        sa.Column("fields_total", sa.Integer(), nullable=False),
        sa.Column("fields_corrected", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
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
            ["extraction_job_id"],
            ["idp.extraction_jobs.id"],
            name=op.f("fk_extraction_reviews_extraction_job_id_extraction_jobs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["idp.source_documents.id"],
            name=op.f("fk_extraction_reviews_source_document_id_source_documents"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_extraction_reviews")),
        schema="idp",
    )
    op.create_index(
        op.f("ix_extraction_reviews_extraction_job_id"),
        "extraction_reviews",
        ["extraction_job_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        op.f("ix_extraction_reviews_reviewer_id"),
        "extraction_reviews",
        ["reviewer_id"],
        unique=False,
        schema="idp",
    )
    op.create_index(
        op.f("ix_extraction_reviews_source_document_id"),
        "extraction_reviews",
        ["source_document_id"],
        unique=False,
        schema="idp",
    )
    # Cyclic FKs (use_alter) — added after both tables exist.
    op.create_foreign_key(
        "fk_document_types_current_schema_id_extraction_schemas",
        "document_types",
        "extraction_schemas",
        ["current_schema_id"],
        ["id"],
        source_schema="idp",
        referent_schema="idp",
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # Cyclic FKs first, so the tables can be dropped.
    op.drop_constraint(
        "fk_document_types_current_schema_id_extraction_schemas",
        "document_types",
        schema="idp",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_extraction_reviews_source_document_id"),
        table_name="extraction_reviews",
        schema="idp",
    )
    op.drop_index(
        op.f("ix_extraction_reviews_reviewer_id"), table_name="extraction_reviews", schema="idp"
    )
    op.drop_index(
        op.f("ix_extraction_reviews_extraction_job_id"),
        table_name="extraction_reviews",
        schema="idp",
    )
    op.drop_table("extraction_reviews", schema="idp")
    op.drop_index(
        "uq_extracted_fields_job_field_row",
        table_name="extracted_fields",
        schema="idp",
        postgresql_nulls_not_distinct=True,
    )
    op.drop_index(
        op.f("ix_extracted_fields_extraction_job_id"), table_name="extracted_fields", schema="idp"
    )
    op.drop_index(
        op.f("ix_extracted_fields_document_page_id"), table_name="extracted_fields", schema="idp"
    )
    op.drop_index(
        op.f("ix_extracted_fields_corrected_by"), table_name="extracted_fields", schema="idp"
    )
    op.drop_table("extracted_fields", schema="idp")
    op.drop_index("uq_validation_rules_schema_code", table_name="validation_rules", schema="idp")
    op.drop_index(
        op.f("ix_validation_rules_extraction_schema_id"),
        table_name="validation_rules",
        schema="idp",
    )
    op.drop_table("validation_rules", schema="idp")
    op.drop_index(
        "uq_review_assignments_current",
        table_name="review_assignments",
        schema="idp",
        postgresql_where=sa.text("is_current"),
    )
    op.drop_index(
        "ix_review_assignments_to_user_id_due_at",
        table_name="review_assignments",
        schema="idp",
        postgresql_where=sa.text("is_current"),
    )
    op.drop_index(
        op.f("ix_review_assignments_to_user_id"), table_name="review_assignments", schema="idp"
    )
    op.drop_index(
        "ix_review_assignments_source_document_id_is_current",
        table_name="review_assignments",
        schema="idp",
    )
    op.drop_index(
        op.f("ix_review_assignments_source_document_id"),
        table_name="review_assignments",
        schema="idp",
    )
    op.drop_index(
        op.f("ix_review_assignments_from_user_id"), table_name="review_assignments", schema="idp"
    )
    op.drop_table("review_assignments", schema="idp")
    op.drop_index(
        "uq_extraction_jobs_source_document_id_attempt_no",
        table_name="extraction_jobs",
        schema="idp",
    )
    op.drop_index(
        op.f("ix_extraction_jobs_source_document_id"), table_name="extraction_jobs", schema="idp"
    )
    op.drop_index(
        op.f("ix_extraction_jobs_extraction_schema_id"), table_name="extraction_jobs", schema="idp"
    )
    op.drop_table("extraction_jobs", schema="idp")
    op.drop_index(
        "uq_document_pages_source_document_id_page_number",
        table_name="document_pages",
        schema="idp",
    )
    op.drop_index(
        op.f("ix_document_pages_source_document_id"), table_name="document_pages", schema="idp"
    )
    op.drop_index(
        "ix_document_pages_embedding",
        table_name="document_pages",
        schema="idp",
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_table("document_pages", schema="idp")
    op.drop_index(op.f("ix_tool_call_logs_message_id"), table_name="tool_call_logs", schema="ai")
    op.drop_index(
        op.f("ix_tool_call_logs_approval_request_id"), table_name="tool_call_logs", schema="ai"
    )
    op.drop_table("tool_call_logs", schema="ai")
    op.drop_index(op.f("ix_model_call_logs_user_id"), table_name="model_call_logs", schema="ai")
    op.drop_index(
        op.f("ix_model_call_logs_source_document_id"), table_name="model_call_logs", schema="ai"
    )
    op.drop_index(op.f("ix_model_call_logs_message_id"), table_name="model_call_logs", schema="ai")
    op.drop_table("model_call_logs", schema="ai")
    op.drop_index(op.f("ix_feedback_user_id"), table_name="feedback", schema="ai")
    op.drop_index(op.f("ix_feedback_message_id"), table_name="feedback", schema="ai")
    op.drop_index(op.f("ix_feedback_insight_id"), table_name="feedback", schema="ai")
    op.drop_table("feedback", schema="ai")
    op.drop_index(op.f("ix_ai_actions_undone_by"), table_name="ai_actions", schema="ai")
    op.drop_index("ix_ai_actions_status_undo_deadline", table_name="ai_actions", schema="ai")
    op.drop_index(op.f("ix_ai_actions_source_document_id"), table_name="ai_actions", schema="ai")
    op.drop_index(op.f("ix_ai_actions_on_behalf_of"), table_name="ai_actions", schema="ai")
    op.drop_index(op.f("ix_ai_actions_message_id"), table_name="ai_actions", schema="ai")
    op.drop_index(op.f("ix_ai_actions_insight_id"), table_name="ai_actions", schema="ai")
    op.drop_index(op.f("ix_ai_actions_approval_request_id"), table_name="ai_actions", schema="ai")
    op.drop_table("ai_actions", schema="ai")
    op.drop_index(
        op.f("ix_source_documents_superseded_by_id"), table_name="source_documents", schema="idp"
    )
    op.drop_index(
        op.f("ix_source_documents_submitted_by"), table_name="source_documents", schema="idp"
    )
    op.drop_index(
        "ix_source_documents_status_submitted_at", table_name="source_documents", schema="idp"
    )
    op.drop_index(op.f("ix_source_documents_sha256"), table_name="source_documents", schema="idp")
    op.drop_index(
        "ix_source_documents_pillars",
        table_name="source_documents",
        schema="idp",
        postgresql_using="gin",
    )
    op.drop_index(
        op.f("ix_source_documents_parent_id"), table_name="source_documents", schema="idp"
    )
    op.drop_index(
        op.f("ix_source_documents_locked_by"), table_name="source_documents", schema="idp"
    )
    op.drop_index(
        op.f("ix_source_documents_import_batch_id"), table_name="source_documents", schema="idp"
    )
    op.drop_index(
        "ix_source_documents_embedding",
        table_name="source_documents",
        schema="idp",
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_index(
        op.f("ix_source_documents_duplicate_of_id"), table_name="source_documents", schema="idp"
    )
    op.drop_index(
        op.f("ix_source_documents_document_type_id"), table_name="source_documents", schema="idp"
    )
    op.drop_index(
        op.f("ix_source_documents_department_id"), table_name="source_documents", schema="idp"
    )
    op.drop_table("source_documents", schema="idp")
    op.drop_index(
        "uq_extraction_schemas_document_type_id_version",
        table_name="extraction_schemas",
        schema="idp",
    )
    op.drop_index(
        op.f("ix_extraction_schemas_document_type_id"),
        table_name="extraction_schemas",
        schema="idp",
    )
    op.drop_table("extraction_schemas", schema="idp")
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages", schema="ai")
    op.drop_table("messages", schema="ai")
    op.drop_index(op.f("ix_import_batches_submitted_by"), table_name="import_batches", schema="idp")
    op.drop_table("import_batches", schema="idp")
    op.drop_index(
        op.f("ix_document_types_current_schema_id"), table_name="document_types", schema="idp"
    )
    op.drop_table("document_types", schema="idp")
    op.drop_index(op.f("ix_insights_decision_id"), table_name="insights", schema="ai")
    op.drop_table("insights", schema="ai")
    op.drop_index(op.f("ix_conversations_user_id"), table_name="conversations", schema="ai")
    op.drop_table("conversations", schema="ai")
    op.drop_index(
        "uq_autonomy_policies_action_role_amount",
        table_name="autonomy_policies",
        schema="ai",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("autonomy_policies", schema="ai")
    op.drop_table("agent_profiles", schema="ai")
    for schema, name, values in reversed(MODULE_ENUMS):
        postgresql.ENUM(*values, name=name, schema=schema).drop(op.get_bind())

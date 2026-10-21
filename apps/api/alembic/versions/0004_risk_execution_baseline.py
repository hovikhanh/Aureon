"""risk and execution baseline

Revision ID: 0004_risk_execution_baseline
Revises: 0003_hr_product_baseline
Create Date: 2026-10-21 08:22:32.732746+00:00

Every migration must be reversible (05 §12.1 G3): implement both upgrade() and downgrade().
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_risk_execution_baseline"
down_revision: str | Sequence[str] | None = "0003_hr_product_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Frozen snapshot of module-owned enums at this revision (05 §6). Enum changes need a new
# migration; never edit this list in place.
MODULE_ENUMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "risk",
        "risk_category",
        (
            "financial",
            "operational",
            "strategic",
            "people",
            "business",
            "customer",
            "product",
            "technology",
            "security",
            "compliance",
            "legal",
            "partner_supplier",
            "ai",
        ),
    ),
    (
        "risk",
        "risk_severity",
        (
            "low",
            "medium",
            "high",
            "critical",
        ),
    ),
    (
        "risk",
        "risk_status",
        (
            "proposed",
            "identified",
            "assessed",
            "mitigating",
            "monitoring",
            "accepted",
            "closed",
            "rejected",
        ),
    ),
    (
        "risk",
        "risk_source",
        (
            "manual",
            "event",
            "ai",
            "document",
        ),
    ),
    (
        "risk",
        "mitigation_status",
        (
            "planned",
            "in_progress",
            "done",
            "cancelled",
        ),
    ),
    (
        "execution",
        "decision_status",
        (
            "open",
            "in_progress",
            "done",
            "cancelled",
        ),
    ),
    (
        "execution",
        "task_status",
        (
            "backlog",
            "todo",
            "in_progress",
            "blocked",
            "in_review",
            "done",
            "cancelled",
        ),
    ),
    (
        "execution",
        "task_priority",
        (
            "low",
            "medium",
            "high",
            "urgent",
        ),
    ),
    (
        "execution",
        "task_source",
        (
            "manual",
            "meeting",
            "ai",
            "document",
            "mitigation",
        ),
    ),
    (
        "execution",
        "project_status",
        (
            "planned",
            "active",
            "on_hold",
            "done",
            "cancelled",
        ),
    ),
    (
        "execution",
        "objective_level",
        (
            "company",
            "department",
            "team",
            "individual",
        ),
    ),
    (
        "execution",
        "okr_status",
        (
            "draft",
            "active",
            "closed",
        ),
    ),
    (
        "execution",
        "okr_type",
        (
            "committed",
            "aspirational",
        ),
    ),
    (
        "execution",
        "kpi_direction",
        (
            "HIGHER_IS_BETTER",
            "LOWER_IS_BETTER",
            "WITHIN_RANGE",
            "BINARY",
        ),
    ),
    (
        "execution",
        "kpi_value_type",
        (
            "ratio",
            "percentage",
            "numeric",
            "currency",
            "duration",
            "count",
        ),
    ),
    (
        "execution",
        "kpi_data_source",
        (
            "manual",
            "document",
            "automated",
            "ai_assisted",
        ),
    ),
    (
        "execution",
        "kpi_band",
        (
            "CRITICAL",
            "BELOW",
            "NEAR",
            "MEETS",
            "EXCEEDS",
        ),
    ),
    (
        "execution",
        "initiative_status",
        (
            "planned",
            "active",
            "at_risk",
            "done",
            "cancelled",
        ),
    ),
    (
        "execution",
        "milestone_status",
        (
            "planned",
            "done",
            "missed",
        ),
    ),
    (
        "execution",
        "transcript_status",
        (
            "UPLOADED",
            "PROCESSED",
            "FAILED",
        ),
    ),
)


def upgrade() -> None:
    for schema, name, values in MODULE_ENUMS:
        postgresql.ENUM(*values, name=name, schema=schema).create(op.get_bind())
    op.create_table(
        "meetings",
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("held_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("chair_id", sa.UUID(), nullable=True),
        sa.Column("attendee_ids", sa.ARRAY(sa.UUID()), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_document_id", sa.UUID(), nullable=True),
        sa.Column("transcript_id", sa.UUID(), nullable=True),
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
            ["transcript_id"],
            ["execution.meeting_transcripts.id"],
            name=op.f("fk_meetings_transcript_id_meeting_transcripts"),
            ondelete="RESTRICT",
            use_alter=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meetings")),
        schema="execution",
    )
    op.create_index(
        "ix_meetings_attendee_ids",
        "meetings",
        ["attendee_ids"],
        unique=False,
        schema="execution",
        postgresql_using="gin",
    )
    op.create_index(
        op.f("ix_meetings_chair_id"), "meetings", ["chair_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_meetings_department_id"),
        "meetings",
        ["department_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_meetings_source_document_id"),
        "meetings",
        ["source_document_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_meetings_transcript_id"),
        "meetings",
        ["transcript_id"],
        unique=False,
        schema="execution",
    )
    op.create_table(
        "objectives",
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("period_key", sa.Text(), nullable=False),
        sa.Column(
            "level",
            postgresql.ENUM(
                "company",
                "department",
                "team",
                "individual",
                name="objective_level",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column(
            "okr_type",
            postgresql.ENUM(
                "committed", "aspirational", name="okr_type", create_type=False, schema="execution"
            ),
            nullable=False,
        ),
        sa.Column("weight_pct", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("team_id", sa.UUID(), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column(
            "pillar",
            postgresql.ENUM(
                "F", "O", "C", "U", "S", name="pillar", create_type=False, schema="platform"
            ),
            nullable=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "active",
                "closed",
                name="okr_status",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column("progress_pct", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("source_document_id", sa.UUID(), nullable=True),
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
        sa.CheckConstraint("score BETWEEN 0 AND 1", name=op.f("ck_objectives_score_0_1")),
        sa.CheckConstraint(
            "weight_pct BETWEEN 0 AND 100", name=op.f("ck_objectives_weight_pct_0_100")
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["execution.objectives.id"],
            name=op.f("fk_objectives_parent_id_objectives"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_objectives")),
        schema="execution",
    )
    op.create_index(
        op.f("ix_objectives_department_id"),
        "objectives",
        ["department_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_objectives_owner_id"), "objectives", ["owner_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_objectives_parent_id"),
        "objectives",
        ["parent_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_objectives_source_document_id"),
        "objectives",
        ["source_document_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_objectives_team_id"), "objectives", ["team_id"], unique=False, schema="execution"
    )
    op.create_table(
        "projects",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("planned_end_date", sa.Date(), nullable=True),
        sa.Column("actual_end_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "planned",
                "active",
                "on_hold",
                "done",
                "cancelled",
                name="project_status",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column("budget_amount", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("code", name=op.f("uq_projects_code")),
        schema="execution",
    )
    op.create_index(
        op.f("ix_projects_department_id"),
        "projects",
        ["department_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_projects_owner_id"), "projects", ["owner_id"], unique=False, schema="execution"
    )
    op.create_table(
        "risks",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "category",
            postgresql.ENUM(
                "financial",
                "operational",
                "strategic",
                "people",
                "business",
                "customer",
                "product",
                "technology",
                "security",
                "compliance",
                "legal",
                "partner_supplier",
                "ai",
                name="risk_category",
                create_type=False,
                schema="risk",
            ),
            nullable=False,
        ),
        sa.Column("likelihood", sa.SmallInteger(), nullable=False),
        sa.Column("impact", sa.SmallInteger(), nullable=False),
        sa.Column(
            "risk_score",
            sa.SmallInteger(),
            sa.Computed("likelihood * impact", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "severity",
            postgresql.ENUM(
                "low",
                "medium",
                "high",
                "critical",
                name="risk_severity",
                create_type=False,
                schema="risk",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "proposed",
                "identified",
                "assessed",
                "mitigating",
                "monitoring",
                "accepted",
                "closed",
                "rejected",
                name="risk_status",
                create_type=False,
                schema="risk",
            ),
            nullable=False,
        ),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.UUID(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "risk_source",
            postgresql.ENUM(
                "manual",
                "event",
                "ai",
                "document",
                name="risk_source",
                create_type=False,
                schema="risk",
            ),
            nullable=False,
        ),
        sa.Column("source_event_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("linked_entities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("review_date", sa.Date(), nullable=True),
        sa.Column("accepted_by", sa.UUID(), nullable=True),
        sa.Column("accepted_reason", sa.Text(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("identified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_document_id", sa.UUID(), nullable=True),
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
        sa.CheckConstraint("impact BETWEEN 1 AND 5", name=op.f("ck_risks_impact_1_5")),
        sa.CheckConstraint("likelihood BETWEEN 1 AND 5", name=op.f("ck_risks_likelihood_1_5")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risks")),
        sa.UniqueConstraint("code", name=op.f("uq_risks_code")),
        schema="risk",
    )
    op.create_index(
        op.f("ix_risks_accepted_by"), "risks", ["accepted_by"], unique=False, schema="risk"
    )
    op.create_index(
        op.f("ix_risks_confirmed_by"), "risks", ["confirmed_by"], unique=False, schema="risk"
    )
    op.create_index(
        op.f("ix_risks_department_id"), "risks", ["department_id"], unique=False, schema="risk"
    )
    op.create_index(
        "ix_risks_linked_entities",
        "risks",
        ["linked_entities"],
        unique=False,
        schema="risk",
        postgresql_using="gin",
    )
    op.create_index(op.f("ix_risks_owner_id"), "risks", ["owner_id"], unique=False, schema="risk")
    op.create_index(
        op.f("ix_risks_source_document_id"),
        "risks",
        ["source_document_id"],
        unique=False,
        schema="risk",
    )
    op.create_index(
        "ix_risks_status_severity", "risks", ["status", "severity"], unique=False, schema="risk"
    )
    op.create_index(
        "uq_risks_source_event_id",
        "risks",
        ["source_event_id"],
        unique=True,
        schema="risk",
        postgresql_where=sa.text("source_event_id IS NOT NULL"),
    )
    op.create_table(
        "scenarios",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("risk_ids", sa.ARRAY(sa.UUID()), nullable=False),
        sa.Column("horizon_months", sa.SmallInteger(), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("impact_domains", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenarios")),
        schema="risk",
    )
    op.create_index(
        "ix_scenarios_risk_ids",
        "scenarios",
        ["risk_ids"],
        unique=False,
        schema="risk",
        postgresql_using="gin",
    )
    op.create_table(
        "initiatives",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objective_id", sa.UUID(), nullable=False),
        sa.Column(
            "pillar",
            postgresql.ENUM(
                "F", "O", "C", "U", "S", name="pillar", create_type=False, schema="platform"
            ),
            nullable=True,
        ),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("planned_end_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "planned",
                "active",
                "at_risk",
                "done",
                "cancelled",
                name="initiative_status",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column("progress_pct", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("weight_pct", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("budget_amount", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
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
            "weight_pct BETWEEN 0 AND 100", name=op.f("ck_initiatives_weight_pct_0_100")
        ),
        sa.ForeignKeyConstraint(
            ["objective_id"],
            ["execution.objectives.id"],
            name=op.f("fk_initiatives_objective_id_objectives"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_initiatives")),
        sa.UniqueConstraint("code", name=op.f("uq_initiatives_code")),
        schema="execution",
    )
    op.create_index(
        op.f("ix_initiatives_department_id"),
        "initiatives",
        ["department_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_initiatives_objective_id"),
        "initiatives",
        ["objective_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_initiatives_owner_id"),
        "initiatives",
        ["owner_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        "ix_initiatives_status_planned_end_date",
        "initiatives",
        ["status", "planned_end_date"],
        unique=False,
        schema="execution",
    )
    op.create_table(
        "key_results",
        sa.Column("objective_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("metric_code", sa.Text(), nullable=True),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column("baseline", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("target", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("current_value", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "active",
                "closed",
                name="okr_status",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
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
            nullable=True,
        ),
        sa.Column("weight_pct", sa.Numeric(precision=7, scale=4), nullable=False),
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
            "weight_pct BETWEEN 0 AND 100", name=op.f("ck_key_results_weight_pct_0_100")
        ),
        sa.ForeignKeyConstraint(
            ["objective_id"],
            ["execution.objectives.id"],
            name=op.f("fk_key_results_objective_id_objectives"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_key_results")),
        schema="execution",
    )
    op.create_index(
        op.f("ix_key_results_objective_id"),
        "key_results",
        ["objective_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_key_results_owner_id"),
        "key_results",
        ["owner_id"],
        unique=False,
        schema="execution",
    )
    op.create_table(
        "meeting_transcripts",
        sa.Column("meeting_id", sa.UUID(), nullable=True),
        sa.Column("source_document_id", sa.UUID(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("speaker_count", sa.SmallInteger(), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "UPLOADED",
                "PROCESSED",
                "FAILED",
                name="transcript_status",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column("consent_confirmed_by", sa.UUID(), nullable=False),
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
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "language IN ('vi', 'en')", name=op.f("ck_meeting_transcripts_language_vi_en")
        ),
        sa.ForeignKeyConstraint(
            ["meeting_id"],
            ["execution.meetings.id"],
            name=op.f("fk_meeting_transcripts_meeting_id_meetings"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meeting_transcripts")),
        schema="execution",
    )
    op.create_index(
        op.f("ix_meeting_transcripts_consent_confirmed_by"),
        "meeting_transcripts",
        ["consent_confirmed_by"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_meeting_transcripts_meeting_id"),
        "meeting_transcripts",
        ["meeting_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_meeting_transcripts_source_document_id"),
        "meeting_transcripts",
        ["source_document_id"],
        unique=False,
        schema="execution",
    )
    op.create_table(
        "mitigations",
        sa.Column("risk_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "planned",
                "in_progress",
                "done",
                "cancelled",
                name="mitigation_status",
                create_type=False,
                schema="risk",
            ),
            nullable=False,
        ),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("progress_pct", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("task_id", sa.UUID(), nullable=True),
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
            "progress_pct BETWEEN 0 AND 100", name=op.f("ck_mitigations_progress_pct_0_100")
        ),
        sa.ForeignKeyConstraint(
            ["risk_id"],
            ["risk.risks.id"],
            name=op.f("fk_mitigations_risk_id_risks"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mitigations")),
        schema="risk",
    )
    op.create_index(
        op.f("ix_mitigations_owner_id"), "mitigations", ["owner_id"], unique=False, schema="risk"
    )
    op.create_index(
        op.f("ix_mitigations_risk_id"), "mitigations", ["risk_id"], unique=False, schema="risk"
    )
    op.create_index(
        op.f("ix_mitigations_task_id"), "mitigations", ["task_id"], unique=False, schema="risk"
    )
    op.create_table(
        "risk_assessments",
        sa.Column("risk_id", sa.UUID(), nullable=False),
        sa.Column("likelihood", sa.SmallInteger(), nullable=False),
        sa.Column("impact", sa.SmallInteger(), nullable=False),
        sa.Column("risk_score", sa.SmallInteger(), nullable=False),
        sa.Column(
            "severity",
            postgresql.ENUM(
                "low",
                "medium",
                "high",
                "critical",
                name="risk_severity",
                create_type=False,
                schema="risk",
            ),
            nullable=False,
        ),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assessed_by", sa.UUID(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
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
            ["risk_id"],
            ["risk.risks.id"],
            name=op.f("fk_risk_assessments_risk_id_risks"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_assessments")),
        schema="risk",
    )
    op.create_index(
        op.f("ix_risk_assessments_assessed_by"),
        "risk_assessments",
        ["assessed_by"],
        unique=False,
        schema="risk",
    )
    op.create_index(
        op.f("ix_risk_assessments_risk_id"),
        "risk_assessments",
        ["risk_id"],
        unique=False,
        schema="risk",
    )
    op.create_table(
        "decisions",
        sa.Column("meeting_id", sa.UUID(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("alternatives_rejected", sa.Text(), nullable=True),
        sa.Column("expected_outcome", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("review_at", sa.ARRAY(sa.Date()), nullable=False),
        sa.Column("actual_outcome", sa.Text(), nullable=True),
        sa.Column("outcome_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("initiative_id", sa.UUID(), nullable=True),
        sa.Column("source_insight_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "open",
                "in_progress",
                "done",
                "cancelled",
                name="decision_status",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_document_id", sa.UUID(), nullable=True),
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
            ["initiative_id"],
            ["execution.initiatives.id"],
            name=op.f("fk_decisions_initiative_id_initiatives"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["meeting_id"],
            ["execution.meetings.id"],
            name=op.f("fk_decisions_meeting_id_meetings"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_decisions")),
        schema="execution",
    )
    op.create_index(
        op.f("ix_decisions_initiative_id"),
        "decisions",
        ["initiative_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_decisions_meeting_id"),
        "decisions",
        ["meeting_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_decisions_owner_id"), "decisions", ["owner_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_decisions_source_document_id"),
        "decisions",
        ["source_document_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_decisions_source_insight_id"),
        "decisions",
        ["source_insight_id"],
        unique=False,
        schema="execution",
    )
    op.create_table(
        "kpis",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("metric_code", sa.Text(), nullable=True),
        sa.Column("key_result_id", sa.UUID(), nullable=True),
        sa.Column("unit", sa.Text(), nullable=False),
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
        sa.Column("target_value", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column(
            "direction",
            postgresql.ENUM(
                "HIGHER_IS_BETTER",
                "LOWER_IS_BETTER",
                "WITHIN_RANGE",
                "BINARY",
                name="kpi_direction",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column(
            "value_type",
            postgresql.ENUM(
                "ratio",
                "percentage",
                "numeric",
                "currency",
                "duration",
                "count",
                name="kpi_value_type",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column(
            "data_source_kind",
            postgresql.ENUM(
                "manual",
                "document",
                "automated",
                "ai_assisted",
                name="kpi_data_source",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column("parent_kpi_id", sa.UUID(), nullable=True),
        sa.Column("weight_pct", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("initiative_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "active",
                "closed",
                name="okr_status",
                create_type=False,
                schema="execution",
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
        sa.CheckConstraint("weight_pct BETWEEN 0 AND 100", name=op.f("ck_kpis_weight_pct_0_100")),
        sa.ForeignKeyConstraint(
            ["initiative_id"],
            ["execution.initiatives.id"],
            name=op.f("fk_kpis_initiative_id_initiatives"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["key_result_id"],
            ["execution.key_results.id"],
            name=op.f("fk_kpis_key_result_id_key_results"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_kpi_id"],
            ["execution.kpis.id"],
            name=op.f("fk_kpis_parent_kpi_id_kpis"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kpis")),
        sa.UniqueConstraint("code", name=op.f("uq_kpis_code")),
        schema="execution",
    )
    op.create_index(
        op.f("ix_kpis_department_id"), "kpis", ["department_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_kpis_initiative_id"), "kpis", ["initiative_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_kpis_key_result_id"), "kpis", ["key_result_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_kpis_owner_id"), "kpis", ["owner_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_kpis_parent_kpi_id"), "kpis", ["parent_kpi_id"], unique=False, schema="execution"
    )
    op.create_table(
        "milestones",
        sa.Column("initiative_id", sa.UUID(), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "planned",
                "done",
                "missed",
                name="milestone_status",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
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
            "num_nonnulls(initiative_id, project_id) = 1", name=op.f("ck_milestones_one_parent")
        ),
        sa.ForeignKeyConstraint(
            ["initiative_id"],
            ["execution.initiatives.id"],
            name=op.f("fk_milestones_initiative_id_initiatives"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["execution.projects.id"],
            name=op.f("fk_milestones_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_milestones")),
        schema="execution",
    )
    op.create_index(
        op.f("ix_milestones_initiative_id"),
        "milestones",
        ["initiative_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_milestones_project_id"),
        "milestones",
        ["project_id"],
        unique=False,
        schema="execution",
    )
    op.create_table(
        "check_ins",
        sa.Column("key_result_id", sa.UUID(), nullable=True),
        sa.Column("kpi_id", sa.UUID(), nullable=True),
        sa.Column("value", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("blocker", sa.Text(), nullable=True),
        sa.Column("support_needed", sa.Text(), nullable=True),
        sa.Column("next_action", sa.Text(), nullable=True),
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
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
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
            "num_nonnulls(key_result_id, kpi_id) = 1", name=op.f("ck_check_ins_one_target")
        ),
        sa.ForeignKeyConstraint(
            ["key_result_id"],
            ["execution.key_results.id"],
            name=op.f("fk_check_ins_key_result_id_key_results"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["kpi_id"],
            ["execution.kpis.id"],
            name=op.f("fk_check_ins_kpi_id_kpis"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_check_ins")),
        schema="execution",
    )
    op.create_index(
        op.f("ix_check_ins_key_result_id"),
        "check_ins",
        ["key_result_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_check_ins_kpi_id"), "check_ins", ["kpi_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_check_ins_user_id"), "check_ins", ["user_id"], unique=False, schema="execution"
    )
    op.create_table(
        "kpi_targets",
        sa.Column("kpi_id", sa.UUID(), nullable=False),
        sa.Column("period_key", sa.Text(), nullable=False),
        sa.Column("baseline", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("minimum", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("target", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("stretch", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column(
            "band_thresholds",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default='{"CRITICAL":0,"BELOW":70,"NEAR":90,"MEETS":100,"EXCEEDS":110}',
            nullable=False,
        ),
        sa.Column(
            "score_cap_pct",
            sa.Numeric(precision=7, scale=4),
            server_default=sa.text("150"),
            nullable=False,
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
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
            ["kpi_id"],
            ["execution.kpis.id"],
            name=op.f("fk_kpi_targets_kpi_id_kpis"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kpi_targets")),
        schema="execution",
    )
    op.create_index(
        op.f("ix_kpi_targets_kpi_id"), "kpi_targets", ["kpi_id"], unique=False, schema="execution"
    )
    op.create_index(
        "uq_kpi_targets_kpi_id_period_key",
        "kpi_targets",
        ["kpi_id", "period_key"],
        unique=True,
        schema="execution",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "tasks",
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("assignee_id", sa.UUID(), nullable=True),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("meeting_id", sa.UUID(), nullable=True),
        sa.Column("decision_id", sa.UUID(), nullable=True),
        sa.Column("key_result_id", sa.UUID(), nullable=True),
        sa.Column("initiative_id", sa.UUID(), nullable=True),
        sa.Column("milestone_id", sa.UUID(), nullable=True),
        sa.Column("kpi_id", sa.UUID(), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column(
            "priority",
            postgresql.ENUM(
                "low",
                "medium",
                "high",
                "urgent",
                name="task_priority",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "backlog",
                "todo",
                "in_progress",
                "blocked",
                "in_review",
                "done",
                "cancelled",
                name="task_status",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimate_hours", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("actual_hours", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_critical", sa.Boolean(), nullable=False),
        sa.Column(
            "task_source",
            postgresql.ENUM(
                "manual",
                "meeting",
                "ai",
                "document",
                "mitigation",
                name="task_source",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column("overdue_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_document_id", sa.UUID(), nullable=True),
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
            ["decision_id"],
            ["execution.decisions.id"],
            name=op.f("fk_tasks_decision_id_decisions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["initiative_id"],
            ["execution.initiatives.id"],
            name=op.f("fk_tasks_initiative_id_initiatives"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["key_result_id"],
            ["execution.key_results.id"],
            name=op.f("fk_tasks_key_result_id_key_results"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["kpi_id"],
            ["execution.kpis.id"],
            name=op.f("fk_tasks_kpi_id_kpis"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["meeting_id"],
            ["execution.meetings.id"],
            name=op.f("fk_tasks_meeting_id_meetings"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["milestone_id"],
            ["execution.milestones.id"],
            name=op.f("fk_tasks_milestone_id_milestones"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["execution.tasks.id"],
            name=op.f("fk_tasks_parent_id_tasks"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["execution.projects.id"],
            name=op.f("fk_tasks_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
        schema="execution",
    )
    op.create_index(
        op.f("ix_tasks_assignee_id"), "tasks", ["assignee_id"], unique=False, schema="execution"
    )
    op.create_index(
        "ix_tasks_assignee_id_status_due_date",
        "tasks",
        ["assignee_id", "status", "due_date"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_tasks_decision_id"), "tasks", ["decision_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_tasks_department_id"), "tasks", ["department_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_tasks_initiative_id"), "tasks", ["initiative_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_tasks_key_result_id"), "tasks", ["key_result_id"], unique=False, schema="execution"
    )
    op.create_index(op.f("ix_tasks_kpi_id"), "tasks", ["kpi_id"], unique=False, schema="execution")
    op.create_index(
        op.f("ix_tasks_meeting_id"), "tasks", ["meeting_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_tasks_milestone_id"), "tasks", ["milestone_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_tasks_owner_id"), "tasks", ["owner_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_tasks_parent_id"), "tasks", ["parent_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_tasks_project_id"), "tasks", ["project_id"], unique=False, schema="execution"
    )
    op.create_index(
        op.f("ix_tasks_source_document_id"),
        "tasks",
        ["source_document_id"],
        unique=False,
        schema="execution",
    )
    op.create_table(
        "kpi_measurements",
        sa.Column("kpi_id", sa.UUID(), nullable=False),
        sa.Column("period_key", sa.Text(), nullable=False),
        sa.Column("actual_value", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("achievement_pct", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column(
            "evaluation_band",
            postgresql.ENUM(
                "CRITICAL",
                "BELOW",
                "NEAR",
                "MEETS",
                "EXCEEDS",
                name="kpi_band",
                create_type=False,
                schema="execution",
            ),
            nullable=False,
        ),
        sa.Column("kpi_target_id", sa.UUID(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_document_id", sa.UUID(), nullable=True),
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
            ["kpi_id"],
            ["execution.kpis.id"],
            name=op.f("fk_kpi_measurements_kpi_id_kpis"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["kpi_target_id"],
            ["execution.kpi_targets.id"],
            name=op.f("fk_kpi_measurements_kpi_target_id_kpi_targets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kpi_measurements")),
        sa.UniqueConstraint("kpi_id", "period_key", name="uq_kpi_measurements_kpi_id_period_key"),
        schema="execution",
    )
    op.create_index(
        op.f("ix_kpi_measurements_kpi_id"),
        "kpi_measurements",
        ["kpi_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_kpi_measurements_kpi_target_id"),
        "kpi_measurements",
        ["kpi_target_id"],
        unique=False,
        schema="execution",
    )
    op.create_index(
        op.f("ix_kpi_measurements_source_document_id"),
        "kpi_measurements",
        ["source_document_id"],
        unique=False,
        schema="execution",
    )
    # Cyclic FKs (use_alter) — added after both tables exist.
    op.create_foreign_key(
        "fk_meetings_transcript_id_meeting_transcripts",
        "meetings",
        "meeting_transcripts",
        ["transcript_id"],
        ["id"],
        source_schema="execution",
        referent_schema="execution",
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # Cyclic FKs first, so the tables can be dropped.
    op.drop_constraint(
        "fk_meetings_transcript_id_meeting_transcripts",
        "meetings",
        schema="execution",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_kpi_measurements_source_document_id"),
        table_name="kpi_measurements",
        schema="execution",
    )
    op.drop_index(
        op.f("ix_kpi_measurements_kpi_target_id"), table_name="kpi_measurements", schema="execution"
    )
    op.drop_index(
        op.f("ix_kpi_measurements_kpi_id"), table_name="kpi_measurements", schema="execution"
    )
    op.drop_table("kpi_measurements", schema="execution")
    op.drop_index(op.f("ix_tasks_source_document_id"), table_name="tasks", schema="execution")
    op.drop_index(op.f("ix_tasks_project_id"), table_name="tasks", schema="execution")
    op.drop_index(op.f("ix_tasks_parent_id"), table_name="tasks", schema="execution")
    op.drop_index(op.f("ix_tasks_owner_id"), table_name="tasks", schema="execution")
    op.drop_index(op.f("ix_tasks_milestone_id"), table_name="tasks", schema="execution")
    op.drop_index(op.f("ix_tasks_meeting_id"), table_name="tasks", schema="execution")
    op.drop_index(op.f("ix_tasks_kpi_id"), table_name="tasks", schema="execution")
    op.drop_index(op.f("ix_tasks_key_result_id"), table_name="tasks", schema="execution")
    op.drop_index(op.f("ix_tasks_initiative_id"), table_name="tasks", schema="execution")
    op.drop_index(op.f("ix_tasks_department_id"), table_name="tasks", schema="execution")
    op.drop_index(op.f("ix_tasks_decision_id"), table_name="tasks", schema="execution")
    op.drop_index("ix_tasks_assignee_id_status_due_date", table_name="tasks", schema="execution")
    op.drop_index(op.f("ix_tasks_assignee_id"), table_name="tasks", schema="execution")
    op.drop_table("tasks", schema="execution")
    op.drop_index(
        "uq_kpi_targets_kpi_id_period_key",
        table_name="kpi_targets",
        schema="execution",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_kpi_targets_kpi_id"), table_name="kpi_targets", schema="execution")
    op.drop_table("kpi_targets", schema="execution")
    op.drop_index(op.f("ix_check_ins_user_id"), table_name="check_ins", schema="execution")
    op.drop_index(op.f("ix_check_ins_kpi_id"), table_name="check_ins", schema="execution")
    op.drop_index(op.f("ix_check_ins_key_result_id"), table_name="check_ins", schema="execution")
    op.drop_table("check_ins", schema="execution")
    op.drop_index(op.f("ix_milestones_project_id"), table_name="milestones", schema="execution")
    op.drop_index(op.f("ix_milestones_initiative_id"), table_name="milestones", schema="execution")
    op.drop_table("milestones", schema="execution")
    op.drop_index(op.f("ix_kpis_parent_kpi_id"), table_name="kpis", schema="execution")
    op.drop_index(op.f("ix_kpis_owner_id"), table_name="kpis", schema="execution")
    op.drop_index(op.f("ix_kpis_key_result_id"), table_name="kpis", schema="execution")
    op.drop_index(op.f("ix_kpis_initiative_id"), table_name="kpis", schema="execution")
    op.drop_index(op.f("ix_kpis_department_id"), table_name="kpis", schema="execution")
    op.drop_table("kpis", schema="execution")
    op.drop_index(
        op.f("ix_decisions_source_insight_id"), table_name="decisions", schema="execution"
    )
    op.drop_index(
        op.f("ix_decisions_source_document_id"), table_name="decisions", schema="execution"
    )
    op.drop_index(op.f("ix_decisions_owner_id"), table_name="decisions", schema="execution")
    op.drop_index(op.f("ix_decisions_meeting_id"), table_name="decisions", schema="execution")
    op.drop_index(op.f("ix_decisions_initiative_id"), table_name="decisions", schema="execution")
    op.drop_table("decisions", schema="execution")
    op.drop_index(op.f("ix_risk_assessments_risk_id"), table_name="risk_assessments", schema="risk")
    op.drop_index(
        op.f("ix_risk_assessments_assessed_by"), table_name="risk_assessments", schema="risk"
    )
    op.drop_table("risk_assessments", schema="risk")
    op.drop_index(op.f("ix_mitigations_task_id"), table_name="mitigations", schema="risk")
    op.drop_index(op.f("ix_mitigations_risk_id"), table_name="mitigations", schema="risk")
    op.drop_index(op.f("ix_mitigations_owner_id"), table_name="mitigations", schema="risk")
    op.drop_table("mitigations", schema="risk")
    op.drop_index(
        op.f("ix_meeting_transcripts_source_document_id"),
        table_name="meeting_transcripts",
        schema="execution",
    )
    op.drop_index(
        op.f("ix_meeting_transcripts_meeting_id"),
        table_name="meeting_transcripts",
        schema="execution",
    )
    op.drop_index(
        op.f("ix_meeting_transcripts_consent_confirmed_by"),
        table_name="meeting_transcripts",
        schema="execution",
    )
    op.drop_table("meeting_transcripts", schema="execution")
    op.drop_index(op.f("ix_key_results_owner_id"), table_name="key_results", schema="execution")
    op.drop_index(op.f("ix_key_results_objective_id"), table_name="key_results", schema="execution")
    op.drop_table("key_results", schema="execution")
    op.drop_index(
        "ix_initiatives_status_planned_end_date", table_name="initiatives", schema="execution"
    )
    op.drop_index(op.f("ix_initiatives_owner_id"), table_name="initiatives", schema="execution")
    op.drop_index(op.f("ix_initiatives_objective_id"), table_name="initiatives", schema="execution")
    op.drop_index(
        op.f("ix_initiatives_department_id"), table_name="initiatives", schema="execution"
    )
    op.drop_table("initiatives", schema="execution")
    op.drop_index(
        "ix_scenarios_risk_ids", table_name="scenarios", schema="risk", postgresql_using="gin"
    )
    op.drop_table("scenarios", schema="risk")
    op.drop_index(
        "uq_risks_source_event_id",
        table_name="risks",
        schema="risk",
        postgresql_where=sa.text("source_event_id IS NOT NULL"),
    )
    op.drop_index("ix_risks_status_severity", table_name="risks", schema="risk")
    op.drop_index(op.f("ix_risks_source_document_id"), table_name="risks", schema="risk")
    op.drop_index(op.f("ix_risks_owner_id"), table_name="risks", schema="risk")
    op.drop_index(
        "ix_risks_linked_entities", table_name="risks", schema="risk", postgresql_using="gin"
    )
    op.drop_index(op.f("ix_risks_department_id"), table_name="risks", schema="risk")
    op.drop_index(op.f("ix_risks_confirmed_by"), table_name="risks", schema="risk")
    op.drop_index(op.f("ix_risks_accepted_by"), table_name="risks", schema="risk")
    op.drop_table("risks", schema="risk")
    op.drop_index(op.f("ix_projects_owner_id"), table_name="projects", schema="execution")
    op.drop_index(op.f("ix_projects_department_id"), table_name="projects", schema="execution")
    op.drop_table("projects", schema="execution")
    op.drop_index(op.f("ix_objectives_team_id"), table_name="objectives", schema="execution")
    op.drop_index(
        op.f("ix_objectives_source_document_id"), table_name="objectives", schema="execution"
    )
    op.drop_index(op.f("ix_objectives_parent_id"), table_name="objectives", schema="execution")
    op.drop_index(op.f("ix_objectives_owner_id"), table_name="objectives", schema="execution")
    op.drop_index(op.f("ix_objectives_department_id"), table_name="objectives", schema="execution")
    op.drop_table("objectives", schema="execution")
    op.drop_index(op.f("ix_meetings_transcript_id"), table_name="meetings", schema="execution")
    op.drop_index(op.f("ix_meetings_source_document_id"), table_name="meetings", schema="execution")
    op.drop_index(op.f("ix_meetings_department_id"), table_name="meetings", schema="execution")
    op.drop_index(op.f("ix_meetings_chair_id"), table_name="meetings", schema="execution")
    op.drop_index(
        "ix_meetings_attendee_ids",
        table_name="meetings",
        schema="execution",
        postgresql_using="gin",
    )
    op.drop_table("meetings", schema="execution")
    for schema, name, values in reversed(MODULE_ENUMS):
        postgresql.ENUM(*values, name=name, schema=schema).drop(op.get_bind())

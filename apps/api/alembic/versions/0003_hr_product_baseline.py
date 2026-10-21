"""hr and product baseline

Revision ID: 0003_hr_product_baseline
Revises: 0002_finance_sales_baseline
Create Date: 2026-10-21 08:21:52.240105+00:00

Every migration must be reversible (05 §12.1 G3): implement both upgrade() and downgrade().
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_hr_product_baseline"
down_revision: str | Sequence[str] | None = "0002_finance_sales_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Frozen snapshot of module-owned enums at this revision (05 §6). Enum changes need a new
# migration; never edit this list in place.
MODULE_ENUMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "hr",
        "employee_status",
        (
            "probation",
            "active",
            "on_leave",
            "terminated",
        ),
    ),
    (
        "hr",
        "contract_type",
        (
            "permanent",
            "fixed_term",
            "probation",
            "intern",
            "contractor",
        ),
    ),
    (
        "hr",
        "leave_type",
        (
            "annual",
            "sick",
            "unpaid",
            "public_holiday",
            "other",
        ),
    ),
    (
        "hr",
        "leave_status",
        (
            "requested",
            "approved",
            "rejected",
            "cancelled",
        ),
    ),
    (
        "hr",
        "hiring_priority",
        (
            "low",
            "medium",
            "high",
            "critical",
        ),
    ),
    (
        "hr",
        "hiring_status",
        (
            "draft",
            "submitted",
            "approved",
            "rejected",
            "in_progress",
            "completed",
            "cancelled",
        ),
    ),
    (
        "product",
        "product_status",
        (
            "active",
            "paused",
            "retired",
        ),
    ),
    (
        "product",
        "lifecycle_stage",
        (
            "idea",
            "development",
            "launched",
            "growth",
            "mature",
            "sunset",
        ),
    ),
    (
        "product",
        "feature_status",
        (
            "planned",
            "in_progress",
            "released",
            "deprecated",
        ),
    ),
    (
        "product",
        "roadmap_status",
        (
            "planned",
            "in_progress",
            "done",
            "delayed",
            "dropped",
        ),
    ),
    (
        "product",
        "release_status",
        (
            "planned",
            "in_progress",
            "released",
            "rolled_back",
        ),
    ),
)


def upgrade() -> None:
    for schema, name, values in MODULE_ENUMS:
        postgresql.ENUM(*values, name=name, schema=schema).create(op.get_bind())
    op.create_table(
        "departments",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("aliases", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("head_employee_id", sa.UUID(), nullable=True),
        sa.Column("cost_center", sa.Text(), nullable=True),
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
            ["head_employee_id"],
            ["hr.employees.id"],
            name=op.f("fk_departments_head_employee_id_employees"),
            ondelete="RESTRICT",
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["hr.departments.id"],
            name=op.f("fk_departments_parent_id_departments"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departments")),
        sa.UniqueConstraint("code", name=op.f("uq_departments_code")),
        schema="hr",
    )
    op.create_index(
        op.f("ix_departments_head_employee_id"),
        "departments",
        ["head_employee_id"],
        unique=False,
        schema="hr",
    )
    op.create_index(
        op.f("ix_departments_parent_id"), "departments", ["parent_id"], unique=False, schema="hr"
    )
    op.create_table(
        "products",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active",
                "paused",
                "retired",
                name="product_status",
                create_type=False,
                schema="product",
            ),
            nullable=False,
        ),
        sa.Column(
            "lifecycle_stage",
            postgresql.ENUM(
                "idea",
                "development",
                "launched",
                "growth",
                "mature",
                "sunset",
                name="lifecycle_stage",
                create_type=False,
                schema="product",
            ),
            nullable=False,
        ),
        sa.Column("target_launch_date", sa.Date(), nullable=True),
        sa.Column("launched_at", sa.Date(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("code", name=op.f("uq_products_code")),
        schema="product",
    )
    op.create_index(
        op.f("ix_products_owner_id"), "products", ["owner_id"], unique=False, schema="product"
    )
    op.create_table(
        "hiring_plans",
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Text(), nullable=False),
        sa.Column("headcount", sa.SmallInteger(), nullable=False),
        sa.Column("filled", sa.SmallInteger(), nullable=False),
        sa.Column(
            "priority",
            postgresql.ENUM(
                "low",
                "medium",
                "high",
                "critical",
                name="hiring_priority",
                create_type=False,
                schema="hr",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "submitted",
                "approved",
                "rejected",
                "in_progress",
                "completed",
                "cancelled",
                name="hiring_status",
                create_type=False,
                schema="hr",
            ),
            nullable=False,
        ),
        sa.Column("salary_range_min", sa.BigInteger(), nullable=True),
        sa.Column("salary_range_max", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("target_fill_date", sa.Date(), nullable=False),
        sa.Column("hiring_manager_id", sa.UUID(), nullable=False),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("budget_allocated", sa.BigInteger(), nullable=False),
        sa.Column("budget_spent", sa.BigInteger(), nullable=False),
        sa.Column("delayed_notified_at", sa.DateTime(timezone=True), nullable=True),
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
            "filled >= 0 AND filled <= headcount",
            name=op.f("ck_hiring_plans_filled_within_headcount"),
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["hr.departments.id"],
            name=op.f("fk_hiring_plans_department_id_departments"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hiring_plans")),
        schema="hr",
    )
    op.create_index(
        op.f("ix_hiring_plans_approved_by"),
        "hiring_plans",
        ["approved_by"],
        unique=False,
        schema="hr",
    )
    op.create_index(
        op.f("ix_hiring_plans_department_id"),
        "hiring_plans",
        ["department_id"],
        unique=False,
        schema="hr",
    )
    op.create_index(
        op.f("ix_hiring_plans_hiring_manager_id"),
        "hiring_plans",
        ["hiring_manager_id"],
        unique=False,
        schema="hr",
    )
    op.create_index(
        "ix_hiring_plans_status_target_fill_date",
        "hiring_plans",
        ["status", "target_fill_date"],
        unique=False,
        schema="hr",
    )
    op.create_table(
        "positions",
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("level", sa.SmallInteger(), nullable=True),
        sa.Column("headcount_budget", sa.SmallInteger(), nullable=False),
        sa.Column("reports_to_position_id", sa.UUID(), nullable=True),
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
            "headcount_budget >= 0", name=op.f("ck_positions_headcount_budget_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["hr.departments.id"],
            name=op.f("fk_positions_department_id_departments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reports_to_position_id"],
            ["hr.positions.id"],
            name=op.f("fk_positions_reports_to_position_id_positions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_positions")),
        sa.UniqueConstraint("code", name=op.f("uq_positions_code")),
        schema="hr",
    )
    op.create_index(
        op.f("ix_positions_department_id"),
        "positions",
        ["department_id"],
        unique=False,
        schema="hr",
    )
    op.create_index(
        op.f("ix_positions_reports_to_position_id"),
        "positions",
        ["reports_to_position_id"],
        unique=False,
        schema="hr",
    )
    op.create_table(
        "teams",
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("lead_employee_id", sa.UUID(), nullable=True),
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
            ["department_id"],
            ["hr.departments.id"],
            name=op.f("fk_teams_department_id_departments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lead_employee_id"],
            ["hr.employees.id"],
            name=op.f("fk_teams_lead_employee_id_employees"),
            ondelete="RESTRICT",
            use_alter=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teams")),
        sa.UniqueConstraint("code", name=op.f("uq_teams_code")),
        schema="hr",
    )
    op.create_index(
        op.f("ix_teams_department_id"), "teams", ["department_id"], unique=False, schema="hr"
    )
    op.create_index(
        op.f("ix_teams_lead_employee_id"), "teams", ["lead_employee_id"], unique=False, schema="hr"
    )
    op.create_table(
        "product_metrics",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("period_key", sa.Text(), nullable=False),
        sa.Column("mau", sa.Integer(), nullable=False),
        sa.Column("dau", sa.Integer(), nullable=True),
        sa.Column("adoption_rate_pct", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("churn_rate_pct", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("retention_30d_pct", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("nps", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("arpu", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column("superseded_by_id", sa.UUID(), nullable=True),
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
        sa.CheckConstraint(
            "adoption_rate_pct IS NULL OR adoption_rate_pct BETWEEN 0 AND 100",
            name=op.f("ck_product_metrics_adoption_rate_pct_0_100"),
        ),
        sa.CheckConstraint(
            "churn_rate_pct BETWEEN 0 AND 100", name=op.f("ck_product_metrics_churn_rate_pct_0_100")
        ),
        sa.CheckConstraint("dau IS NULL OR dau <= mau", name=op.f("ck_product_metrics_dau_le_mau")),
        sa.CheckConstraint(
            "nps IS NULL OR nps BETWEEN -100 AND 100", name=op.f("ck_product_metrics_nps_range")
        ),
        sa.CheckConstraint(
            "retention_30d_pct IS NULL OR retention_30d_pct BETWEEN 0 AND 100",
            name=op.f("ck_product_metrics_retention_30d_pct_0_100"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.products.id"],
            name=op.f("fk_product_metrics_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"],
            ["product.product_metrics.id"],
            name=op.f("fk_product_metrics_superseded_by_id_product_metrics"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_metrics")),
        schema="product",
    )
    op.create_index(
        op.f("ix_product_metrics_product_id"),
        "product_metrics",
        ["product_id"],
        unique=False,
        schema="product",
    )
    op.create_index(
        op.f("ix_product_metrics_source_document_id"),
        "product_metrics",
        ["source_document_id"],
        unique=False,
        schema="product",
    )
    op.create_index(
        op.f("ix_product_metrics_superseded_by_id"),
        "product_metrics",
        ["superseded_by_id"],
        unique=False,
        schema="product",
    )
    op.create_index(
        "uq_product_metrics_product_id_period_key_current",
        "product_metrics",
        ["product_id", "period_key"],
        unique=True,
        schema="product",
        postgresql_where=sa.text("superseded_by_id IS NULL"),
    )
    op.create_table(
        "releases",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("release_version", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "planned",
                "in_progress",
                "released",
                "rolled_back",
                name="release_status",
                create_type=False,
                schema="product",
            ),
            nullable=False,
        ),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_notes", sa.Text(), nullable=True),
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
            ["product_id"],
            ["product.products.id"],
            name=op.f("fk_releases_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_releases")),
        sa.UniqueConstraint(
            "product_id", "release_version", name=op.f("uq_releases_product_id_release_version")
        ),
        schema="product",
    )
    op.create_index(
        op.f("ix_releases_product_id"), "releases", ["product_id"], unique=False, schema="product"
    )
    op.create_table(
        "roadmap_items",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("quarter", sa.Text(), nullable=False),
        sa.Column("planned_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.Date(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "planned",
                "in_progress",
                "done",
                "delayed",
                "dropped",
                name="roadmap_status",
                create_type=False,
                schema="product",
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
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.products.id"],
            name=op.f("fk_roadmap_items_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roadmap_items")),
        schema="product",
    )
    op.create_index(
        op.f("ix_roadmap_items_product_id"),
        "roadmap_items",
        ["product_id"],
        unique=False,
        schema="product",
    )
    op.create_table(
        "employees",
        sa.Column("employee_code", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("normalized_name", sa.Text(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("position_id", sa.UUID(), nullable=True),
        sa.Column("team_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "probation",
                "active",
                "on_leave",
                "terminated",
                name="employee_status",
                create_type=False,
                schema="hr",
            ),
            nullable=False,
        ),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column("termination_date", sa.Date(), nullable=True),
        sa.Column(
            "contract_type",
            postgresql.ENUM(
                "permanent",
                "fixed_term",
                "probation",
                "intern",
                "contractor",
                name="contract_type",
                create_type=False,
                schema="hr",
            ),
            nullable=True,
        ),
        sa.Column("manager_id", sa.UUID(), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("national_id", sa.Text(), nullable=True),
        sa.Column("bank_account", sa.Text(), nullable=True),
        sa.Column("emergency_contact", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.CheckConstraint(
            "termination_date IS NULL OR termination_date >= hire_date",
            name=op.f("ck_employees_termination_after_hire"),
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["hr.departments.id"],
            name=op.f("fk_employees_department_id_departments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["manager_id"],
            ["hr.employees.id"],
            name=op.f("fk_employees_manager_id_employees"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["hr.positions.id"],
            name=op.f("fk_employees_position_id_positions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["hr.teams.id"],
            name=op.f("fk_employees_team_id_teams"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employees")),
        sa.UniqueConstraint("email", name=op.f("uq_employees_email")),
        schema="hr",
    )
    op.create_index(
        op.f("ix_employees_department_id"),
        "employees",
        ["department_id"],
        unique=False,
        schema="hr",
    )
    op.create_index(
        "ix_employees_department_id_status",
        "employees",
        ["department_id", "status"],
        unique=False,
        schema="hr",
    )
    op.create_index(
        op.f("ix_employees_manager_id"), "employees", ["manager_id"], unique=False, schema="hr"
    )
    op.create_index(
        "ix_employees_normalized_name_trgm",
        "employees",
        ["normalized_name"],
        unique=False,
        schema="hr",
        postgresql_using="gin",
        postgresql_ops={"normalized_name": "gin_trgm_ops"},
    )
    op.create_index(
        op.f("ix_employees_position_id"), "employees", ["position_id"], unique=False, schema="hr"
    )
    op.create_index(
        op.f("ix_employees_source_document_id"),
        "employees",
        ["source_document_id"],
        unique=False,
        schema="hr",
    )
    op.create_index(
        op.f("ix_employees_team_id"), "employees", ["team_id"], unique=False, schema="hr"
    )
    op.create_index(
        "uq_employees_employee_code_live",
        "employees",
        ["employee_code"],
        unique=True,
        schema="hr",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "features",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "planned",
                "in_progress",
                "released",
                "deprecated",
                name="feature_status",
                create_type=False,
                schema="product",
            ),
            nullable=False,
        ),
        sa.Column("release_id", sa.UUID(), nullable=True),
        sa.Column("roadmap_item_id", sa.UUID(), nullable=True),
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
            ["product_id"],
            ["product.products.id"],
            name=op.f("fk_features_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["release_id"],
            ["product.releases.id"],
            name=op.f("fk_features_release_id_releases"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["roadmap_item_id"],
            ["product.roadmap_items.id"],
            name=op.f("fk_features_roadmap_item_id_roadmap_items"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_features")),
        schema="product",
    )
    op.create_index(
        op.f("ix_features_product_id"), "features", ["product_id"], unique=False, schema="product"
    )
    op.create_index(
        op.f("ix_features_release_id"), "features", ["release_id"], unique=False, schema="product"
    )
    op.create_index(
        op.f("ix_features_roadmap_item_id"),
        "features",
        ["roadmap_item_id"],
        unique=False,
        schema="product",
    )
    op.create_table(
        "employee_skills",
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("skill", sa.Text(), nullable=False),
        sa.Column("level", sa.SmallInteger(), nullable=False),
        sa.Column("verified_by", sa.UUID(), nullable=True),
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
        sa.CheckConstraint("level BETWEEN 1 AND 5", name=op.f("ck_employee_skills_level_1_5")),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["hr.employees.id"],
            name=op.f("fk_employee_skills_employee_id_employees"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee_skills")),
        schema="hr",
    )
    op.create_index(
        op.f("ix_employee_skills_employee_id"),
        "employee_skills",
        ["employee_id"],
        unique=False,
        schema="hr",
    )
    op.create_index(
        op.f("ix_employee_skills_verified_by"),
        "employee_skills",
        ["verified_by"],
        unique=False,
        schema="hr",
    )
    op.create_index(
        "uq_employee_skills_employee_id_skill_live",
        "employee_skills",
        ["employee_id", "skill"],
        unique=True,
        schema="hr",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "leaves",
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column(
            "leave_type",
            postgresql.ENUM(
                "annual",
                "sick",
                "unpaid",
                "public_holiday",
                "other",
                name="leave_type",
                create_type=False,
                schema="hr",
            ),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("hours", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "requested",
                "approved",
                "rejected",
                "cancelled",
                name="leave_status",
                create_type=False,
                schema="hr",
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
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
        sa.CheckConstraint("end_date >= start_date", name=op.f("ck_leaves_end_after_start")),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["hr.employees.id"],
            name=op.f("fk_leaves_employee_id_employees"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leaves")),
        schema="hr",
    )
    op.create_index(
        op.f("ix_leaves_employee_id"), "leaves", ["employee_id"], unique=False, schema="hr"
    )
    op.create_index(
        "ix_leaves_employee_id_start_date",
        "leaves",
        ["employee_id", "start_date"],
        unique=False,
        schema="hr",
    )
    op.create_table(
        "salary_history",
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("base_salary", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
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
        sa.CheckConstraint("base_salary > 0", name=op.f("ck_salary_history_base_salary_positive")),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["hr.employees.id"],
            name=op.f("fk_salary_history_employee_id_employees"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_salary_history")),
        sa.UniqueConstraint(
            "employee_id",
            "effective_date",
            name=op.f("uq_salary_history_employee_id_effective_date"),
        ),
        schema="hr",
    )
    op.create_index(
        op.f("ix_salary_history_employee_id"),
        "salary_history",
        ["employee_id"],
        unique=False,
        schema="hr",
    )
    op.create_index(
        op.f("ix_salary_history_source_document_id"),
        "salary_history",
        ["source_document_id"],
        unique=False,
        schema="hr",
    )
    # Cyclic FKs (use_alter) — added after both tables exist.
    op.create_foreign_key(
        "fk_departments_head_employee_id_employees",
        "departments",
        "employees",
        ["head_employee_id"],
        ["id"],
        source_schema="hr",
        referent_schema="hr",
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_teams_lead_employee_id_employees",
        "teams",
        "employees",
        ["lead_employee_id"],
        ["id"],
        source_schema="hr",
        referent_schema="hr",
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # Cyclic FKs first, so the tables can be dropped.
    op.drop_constraint(
        "fk_departments_head_employee_id_employees", "departments", schema="hr", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_teams_lead_employee_id_employees", "teams", schema="hr", type_="foreignkey"
    )
    op.drop_index(
        op.f("ix_salary_history_source_document_id"), table_name="salary_history", schema="hr"
    )
    op.drop_index(op.f("ix_salary_history_employee_id"), table_name="salary_history", schema="hr")
    op.drop_table("salary_history", schema="hr")
    op.drop_index("ix_leaves_employee_id_start_date", table_name="leaves", schema="hr")
    op.drop_index(op.f("ix_leaves_employee_id"), table_name="leaves", schema="hr")
    op.drop_table("leaves", schema="hr")
    op.drop_index(
        "uq_employee_skills_employee_id_skill_live",
        table_name="employee_skills",
        schema="hr",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_employee_skills_verified_by"), table_name="employee_skills", schema="hr")
    op.drop_index(op.f("ix_employee_skills_employee_id"), table_name="employee_skills", schema="hr")
    op.drop_table("employee_skills", schema="hr")
    op.drop_index(op.f("ix_features_roadmap_item_id"), table_name="features", schema="product")
    op.drop_index(op.f("ix_features_release_id"), table_name="features", schema="product")
    op.drop_index(op.f("ix_features_product_id"), table_name="features", schema="product")
    op.drop_table("features", schema="product")
    op.drop_index(
        "uq_employees_employee_code_live",
        table_name="employees",
        schema="hr",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_employees_team_id"), table_name="employees", schema="hr")
    op.drop_index(op.f("ix_employees_source_document_id"), table_name="employees", schema="hr")
    op.drop_index(op.f("ix_employees_position_id"), table_name="employees", schema="hr")
    op.drop_index(
        "ix_employees_normalized_name_trgm",
        table_name="employees",
        schema="hr",
        postgresql_using="gin",
        postgresql_ops={"normalized_name": "gin_trgm_ops"},
    )
    op.drop_index(op.f("ix_employees_manager_id"), table_name="employees", schema="hr")
    op.drop_index("ix_employees_department_id_status", table_name="employees", schema="hr")
    op.drop_index(op.f("ix_employees_department_id"), table_name="employees", schema="hr")
    op.drop_table("employees", schema="hr")
    op.drop_index(op.f("ix_roadmap_items_product_id"), table_name="roadmap_items", schema="product")
    op.drop_table("roadmap_items", schema="product")
    op.drop_index(op.f("ix_releases_product_id"), table_name="releases", schema="product")
    op.drop_table("releases", schema="product")
    op.drop_index(
        "uq_product_metrics_product_id_period_key_current",
        table_name="product_metrics",
        schema="product",
        postgresql_where=sa.text("superseded_by_id IS NULL"),
    )
    op.drop_index(
        op.f("ix_product_metrics_superseded_by_id"), table_name="product_metrics", schema="product"
    )
    op.drop_index(
        op.f("ix_product_metrics_source_document_id"),
        table_name="product_metrics",
        schema="product",
    )
    op.drop_index(
        op.f("ix_product_metrics_product_id"), table_name="product_metrics", schema="product"
    )
    op.drop_table("product_metrics", schema="product")
    op.drop_index(op.f("ix_teams_lead_employee_id"), table_name="teams", schema="hr")
    op.drop_index(op.f("ix_teams_department_id"), table_name="teams", schema="hr")
    op.drop_table("teams", schema="hr")
    op.drop_index(op.f("ix_positions_reports_to_position_id"), table_name="positions", schema="hr")
    op.drop_index(op.f("ix_positions_department_id"), table_name="positions", schema="hr")
    op.drop_table("positions", schema="hr")
    op.drop_index("ix_hiring_plans_status_target_fill_date", table_name="hiring_plans", schema="hr")
    op.drop_index(op.f("ix_hiring_plans_hiring_manager_id"), table_name="hiring_plans", schema="hr")
    op.drop_index(op.f("ix_hiring_plans_department_id"), table_name="hiring_plans", schema="hr")
    op.drop_index(op.f("ix_hiring_plans_approved_by"), table_name="hiring_plans", schema="hr")
    op.drop_table("hiring_plans", schema="hr")
    op.drop_index(op.f("ix_products_owner_id"), table_name="products", schema="product")
    op.drop_table("products", schema="product")
    op.drop_index(op.f("ix_departments_parent_id"), table_name="departments", schema="hr")
    op.drop_index(op.f("ix_departments_head_employee_id"), table_name="departments", schema="hr")
    op.drop_table("departments", schema="hr")
    for schema, name, values in reversed(MODULE_ENUMS):
        postgresql.ENUM(*values, name=name, schema=schema).drop(op.get_bind())

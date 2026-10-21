"""finance and sales baseline

Revision ID: 0002_finance_sales_baseline
Revises: 0001_platform_auth_baseline
Create Date: 2026-10-21 08:20:29.844219+00:00

Every migration must be reversible (05 §12.1 G3): implement both upgrade() and downgrade().
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_finance_sales_baseline"
down_revision: str | Sequence[str] | None = "0001_platform_auth_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Frozen snapshot of module-owned enums at this revision (05 §6). Enum changes need a new
# migration; never edit this list in place.
MODULE_ENUMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "finance",
        "revenue_category",
        (
            "product_sales",
            "service",
            "consulting",
            "other",
        ),
    ),
    (
        "finance",
        "expense_category",
        (
            "salary",
            "cogs",
            "infrastructure",
            "marketing",
            "office",
            "travel",
            "other",
        ),
    ),
    (
        "finance",
        "record_origin",
        (
            "manual",
            "invoice",
            "financial_report",
            "imported",
        ),
    ),
    (
        "finance",
        "recurrence_period",
        (
            "monthly",
            "quarterly",
            "yearly",
        ),
    ),
    (
        "finance",
        "quarter",
        (
            "Q1",
            "Q2",
            "Q3",
            "Q4",
        ),
    ),
    (
        "finance",
        "forecast_scenario",
        (
            "base",
            "optimistic",
            "pessimistic",
        ),
    ),
    (
        "finance",
        "invoice_direction",
        (
            "OUT",
            "IN",
        ),
    ),
    (
        "finance",
        "invoice_status",
        (
            "draft",
            "sent",
            "partial",
            "paid",
            "overdue",
            "cancelled",
        ),
    ),
    (
        "finance",
        "cash_source",
        (
            "bank_statement",
            "manual",
            "imported",
        ),
    ),
    (
        "sales",
        "company_size",
        (
            "startup",
            "small",
            "medium",
            "enterprise",
        ),
    ),
    (
        "sales",
        "client_status",
        (
            "prospect",
            "active",
            "churned",
        ),
    ),
    (
        "sales",
        "deal_stage",
        (
            "lead",
            "qualified",
            "proposal",
            "negotiation",
            "closed_won",
            "closed_lost",
        ),
    ),
    (
        "sales",
        "target_scope",
        (
            "team",
            "individual",
        ),
    ),
    (
        "sales",
        "contract_status",
        (
            "draft",
            "active",
            "expired",
            "terminated",
        ),
    ),
)


def upgrade() -> None:
    for schema, name, values in MODULE_ENUMS:
        postgresql.ENUM(*values, name=name, schema=schema).create(op.get_bind())
    op.create_table(
        "budgets",
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("fiscal_year", sa.SmallInteger(), nullable=False),
        sa.Column(
            "quarter",
            postgresql.ENUM(
                "Q1", "Q2", "Q3", "Q4", name="quarter", create_type=False, schema="finance"
            ),
            nullable=True,
        ),
        sa.Column("allocated_amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column("categories", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.CheckConstraint("allocated_amount > 0", name=op.f("ck_budgets_allocated_positive")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_budgets")),
        schema="finance",
    )
    op.create_index(
        op.f("ix_budgets_department_id"),
        "budgets",
        ["department_id"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        op.f("ix_budgets_source_document_id"),
        "budgets",
        ["source_document_id"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        "uq_budgets_department_year_quarter",
        "budgets",
        ["department_id", "fiscal_year", "quarter"],
        unique=True,
        schema="finance",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "cash_flow_forecasts",
        sa.Column("start_week", sa.Date(), nullable=False),
        sa.Column("weeks", sa.SmallInteger(), nullable=False),
        sa.Column("opening_cash", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column("min_projected_cash", sa.BigInteger(), nullable=False),
        sa.Column("min_cash_week", sa.SmallInteger(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "generated_by",
            postgresql.ENUM(
                "USER", "AI", "SYSTEM", name="actor_type", create_type=False, schema="platform"
            ),
            nullable=False,
        ),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            "min_cash_week BETWEEN 1 AND 13",
            name=op.f("ck_cash_flow_forecasts_min_cash_week_range"),
        ),
        sa.CheckConstraint("weeks = 13", name=op.f("ck_cash_flow_forecasts_weeks_is_13")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cash_flow_forecasts")),
        schema="finance",
    )
    op.create_index(
        "uq_cash_flow_forecasts_current",
        "cash_flow_forecasts",
        ["is_current"],
        unique=True,
        schema="finance",
        postgresql_where=sa.text("is_current AND deleted_at IS NULL"),
    )
    op.create_table(
        "cash_positions",
        sa.Column("period_key", sa.Text(), nullable=False),
        sa.Column("closing_balance", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column(
            "cash_source",
            postgresql.ENUM(
                "bank_statement",
                "manual",
                "imported",
                name="cash_source",
                create_type=False,
                schema="finance",
            ),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("recorded_by", sa.UUID(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cash_positions")),
        schema="finance",
    )
    op.create_index(
        op.f("ix_cash_positions_recorded_by"),
        "cash_positions",
        ["recorded_by"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        op.f("ix_cash_positions_source_document_id"),
        "cash_positions",
        ["source_document_id"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        "uq_cash_positions_period_key",
        "cash_positions",
        ["period_key"],
        unique=True,
        schema="finance",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "forecasts",
        sa.Column("horizon_months", sa.SmallInteger(), nullable=False),
        sa.Column(
            "scenario",
            postgresql.ENUM(
                "base",
                "optimistic",
                "pessimistic",
                name="forecast_scenario",
                create_type=False,
                schema="finance",
            ),
            nullable=False,
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "generated_by",
            postgresql.ENUM(
                "USER", "AI", "SYSTEM", name="actor_type", create_type=False, schema="platform"
            ),
            nullable=False,
        ),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ai_insights", sa.Text(), nullable=True),
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
            "horizon_months IN (3, 6, 12)", name=op.f("ck_forecasts_horizon_allowed")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_forecasts")),
        schema="finance",
    )
    op.create_index(
        "uq_forecasts_current_scenario",
        "forecasts",
        ["scenario"],
        unique=True,
        schema="finance",
        postgresql_where=sa.text("is_current AND deleted_at IS NULL"),
    )
    op.create_table(
        "invoices",
        sa.Column(
            "direction",
            postgresql.ENUM(
                "OUT", "IN", name="invoice_direction", create_type=False, schema="finance"
            ),
            nullable=False,
        ),
        sa.Column("series", sa.Text(), nullable=True),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("client_name_snapshot", sa.Text(), nullable=True),
        sa.Column("client_tax_code", sa.Text(), nullable=True),
        sa.Column("counterparty_name", sa.Text(), nullable=True),
        sa.Column("counterparty_tax_code", sa.Text(), nullable=True),
        sa.Column("subtotal", sa.BigInteger(), nullable=False),
        sa.Column("vat_rate_pct", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("vat_amount", sa.BigInteger(), nullable=False),
        sa.Column("total_amount", sa.BigInteger(), nullable=False),
        sa.Column("paid_amount", sa.BigInteger(), nullable=False),
        sa.Column(
            "amount_due",
            sa.BigInteger(),
            sa.Computed("total_amount - paid_amount", persisted=True),
            nullable=False,
        ),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "sent",
                "partial",
                "paid",
                "overdue",
                "cancelled",
                name="invoice_status",
                create_type=False,
                schema="finance",
            ),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            "direction <> 'OUT' OR client_id IS NOT NULL",
            name=op.f("ck_invoices_out_requires_client"),
        ),
        sa.CheckConstraint(
            "due_date IS NULL OR due_date >= issue_date", name=op.f("ck_invoices_due_after_issue")
        ),
        sa.CheckConstraint(
            "paid_amount >= 0 AND paid_amount <= total_amount",
            name=op.f("ck_invoices_paid_in_range"),
        ),
        sa.CheckConstraint("subtotal >= 0", name=op.f("ck_invoices_subtotal_non_negative")),
        sa.CheckConstraint(
            "total_amount = subtotal + vat_amount", name=op.f("ck_invoices_total_is_sum")
        ),
        sa.CheckConstraint(
            "vat_rate_pct IN (0, 5, 8, 10)", name=op.f("ck_invoices_vat_rate_allowed")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoices")),
        schema="finance",
    )
    op.create_index(
        op.f("ix_invoices_client_id"), "invoices", ["client_id"], unique=False, schema="finance"
    )
    op.create_index(
        "ix_invoices_direction_status_due_date",
        "invoices",
        ["direction", "status", "due_date"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        "ix_invoices_issue_date", "invoices", ["issue_date"], unique=False, schema="finance"
    )
    op.create_index(
        op.f("ix_invoices_source_document_id"),
        "invoices",
        ["source_document_id"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        "uq_invoices_business_key",
        "invoices",
        [
            "direction",
            sa.literal_column("COALESCE(counterparty_tax_code, '')"),
            sa.literal_column("COALESCE(series, '')"),
            "number",
        ],
        unique=True,
        schema="finance",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "clients",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("normalized_name", sa.Text(), nullable=False),
        sa.Column("tax_code", sa.Text(), nullable=True),
        sa.Column("industry", sa.Text(), nullable=True),
        sa.Column(
            "company_size",
            postgresql.ENUM(
                "startup",
                "small",
                "medium",
                "enterprise",
                name="company_size",
                create_type=False,
                schema="sales",
            ),
            nullable=True,
        ),
        sa.Column("contact_person", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column("contact_phone", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("account_owner_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "prospect",
                "active",
                "churned",
                name="client_status",
                create_type=False,
                schema="sales",
            ),
            nullable=False,
        ),
        sa.Column("merged_into_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            ["merged_into_id"],
            ["sales.clients.id"],
            name=op.f("fk_clients_merged_into_id_clients"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clients")),
        schema="sales",
    )
    op.create_index(
        op.f("ix_clients_account_owner_id"),
        "clients",
        ["account_owner_id"],
        unique=False,
        schema="sales",
    )
    op.create_index(
        op.f("ix_clients_merged_into_id"),
        "clients",
        ["merged_into_id"],
        unique=False,
        schema="sales",
    )
    op.create_index(
        "ix_clients_normalized_name_trgm",
        "clients",
        ["normalized_name"],
        unique=False,
        schema="sales",
        postgresql_using="gin",
        postgresql_ops={"normalized_name": "gin_trgm_ops"},
    )
    op.create_index(
        "uq_clients_tax_code",
        "clients",
        ["tax_code"],
        unique=True,
        schema="sales",
        postgresql_where=sa.text("tax_code IS NOT NULL AND deleted_at IS NULL"),
    )
    op.create_table(
        "sales_targets",
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
            "scope",
            postgresql.ENUM(
                "team", "individual", name="target_scope", create_type=False, schema="sales"
            ),
            nullable=False,
        ),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("target_amount", sa.BigInteger(), nullable=False),
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
            "target_amount > 0", name=op.f("ck_sales_targets_target_amount_positive")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sales_targets")),
        schema="sales",
    )
    op.create_index(
        op.f("ix_sales_targets_owner_id"),
        "sales_targets",
        ["owner_id"],
        unique=False,
        schema="sales",
    )
    op.create_index(
        "uq_sales_targets_period_scope_owner",
        "sales_targets",
        [
            "period_key",
            "scope",
            sa.literal_column("COALESCE(owner_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
        ],
        unique=True,
        schema="sales",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "cash_flow_forecast_lines",
        sa.Column("forecast_id", sa.UUID(), nullable=False),
        sa.Column("week_no", sa.SmallInteger(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("inflow_receivables", sa.BigInteger(), nullable=False),
        sa.Column("inflow_other", sa.BigInteger(), nullable=False),
        sa.Column("outflow_payables", sa.BigInteger(), nullable=False),
        sa.Column("outflow_payroll", sa.BigInteger(), nullable=False),
        sa.Column("outflow_opex", sa.BigInteger(), nullable=False),
        sa.Column("outflow_other", sa.BigInteger(), nullable=False),
        sa.Column("net_flow", sa.BigInteger(), nullable=False),
        sa.Column("closing_cash", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column(
            "confidence_level",
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
            "week_no BETWEEN 1 AND 13", name=op.f("ck_cash_flow_forecast_lines_week_no_range")
        ),
        sa.ForeignKeyConstraint(
            ["forecast_id"],
            ["finance.cash_flow_forecasts.id"],
            name=op.f("fk_cash_flow_forecast_lines_forecast_id_cash_flow_forecasts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cash_flow_forecast_lines")),
        sa.UniqueConstraint(
            "forecast_id", "week_no", name=op.f("uq_cash_flow_forecast_lines_forecast_id_week_no")
        ),
        schema="finance",
    )
    op.create_index(
        op.f("ix_cash_flow_forecast_lines_forecast_id"),
        "cash_flow_forecast_lines",
        ["forecast_id"],
        unique=False,
        schema="finance",
    )
    op.create_table(
        "expenses",
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(
                "salary",
                "cogs",
                "infrastructure",
                "marketing",
                "office",
                "travel",
                "other",
                name="expense_category",
                create_type=False,
                schema="finance",
            ),
            nullable=False,
        ),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("budget_id", sa.UUID(), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("period_key", sa.Text(), nullable=False),
        sa.Column("is_recurring", sa.Boolean(), nullable=False),
        sa.Column(
            "recurrence_period",
            postgresql.ENUM(
                "monthly",
                "quarterly",
                "yearly",
                name="recurrence_period",
                create_type=False,
                schema="finance",
            ),
            nullable=True,
        ),
        sa.Column("invoice_id", sa.UUID(), nullable=True),
        sa.Column("counterparty_name", sa.Text(), nullable=True),
        sa.Column("counterparty_tax_code", sa.Text(), nullable=True),
        sa.Column(
            "origin",
            postgresql.ENUM(
                "manual",
                "invoice",
                "financial_report",
                "imported",
                name="record_origin",
                create_type=False,
                schema="finance",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.CheckConstraint("amount >= 0", name=op.f("ck_expenses_amount_non_negative")),
        sa.ForeignKeyConstraint(
            ["budget_id"],
            ["finance.budgets.id"],
            name=op.f("fk_expenses_budget_id_budgets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["finance.invoices.id"],
            name=op.f("fk_expenses_invoice_id_invoices"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expenses")),
        schema="finance",
    )
    op.create_index(
        op.f("ix_expenses_budget_id"), "expenses", ["budget_id"], unique=False, schema="finance"
    )
    op.create_index(
        op.f("ix_expenses_department_id"),
        "expenses",
        ["department_id"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        op.f("ix_expenses_invoice_id"), "expenses", ["invoice_id"], unique=False, schema="finance"
    )
    op.create_index(
        "ix_expenses_period_key_category",
        "expenses",
        ["period_key", "category"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        "ix_expenses_period_key_department_id",
        "expenses",
        ["period_key", "department_id"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        op.f("ix_expenses_source_document_id"),
        "expenses",
        ["source_document_id"],
        unique=False,
        schema="finance",
    )
    op.create_table(
        "forecast_lines",
        sa.Column("forecast_id", sa.UUID(), nullable=False),
        sa.Column("period_key", sa.Text(), nullable=False),
        sa.Column("projected_revenue", sa.BigInteger(), nullable=False),
        sa.Column("projected_expenses", sa.BigInteger(), nullable=False),
        sa.Column("projected_net_profit", sa.BigInteger(), nullable=False),
        sa.Column("projected_closing_cash", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column(
            "confidence_level",
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
            ["forecast_id"],
            ["finance.forecasts.id"],
            name=op.f("fk_forecast_lines_forecast_id_forecasts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_forecast_lines")),
        sa.UniqueConstraint(
            "forecast_id", "period_key", name=op.f("uq_forecast_lines_forecast_id_period_key")
        ),
        schema="finance",
    )
    op.create_index(
        op.f("ix_forecast_lines_forecast_id"),
        "forecast_lines",
        ["forecast_id"],
        unique=False,
        schema="finance",
    )
    op.create_table(
        "invoice_lines",
        sa.Column("invoice_id", sa.UUID(), nullable=False),
        sa.Column("line_no", sa.SmallInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=True),
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
        sa.CheckConstraint("quantity > 0", name=op.f("ck_invoice_lines_quantity_positive")),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["finance.invoices.id"],
            name=op.f("fk_invoice_lines_invoice_id_invoices"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoice_lines")),
        sa.UniqueConstraint(
            "invoice_id", "line_no", name=op.f("uq_invoice_lines_invoice_id_line_no")
        ),
        schema="finance",
    )
    op.create_index(
        op.f("ix_invoice_lines_invoice_id"),
        "invoice_lines",
        ["invoice_id"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        op.f("ix_invoice_lines_product_id"),
        "invoice_lines",
        ["product_id"],
        unique=False,
        schema="finance",
    )
    op.create_table(
        "revenues",
        sa.Column("source_note", sa.Text(), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(
                "product_sales",
                "service",
                "consulting",
                "other",
                name="revenue_category",
                create_type=False,
                schema="finance",
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column("revenue_date", sa.Date(), nullable=False),
        sa.Column("period_key", sa.Text(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("invoice_id", sa.UUID(), nullable=True),
        sa.Column(
            "origin",
            postgresql.ENUM(
                "manual",
                "invoice",
                "financial_report",
                "imported",
                name="record_origin",
                create_type=False,
                schema="finance",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.CheckConstraint("amount >= 0", name=op.f("ck_revenues_amount_non_negative")),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["finance.invoices.id"],
            name=op.f("fk_revenues_invoice_id_invoices"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_revenues")),
        schema="finance",
    )
    op.create_index(
        op.f("ix_revenues_client_id"), "revenues", ["client_id"], unique=False, schema="finance"
    )
    op.create_index(
        op.f("ix_revenues_invoice_id"), "revenues", ["invoice_id"], unique=False, schema="finance"
    )
    op.create_index(
        "ix_revenues_period_key_category",
        "revenues",
        ["period_key", "category"],
        unique=False,
        schema="finance",
    )
    op.create_index(
        op.f("ix_revenues_product_id"), "revenues", ["product_id"], unique=False, schema="finance"
    )
    op.create_index(
        op.f("ix_revenues_source_document_id"),
        "revenues",
        ["source_document_id"],
        unique=False,
        schema="finance",
    )
    op.create_table(
        "deals",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("deal_value", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column(
            "stage",
            postgresql.ENUM(
                "lead",
                "qualified",
                "proposal",
                "negotiation",
                "closed_won",
                "closed_lost",
                name="deal_stage",
                create_type=False,
                schema="sales",
            ),
            nullable=False,
        ),
        sa.Column("probability_pct", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column(
            "weighted_value",
            sa.BigInteger(),
            sa.Computed("(deal_value * probability_pct / 100)::bigint", persisted=True),
            nullable=False,
        ),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lost_reason", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.CheckConstraint("deal_value >= 0", name=op.f("ck_deals_deal_value_non_negative")),
        sa.CheckConstraint(
            "probability_pct >= 0 AND probability_pct <= 100",
            name=op.f("ck_deals_probability_pct_range"),
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["sales.clients.id"],
            name=op.f("fk_deals_client_id_clients"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deals")),
        schema="sales",
    )
    op.create_index(
        op.f("ix_deals_assigned_to"), "deals", ["assigned_to"], unique=False, schema="sales"
    )
    op.create_index(
        op.f("ix_deals_client_id"), "deals", ["client_id"], unique=False, schema="sales"
    )
    op.create_index(
        op.f("ix_deals_department_id"), "deals", ["department_id"], unique=False, schema="sales"
    )
    op.create_index(
        op.f("ix_deals_product_id"), "deals", ["product_id"], unique=False, schema="sales"
    )
    op.create_index(
        op.f("ix_deals_source_document_id"),
        "deals",
        ["source_document_id"],
        unique=False,
        schema="sales",
    )
    op.create_index(
        "ix_deals_stage_expected_close_date",
        "deals",
        ["stage", "expected_close_date"],
        unique=False,
        schema="sales",
    )
    op.create_table(
        "contracts",
        sa.Column("contract_number", sa.Text(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("deal_id", sa.UUID(), nullable=True),
        sa.Column("contract_value", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column("signed_at", sa.Date(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("renewal_notice_days", sa.SmallInteger(), nullable=True),
        sa.Column("payment_terms", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "active",
                "expired",
                "terminated",
                name="contract_status",
                create_type=False,
                schema="sales",
            ),
            nullable=False,
        ),
        sa.Column("is_recurring", sa.Boolean(), nullable=False),
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
        sa.CheckConstraint("contract_value > 0", name=op.f("ck_contracts_contract_value_positive")),
        sa.CheckConstraint(
            "expiry_date IS NULL OR expiry_date >= effective_date",
            name=op.f("ck_contracts_expiry_after_effective"),
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["sales.clients.id"],
            name=op.f("fk_contracts_client_id_clients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["sales.deals.id"],
            name=op.f("fk_contracts_deal_id_deals"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contracts")),
        schema="sales",
    )
    op.create_index(
        op.f("ix_contracts_client_id"), "contracts", ["client_id"], unique=False, schema="sales"
    )
    op.create_index(
        op.f("ix_contracts_deal_id"), "contracts", ["deal_id"], unique=False, schema="sales"
    )
    op.create_index(
        op.f("ix_contracts_source_document_id"),
        "contracts",
        ["source_document_id"],
        unique=False,
        schema="sales",
    )
    op.create_index(
        "ix_contracts_status_expiry_date",
        "contracts",
        ["status", "expiry_date"],
        unique=False,
        schema="sales",
    )
    op.create_index(
        "uq_contracts_contract_number",
        "contracts",
        ["contract_number"],
        unique=True,
        schema="sales",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "deal_stage_history",
        sa.Column("deal_id", sa.UUID(), nullable=False),
        sa.Column(
            "stage",
            postgresql.ENUM(
                "lead",
                "qualified",
                "proposal",
                "negotiation",
                "closed_won",
                "closed_lost",
                name="deal_stage",
                create_type=False,
                schema="sales",
            ),
            nullable=False,
        ),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exited_at", sa.DateTime(timezone=True), nullable=True),
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
            ["deal_id"],
            ["sales.deals.id"],
            name=op.f("fk_deal_stage_history_deal_id_deals"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deal_stage_history")),
        schema="sales",
    )
    op.create_index(
        op.f("ix_deal_stage_history_deal_id"),
        "deal_stage_history",
        ["deal_id"],
        unique=False,
        schema="sales",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_deal_stage_history_deal_id"), table_name="deal_stage_history", schema="sales"
    )
    op.drop_table("deal_stage_history", schema="sales")
    op.drop_index(
        "uq_contracts_contract_number",
        table_name="contracts",
        schema="sales",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index("ix_contracts_status_expiry_date", table_name="contracts", schema="sales")
    op.drop_index(op.f("ix_contracts_source_document_id"), table_name="contracts", schema="sales")
    op.drop_index(op.f("ix_contracts_deal_id"), table_name="contracts", schema="sales")
    op.drop_index(op.f("ix_contracts_client_id"), table_name="contracts", schema="sales")
    op.drop_table("contracts", schema="sales")
    op.drop_index("ix_deals_stage_expected_close_date", table_name="deals", schema="sales")
    op.drop_index(op.f("ix_deals_source_document_id"), table_name="deals", schema="sales")
    op.drop_index(op.f("ix_deals_product_id"), table_name="deals", schema="sales")
    op.drop_index(op.f("ix_deals_department_id"), table_name="deals", schema="sales")
    op.drop_index(op.f("ix_deals_client_id"), table_name="deals", schema="sales")
    op.drop_index(op.f("ix_deals_assigned_to"), table_name="deals", schema="sales")
    op.drop_table("deals", schema="sales")
    op.drop_index(op.f("ix_revenues_source_document_id"), table_name="revenues", schema="finance")
    op.drop_index(op.f("ix_revenues_product_id"), table_name="revenues", schema="finance")
    op.drop_index("ix_revenues_period_key_category", table_name="revenues", schema="finance")
    op.drop_index(op.f("ix_revenues_invoice_id"), table_name="revenues", schema="finance")
    op.drop_index(op.f("ix_revenues_client_id"), table_name="revenues", schema="finance")
    op.drop_table("revenues", schema="finance")
    op.drop_index(op.f("ix_invoice_lines_product_id"), table_name="invoice_lines", schema="finance")
    op.drop_index(op.f("ix_invoice_lines_invoice_id"), table_name="invoice_lines", schema="finance")
    op.drop_table("invoice_lines", schema="finance")
    op.drop_index(
        op.f("ix_forecast_lines_forecast_id"), table_name="forecast_lines", schema="finance"
    )
    op.drop_table("forecast_lines", schema="finance")
    op.drop_index(op.f("ix_expenses_source_document_id"), table_name="expenses", schema="finance")
    op.drop_index("ix_expenses_period_key_department_id", table_name="expenses", schema="finance")
    op.drop_index("ix_expenses_period_key_category", table_name="expenses", schema="finance")
    op.drop_index(op.f("ix_expenses_invoice_id"), table_name="expenses", schema="finance")
    op.drop_index(op.f("ix_expenses_department_id"), table_name="expenses", schema="finance")
    op.drop_index(op.f("ix_expenses_budget_id"), table_name="expenses", schema="finance")
    op.drop_table("expenses", schema="finance")
    op.drop_index(
        op.f("ix_cash_flow_forecast_lines_forecast_id"),
        table_name="cash_flow_forecast_lines",
        schema="finance",
    )
    op.drop_table("cash_flow_forecast_lines", schema="finance")
    op.drop_index(
        "uq_sales_targets_period_scope_owner",
        table_name="sales_targets",
        schema="sales",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_sales_targets_owner_id"), table_name="sales_targets", schema="sales")
    op.drop_table("sales_targets", schema="sales")
    op.drop_index(
        "uq_clients_tax_code",
        table_name="clients",
        schema="sales",
        postgresql_where=sa.text("tax_code IS NOT NULL AND deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_clients_normalized_name_trgm",
        table_name="clients",
        schema="sales",
        postgresql_using="gin",
        postgresql_ops={"normalized_name": "gin_trgm_ops"},
    )
    op.drop_index(op.f("ix_clients_merged_into_id"), table_name="clients", schema="sales")
    op.drop_index(op.f("ix_clients_account_owner_id"), table_name="clients", schema="sales")
    op.drop_table("clients", schema="sales")
    op.drop_index(
        "uq_invoices_business_key",
        table_name="invoices",
        schema="finance",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_invoices_source_document_id"), table_name="invoices", schema="finance")
    op.drop_index("ix_invoices_issue_date", table_name="invoices", schema="finance")
    op.drop_index("ix_invoices_direction_status_due_date", table_name="invoices", schema="finance")
    op.drop_index(op.f("ix_invoices_client_id"), table_name="invoices", schema="finance")
    op.drop_table("invoices", schema="finance")
    op.drop_index(
        "uq_forecasts_current_scenario",
        table_name="forecasts",
        schema="finance",
        postgresql_where=sa.text("is_current AND deleted_at IS NULL"),
    )
    op.drop_table("forecasts", schema="finance")
    op.drop_index(
        "uq_cash_positions_period_key",
        table_name="cash_positions",
        schema="finance",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        op.f("ix_cash_positions_source_document_id"), table_name="cash_positions", schema="finance"
    )
    op.drop_index(
        op.f("ix_cash_positions_recorded_by"), table_name="cash_positions", schema="finance"
    )
    op.drop_table("cash_positions", schema="finance")
    op.drop_index(
        "uq_cash_flow_forecasts_current",
        table_name="cash_flow_forecasts",
        schema="finance",
        postgresql_where=sa.text("is_current AND deleted_at IS NULL"),
    )
    op.drop_table("cash_flow_forecasts", schema="finance")
    op.drop_index(
        "uq_budgets_department_year_quarter",
        table_name="budgets",
        schema="finance",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_budgets_source_document_id"), table_name="budgets", schema="finance")
    op.drop_index(op.f("ix_budgets_department_id"), table_name="budgets", schema="finance")
    op.drop_table("budgets", schema="finance")
    for schema, name, values in reversed(MODULE_ENUMS):
        postgresql.ENUM(*values, name=name, schema=schema).drop(op.get_bind())

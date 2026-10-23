"""M1.2 T-611: ENT-Organization + effective-dated departments/teams (05 §2.4, R-DEC-24).

Revision ID: 0011_org_structure
Revises: 0010_tenant_outbox
Create Date: 2026-10-23

- `hr.organizations` (BusinessModel, unique live `(tenant_id, code)`, `[valid_from, valid_to)`).
- `hr.departments`: + `organization_id` (FK RESTRICT, indexed), + `valid_from`/`valid_to`.
- `hr.teams`: + `valid_from`/`valid_to`.
- `code` unique: global → live `(tenant_id, code)` on departments / teams / positions.
- Backfill: one Organization per tenant that already has departments (default tenant gets the
  seed id/code of company ABC so `app.seed` stays idempotent); `valid_from = LEAST(created_at, earliest hire in the unit)`;
  organization `valid_from` = earliest department.

Reversible: downgrade drops the new columns/table and restores the global unique constraints
(fails loudly if two live tenants now share a code — never silently drops data).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_org_structure"
down_revision: str | None = "0010_tenant_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
# = app.seed.ids.seed_uuid("organization", "ABC") — frozen here (migrations never import app).
ABC_ORG_ID = "a0211042-441b-5ba9-84d3-a17aa0f5844f"
S = "hr"
CODE_TABLES = ("departments", "teams", "positions")
RANGE_CK = "valid_to IS NULL OR valid_to > valid_from"


def _enum(name: str, *values: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False, schema="platform")


def _create_organizations() -> None:
    op.create_table(
        "organizations",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("legal_name", sa.Text(), nullable=True),
        sa.Column("tax_code", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"),
            nullable=False,
        ),
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
            _enum("record_source", "MANUAL", "IDP", "IMPORT", "AI", "EVENT", "SEED"),
            nullable=False,
        ),
        sa.Column(
            "data_classification",
            _enum("data_classification", "PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(RANGE_CK, name=op.f("ck_organizations_valid_to_after_valid_from")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        schema=S,
    )
    op.create_index(op.f("ix_organizations_tenant_id"), "organizations", ["tenant_id"], schema=S)
    _live_code_index("organizations")


def _live_code_index(table: str) -> None:
    op.create_index(
        f"uq_{table}_tenant_id_code_live", table, ["tenant_id", "code"], unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"), schema=S,
    )  # fmt: skip


# Start no later than the earliest hire placed in the unit, so the assignment backfill of
# T-612 (`valid_from = hire_date`) never predates its department/team. Literal SQL per table.
VALIDITY_BACKFILL = {
    "departments": (
        "UPDATE hr.departments u SET valid_from = LEAST(u.created_at::date, COALESCE("
        "(SELECT min(e.hire_date) FROM hr.employees e WHERE e.department_id = u.id), "
        "u.created_at::date))",
        "UPDATE hr.departments SET valid_to = GREATEST(deleted_at::date, valid_from + 1) "
        "WHERE deleted_at IS NOT NULL",
    ),
    "teams": (
        "UPDATE hr.teams u SET valid_from = LEAST(u.created_at::date, COALESCE("
        "(SELECT min(e.hire_date) FROM hr.employees e WHERE e.team_id = u.id), "
        "u.created_at::date))",
        "UPDATE hr.teams SET valid_to = GREATEST(deleted_at::date, valid_from + 1) "
        "WHERE deleted_at IS NOT NULL",
    ),
}

# One Organization per tenant owning departments; the default tenant gets company ABC's seed id.
ORG_BACKFILL = (
    "INSERT INTO hr.organizations (id, tenant_id, code, name, valid_from, source) "
    "SELECT CASE WHEN d.tenant_id = CAST(:default_tenant AS uuid) "
    "THEN CAST(:abc_id AS uuid) ELSE gen_random_uuid() END, d.tenant_id, "
    "CASE WHEN d.tenant_id = CAST(:default_tenant AS uuid) THEN 'ABC' ELSE 'ORG' END, "
    "CASE WHEN d.tenant_id = CAST(:default_tenant AS uuid) THEN :abc_name "
    "ELSE 'Organization' END, min(d.valid_from), 'MANUAL' "
    "FROM hr.departments d GROUP BY d.tenant_id"
)
DEPT_ORG_BACKFILL = (
    "UPDATE hr.departments d SET organization_id = o.id FROM hr.organizations o "
    "WHERE o.tenant_id = d.tenant_id"
)


def _add_validity(table: str) -> None:
    op.add_column(table, sa.Column("valid_from", sa.Date(), nullable=True), schema=S)
    op.add_column(table, sa.Column("valid_to", sa.Date(), nullable=True), schema=S)
    for sql in VALIDITY_BACKFILL[table]:
        op.execute(sql)
    op.alter_column(table, "valid_from", nullable=False, schema=S)
    op.create_check_constraint(
        op.f(f"ck_{table}_valid_to_after_valid_from"), table, RANGE_CK, schema=S
    )


def _backfill_organizations() -> None:
    op.get_bind().execute(
        sa.text(ORG_BACKFILL),
        {"default_tenant": DEFAULT_TENANT_ID, "abc_id": ABC_ORG_ID,
         "abc_name": "Công ty TNHH TM&DV ABC"},
    )  # fmt: skip
    op.execute(DEPT_ORG_BACKFILL)


def upgrade() -> None:
    _create_organizations()
    for table in ("departments", "teams"):
        _add_validity(table)
    op.add_column("departments", sa.Column("organization_id", sa.UUID(), nullable=True), schema=S)
    _backfill_organizations()
    op.alter_column("departments", "organization_id", nullable=False, schema=S)
    op.create_foreign_key(
        op.f("fk_departments_organization_id_organizations"), "departments", "organizations",
        ["organization_id"], ["id"], ondelete="RESTRICT", source_schema=S, referent_schema=S,
    )  # fmt: skip
    op.create_index(
        op.f("ix_departments_organization_id"), "departments", ["organization_id"], schema=S
    )
    for table in CODE_TABLES:
        op.drop_constraint(op.f(f"uq_{table}_code"), table, type_="unique", schema=S)
        _live_code_index(table)


def downgrade() -> None:
    for table in CODE_TABLES:
        op.drop_index(f"uq_{table}_tenant_id_code_live", table_name=table, schema=S)
        op.create_unique_constraint(op.f(f"uq_{table}_code"), table, ["code"], schema=S)
    for table in ("departments", "teams"):
        op.drop_constraint(
            op.f(f"ck_{table}_valid_to_after_valid_from"), table, type_="check", schema=S
        )
        op.drop_column(table, "valid_to", schema=S)
        op.drop_column(table, "valid_from", schema=S)
    op.drop_index(op.f("ix_departments_organization_id"), table_name="departments", schema=S)
    op.drop_constraint(
        op.f("fk_departments_organization_id_organizations"), "departments",
        type_="foreignkey", schema=S,
    )  # fmt: skip
    op.drop_column("departments", "organization_id", schema=S)
    op.drop_index("uq_organizations_tenant_id_code_live", table_name="organizations", schema=S)
    op.drop_index(op.f("ix_organizations_tenant_id"), table_name="organizations", schema=S)
    op.drop_table("organizations", schema=S)

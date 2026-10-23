"""M1.2 T-612: `hr.employee_assignments` — effective-dated placement (05 §2.4/§6ter, FR-ORG-04).

Revision ID: 0012_employee_assignments
Revises: 0011_org_structure
Create Date: 2026-10-23

- Half-open `[valid_from, valid_to)`; CHECK `valid_to > valid_from`, CHECK manager ≠ employee.
- Partial unique `(employee_id) WHERE valid_to IS NULL AND deleted_at IS NULL` = at most one
  current assignment per employee. Overlap of past ranges is checked by the service under a row
  lock (no `btree_gist` — OQ-05-07, human 2026-10-23).
- Backfill: one row per live employee from the cached columns of `hr.employees`:
  `valid_from = hire_date`, `valid_to = termination_date` (NULL while employed).

Reversible: downgrade drops the table (cached columns on `hr.employees` are untouched).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_employee_assignments"
down_revision: str | None = "0011_org_structure"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
S = "hr"
T = "employee_assignments"
FKS = (
    ("employee_id", "employees", False),
    ("department_id", "departments", False),
    ("team_id", "teams", True),
    ("position_id", "positions", True),
    ("manager_id", "employees", True),
)
# Termination on the hire day would give an empty range → keep it one day long.
BACKFILL = (
    "INSERT INTO hr.employee_assignments (tenant_id, employee_id, department_id, team_id, "
    "position_id, manager_id, valid_from, valid_to, reason, source) "
    "SELECT e.tenant_id, e.id, e.department_id, e.team_id, e.position_id, "
    "CASE WHEN e.manager_id = e.id THEN NULL ELSE e.manager_id END, e.hire_date, "
    "CASE WHEN e.termination_date IS NULL THEN NULL "
    "ELSE GREATEST(e.termination_date, e.hire_date + 1) END, "
    "'Khởi tạo từ dữ liệu hiện có (migration 0012)', e.source "
    "FROM hr.employees e WHERE e.deleted_at IS NULL"
)


def _enum(name: str, *values: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False, schema="platform")


def upgrade() -> None:
    op.create_table(
        T,
        *(sa.Column(col, sa.UUID(), nullable=nullable) for col, _, nullable in FKS),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name=op.f(f"ck_{T}_valid_to_after_valid_from"),
        ),
        sa.CheckConstraint(
            "manager_id IS NULL OR manager_id <> employee_id",
            name=op.f(f"ck_{T}_manager_not_self"),
        ),
        *(
            sa.ForeignKeyConstraint(
                [col], [f"{S}.{ref}.id"], name=op.f(f"fk_{T}_{col}_{ref}"), ondelete="RESTRICT"
            )
            for col, ref, _ in FKS
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{T}")),
        schema=S,
    )
    for col in ("tenant_id", *(c for c, _, _ in FKS)):
        op.create_index(op.f(f"ix_{T}_{col}"), T, [col], schema=S)
    op.create_index(f"ix_{T}_employee_id_valid_from", T, ["employee_id", "valid_from"], schema=S)
    op.create_index(
        f"ix_{T}_department_id_valid_from", T, ["department_id", "valid_from"], schema=S
    )
    op.create_index(
        f"uq_{T}_employee_id_current",
        T,
        ["employee_id"],
        unique=True,
        postgresql_where=sa.text("valid_to IS NULL AND deleted_at IS NULL"),
        schema=S,
    )
    op.execute(BACKFILL)


def downgrade() -> None:
    op.drop_table(T, schema=S)

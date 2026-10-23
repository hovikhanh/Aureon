"""v3 refactor Phase 1: role_code 10→7 (R-DEC-12), tenant_id (R-DEC-13), users.scope_pillars (R-DEC-12a).

Revision ID: 0009_v3_roles_tenant
Revises: 0008_pgcrypto
Create Date: 2026-10-23

Reversible:
- `auth.role_code` enum 10 giá trị F.O.C.U.S → 7 giá trị v3 (CEO/DIR/MGR/EMP/REV/ADM/AI) qua
  kiểu trung gian + ALTER TYPE USING (remap CASE). Downgrade đảo lại.
- `tenant_id UUID NOT NULL` + index trên 47 business table (server_default = tenant mặc định,
  backfill dữ liệu hiện có). Downgrade drop.
- `auth.users.scope_pillars PILLAR[] NOT NULL DEFAULT '{}'`. Downgrade drop.
- `auth.roles`: gộp 5 C-level → 1 DIR row, repoint `auth.users.role_id`; downgrade tách lại
  (các user DIR quay về role theo scope_pillars).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_v3_roles_tenant"
down_revision: str | None = "0008_pgcrypto"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"

# (schema, table) mang tenant_id — BusinessModel subclasses (47).
BUSINESS_TABLES: tuple[tuple[str, str], ...] = (
    ("ai", "ai_actions"), ("ai", "insights"),
    ("execution", "decisions"), ("execution", "initiatives"), ("execution", "key_results"),
    ("execution", "kpi_targets"), ("execution", "kpis"), ("execution", "meeting_transcripts"),
    ("execution", "meetings"), ("execution", "milestones"), ("execution", "objectives"),
    ("execution", "projects"), ("execution", "tasks"),
    ("finance", "budgets"), ("finance", "cash_flow_forecast_lines"),
    ("finance", "cash_flow_forecasts"), ("finance", "cash_positions"), ("finance", "expenses"),
    ("finance", "forecast_lines"), ("finance", "forecasts"), ("finance", "invoice_lines"),
    ("finance", "invoices"), ("finance", "revenues"),
    ("hr", "departments"), ("hr", "employee_skills"), ("hr", "employees"), ("hr", "hiring_plans"),
    ("hr", "leaves"), ("hr", "positions"), ("hr", "teams"),
    ("idp", "extracted_fields"), ("idp", "source_documents"),
    ("platform", "alerts"), ("platform", "approval_requests"), ("platform", "metric_values"),
    ("platform", "reports"),
    ("product", "features"), ("product", "products"), ("product", "releases"),
    ("product", "roadmap_items"),
    ("risk", "mitigations"), ("risk", "risks"), ("risk", "scenarios"),
    ("sales", "clients"), ("sales", "contracts"), ("sales", "deals"), ("sales", "sales_targets"),
)  # fmt: skip

# Columns typed auth.role_code (scalar) and the ARRAY ones.
ROLE_COLS_SCALAR: tuple[tuple[str, str, str], ...] = (
    ("auth", "roles", "code"),
    ("ai", "autonomy_policies", "role_code"),
    ("ai", "conversations", "role_code"),
    ("idp", "extraction_reviews", "reviewer_role"),
    ("idp", "review_assignments", "to_role_code"),
    ("platform", "approval_rules", "escalate_to_role_code"),
    ("platform", "audit_logs", "actor_role"),
)
ROLE_COLS_ARRAY: tuple[tuple[str, str, str], ...] = (
    ("ai", "insights", "audience_roles"),
    ("platform", "approval_rules", "approver_role_codes"),
    ("platform", "approval_rules", "second_approver_role_codes"),
)

V3_VALUES = ("CEO", "DIR", "MGR", "EMP", "REV", "ADM", "AI")
V21_VALUES = (
    "CEO", "CFO", "VP_SALES", "HR_MANAGER", "REVIEWER", "CPO", "RISK_MANAGER", "MANAGER",
    "EMPLOYEE", "ADMIN",
)  # fmt: skip

# 10→7 (R-DEC-12) and a best-effort 7→10 inverse for downgrade (DIR→CFO by default).
MAP_10_TO_7 = {
    "CEO": "CEO", "CFO": "DIR", "VP_SALES": "DIR", "HR_MANAGER": "DIR", "CPO": "DIR",
    "RISK_MANAGER": "DIR", "MANAGER": "MGR", "EMPLOYEE": "EMP", "REVIEWER": "REV", "ADMIN": "ADM",
}
MAP_7_TO_10 = {
    "CEO": "CEO", "DIR": "CFO", "MGR": "MANAGER", "EMP": "EMPLOYEE", "REV": "REVIEWER",
    "ADM": "ADMIN", "AI": "ADMIN",  # AI không tồn tại ở v2.1 → gần nhất ADMIN (chỉ cho downgrade)
}


def _case_sql(col: str, mapping: dict[str, str], target_type: str) -> str:
    whens = " ".join(f"WHEN '{k}' THEN '{v}'::{target_type}" for k, v in mapping.items())
    return f"CASE {col}::text {whens} ELSE NULL END"


def _swap_enum(old: str, new: str, mapping: dict[str, str], new_values: tuple[str, ...]) -> None:
    """Create `new` enum, convert every role_code column via CASE, drop `old`, rename new→old."""
    tmp = f"auth.{new}"
    vals = ", ".join(f"'{v}'" for v in new_values)
    op.execute(f"CREATE TYPE {tmp} AS ENUM ({vals})")
    for schema, table, col in ROLE_COLS_SCALAR:
        expr = _case_sql(col, mapping, tmp)
        op.execute(
            f'ALTER TABLE "{schema}"."{table}" '
            f'ALTER COLUMN "{col}" TYPE {tmp} USING ({expr})'
        )
    for schema, table, col in ROLE_COLS_ARRAY:
        # Remap each element without a subquery: cast to text[], chain array_replace, cast to new[].
        expr = f'"{col}"::text[]'
        for old_v, new_v in mapping.items():
            if old_v != new_v:
                expr = f"array_replace({expr}, '{old_v}', '{new_v}')"
        op.execute(
            f'ALTER TABLE "{schema}"."{table}" '
            f'ALTER COLUMN "{col}" TYPE {tmp}[] USING ({expr}::{tmp}[])'
        )
    op.execute(f"DROP TYPE auth.{old}")
    op.execute(f"ALTER TYPE {tmp} RENAME TO {old}")


def upgrade() -> None:
    # 1) tenant_id on business tables (server_default backfills existing rows).
    for schema, table in BUSINESS_TABLES:
        op.add_column(
            table,
            sa.Column(
                "tenant_id",
                sa.dialects.postgresql.UUID(as_uuid=True),
                nullable=False,
                server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"),
            ),
            schema=schema,
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"], schema=schema)

    # 2) auth.users.scope_pillars.
    op.add_column(
        "users",
        sa.Column(
            "scope_pillars",
            sa.ARRAY(sa.dialects.postgresql.ENUM(name="pillar", schema="platform", create_type=False)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        schema="auth",
    )

    # 3) Collapse auth.roles 5 C-level → 1 DIR before the enum loses those values.
    #    Repoint users to the surviving DIR row; set scope_pillars from the old role.
    op.execute(
        """
        WITH keep AS (
            SELECT id FROM auth.roles WHERE code = 'CFO' LIMIT 1
        )
        UPDATE auth.users u SET
            scope_pillars = CASE r.code
                WHEN 'CFO' THEN ARRAY['F']::platform.pillar[]
                WHEN 'VP_SALES' THEN ARRAY['C']::platform.pillar[]
                WHEN 'HR_MANAGER' THEN ARRAY['O']::platform.pillar[]
                WHEN 'CPO' THEN ARRAY['U']::platform.pillar[]
                WHEN 'RISK_MANAGER' THEN ARRAY['S']::platform.pillar[]
                ELSE u.scope_pillars END,
            role_id = (SELECT id FROM keep)
        FROM auth.roles r
        WHERE u.role_id = r.id
          AND r.code IN ('CFO','VP_SALES','HR_MANAGER','CPO','RISK_MANAGER')
        """
    )
    # Remove the 4 now-unused C-level rows (CFO row becomes DIR below).
    op.execute(
        "DELETE FROM auth.roles WHERE code IN ('VP_SALES','HR_MANAGER','CPO','RISK_MANAGER')"
    )

    # 4) Swap the enum 10→7 (remaps every role_code column, incl. the surviving CFO row → DIR).
    _swap_enum("role_code", "role_code_v3", MAP_10_TO_7, V3_VALUES)


def downgrade() -> None:
    # 4') Swap enum 7→10 first (DIR→CFO etc.).
    _swap_enum("role_code", "role_code_v21", MAP_7_TO_10, V21_VALUES)

    # 3') scope_pillars no longer meaningful for role split; drop it.
    op.drop_column("users", "scope_pillars", schema="auth")

    # 1') drop tenant_id + its index.
    for schema, table in BUSINESS_TABLES:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table, schema=schema)
        op.drop_column(table, "tenant_id", schema=schema)

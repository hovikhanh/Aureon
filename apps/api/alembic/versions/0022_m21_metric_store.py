"""M2.1 Metric Store: SEI code rename + user_preferences (03 §4, R-DEC-83/87).

Revision ID: 0022_m21_metric_store
Revises: 0021_ai_platform_m16
Create Date: 2026-10-31

- T-701: Strategy Execution Index đổi mã `METRIC-RSK-06` → `METRIC-STR-02` (nhóm STR,
  R-DEC-83). Data-only UPDATE trên `platform.metrics.code` + `alert_code`; `metric_values`
  liên kết qua `metric_id` (FK) nên không mất giá trị. Downgrade đổi ngược.
- T-704: `platform.user_preferences(tenant_id, user_id, key, value_json)` (ConfigModel +
  TenantMixin, 05 §2.1 config group) unique `(tenant_id, user_id, key)` (R-DEC-87);
  `user_id` là soft reference tới `auth.users` (C7, không FK chéo schema). Lưu 4 ô Executive
  (`dashboard.executive_tiles`). `version` cho optimistic concurrency EP-RPT-05.

Reversible: downgrade khôi phục mã SEI cũ + drop bảng user_preferences.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022_m21_metric_store"
down_revision: str | None = "0021_ai_platform_m16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
S = "platform"
P = "user_preferences"


def _tenant() -> sa.Column[sa.Uuid]:
    return sa.Column(
        "tenant_id", sa.UUID(), server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"), nullable=False
    )


def _ts(name: str) -> sa.Column[sa.DateTime]:
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def _rename_metric(from_code: str, to_code: str) -> None:
    op.execute(
        sa.text(
            f"UPDATE {S}.metrics SET code = :to_code, "  # noqa: S608 — static schema/table
            f"alert_code = replace(:to_code, 'METRIC-', 'ALERT-') "
            f"WHERE code = :from_code"
        ).bindparams(to_code=to_code, from_code=from_code)
    )


def upgrade() -> None:
    # T-701 — SEI → STR-02 (data-only; safe if the row is absent, e.g. not yet seeded)
    _rename_metric("METRIC-RSK-06", "METRIC-STR-02")

    # T-704 — user_preferences
    op.create_table(
        P,
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        _tenant(),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "data_classification",
            postgresql.ENUM(name="data_classification", schema=S, create_type=False),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{P}")),
        sa.UniqueConstraint("tenant_id", "user_id", "key", name=f"uq_{P}_tenant_user_key"),
        schema=S,
    )
    op.create_index(op.f(f"ix_{P}_tenant_id"), P, ["tenant_id"], schema=S)


def downgrade() -> None:
    op.drop_index(op.f(f"ix_{P}_tenant_id"), table_name=P, schema=S)
    op.drop_table(P, schema=S)
    _rename_metric("METRIC-STR-02", "METRIC-RSK-06")

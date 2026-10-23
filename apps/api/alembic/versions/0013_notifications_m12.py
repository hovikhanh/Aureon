"""M1.2 T-616: notifications tenant + email status, notification_preferences (05 §2.4).

Revision ID: 0013_notifications_m12
Revises: 0012_employee_assignments
Create Date: 2026-10-23

- `platform.email_status` enum (NOT_REQUIRED/PENDING/SENT/FAILED, R-DEC-33).
- `platform.notifications` + `tenant_id` (backfilled with the system tenant via server default),
  `email_status`, `email_sent_at`, `email_attempts`; index `(email_status, created_at)`.
- `platform.notification_preferences(user_id, kind, email_enabled)` (config group 05 §2.1) unique `(user_id, kind)`
  (R-DEC-32); `user_id` is a soft reference to `auth.users` (C7, no cross-schema FK).

Reversible: downgrade drops the new table, columns and enum.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_notifications_m12"
down_revision: str | None = "0012_employee_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
S = "platform"
N = "notifications"
P = "notification_preferences"
EMAIL_STATUS = ("NOT_REQUIRED", "PENDING", "SENT", "FAILED")
KIND = postgresql.ENUM(name="notification_kind", schema=S, create_type=False)


def _tenant() -> sa.Column[sa.UUID]:
    return sa.Column(
        "tenant_id", sa.UUID(), server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"), nullable=False
    )


def _ts(name: str) -> sa.Column[sa.DateTime]:
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def upgrade() -> None:
    status = postgresql.ENUM(*EMAIL_STATUS, name="email_status", schema=S)
    status.create(op.get_bind(), checkfirst=True)
    op.add_column(N, _tenant(), schema=S)
    op.add_column(
        N,
        sa.Column(
            "email_status",
            postgresql.ENUM(name="email_status", schema=S, create_type=False),
            server_default=sa.text("'NOT_REQUIRED'"),
            nullable=False,
        ),
        schema=S,
    )
    op.add_column(N, sa.Column("email_sent_at", sa.DateTime(timezone=True)), schema=S)
    op.add_column(
        N,
        sa.Column("email_attempts", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        schema=S,
    )
    op.create_index(op.f(f"ix_{N}_tenant_id"), N, ["tenant_id"], schema=S)
    op.create_index(f"ix_{N}_email_status_created_at", N, ["email_status", "created_at"], schema=S)

    op.create_table(
        P,
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        _tenant(),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("kind", KIND, nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False),
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
        sa.UniqueConstraint("user_id", "kind", name=f"uq_{P}_user_id_kind"),
        schema=S,
    )
    op.create_index(op.f(f"ix_{P}_tenant_id"), P, ["tenant_id"], schema=S)
    op.create_index(op.f(f"ix_{P}_user_id"), P, ["user_id"], schema=S)


def downgrade() -> None:
    op.drop_table(P, schema=S)
    op.drop_index(f"ix_{N}_email_status_created_at", table_name=N, schema=S)
    op.drop_index(op.f(f"ix_{N}_tenant_id"), table_name=N, schema=S)
    for col in ("email_attempts", "email_sent_at", "email_status", "tenant_id"):
        op.drop_column(N, col, schema=S)
    postgresql.ENUM(name="email_status", schema=S).drop(op.get_bind(), checkfirst=True)

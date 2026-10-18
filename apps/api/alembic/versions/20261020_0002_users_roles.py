"""ENT-Role (`roles`) + ENT-User (`users`) with enums `pillar`, `role_key` (T-101; 05 §4.1-4.2, §6).

Revision ID: 0002_users_roles
Revises: 0001_baseline
Create Date: 2026-10-20

Every migration must be reversible (05 §12 G2): implement both upgrade() and downgrade().
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_users_roles"
down_revision: str | Sequence[str] | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enum types are created/dropped explicitly (autogenerate misses them — 05 §12 G2).
pillar = postgresql.ENUM("FIN", "CUS", "OPS", "HR", name="pillar", create_type=False)
role_key = postgresql.ENUM(
    "CEO", "CFO", "SALES_DIRECTOR", "HR_MANAGER", "REVIEWER", name="role_key", create_type=False
)


def _common_columns() -> list[sa.Column[object]]:
    """05 §1 C3-C5: id, created_at, updated_at, deleted_at."""
    return [
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    pillar.create(bind, checkfirst=False)
    role_key.create(bind, checkfirst=False)

    op.create_table(
        "roles",
        *_common_columns(),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("key", role_key, nullable=False),
        sa.Column("name_i18n_key", sa.Text(), nullable=False),
        sa.Column("pillar_scope", postgresql.ARRAY(pillar), nullable=False),
        sa.Column("pillar_agg_scope", postgresql.ARRAY(pillar), nullable=False),
        sa.Column("review_pillars", postgresql.ARRAY(pillar), nullable=False),
        sa.Column("can_view_salary", sa.Boolean(), nullable=False),
        sa.Column("home_route", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("code", name=op.f("uq_roles_code")),
        sa.UniqueConstraint("key", name=op.f("uq_roles_key")),
    )

    op.create_table(
        "users",
        *_common_columns(),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("salutation", sa.Text(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("is_demo_account", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("email = lower(email)", name=op.f("ck_users_email_lowercase")),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_users_role_id_roles"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_role_id"), "users", ["role_id"], unique=False)
    # 05 §4.1: email unique among live rows only (partial, soft delete).
    op.create_index(
        "uq_users_email",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_users_email",
        table_name="users",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_users_role_id"), table_name="users")
    op.drop_table("users")
    op.drop_table("roles")
    bind = op.get_bind()
    role_key.drop(bind, checkfirst=False)
    pillar.drop(bind, checkfirst=False)

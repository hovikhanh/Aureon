"""ENT-AuditLog (`audit_logs`) + enum `actor_type` + append-only trigger (T-102; 05 §4.12, §12 G1).

Revision ID: 0003_audit_logs
Revises: 0002_users_roles
Create Date: 2026-10-20

`source_document_id` FK → source_documents is added by T-201 together with that table.

Every migration must be reversible (05 §12 G2): implement both upgrade() and downgrade().
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_audit_logs"
down_revision: str | Sequence[str] | None = "0002_users_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

actor_type = postgresql.ENUM("USER", "AI", "SYSTEM", name="actor_type", create_type=False)

# 05 §4.12: append-only — DB trigger rejects every UPDATE / DELETE on audit_logs.
# SQLSTATE 55000 = object_not_in_prerequisite_state; message names the table for debugging.
_APPEND_ONLY_FUNCTION = """
CREATE FUNCTION audit_logs_append_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only: % is not allowed', TG_OP
        USING ERRCODE = '55000';
END;
$$
"""
_APPEND_ONLY_TRIGGER = """
CREATE TRIGGER trg_audit_logs_append_only
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION audit_logs_append_only()
"""


def upgrade() -> None:
    actor_type.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("actor_type", actor_type, nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("actor_role_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column("source_document_id", sa.UUID(), nullable=True),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_audit_logs_actor_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_role_id"],
            ["roles.id"],
            name=op.f("fk_audit_logs_actor_role_id_roles"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_actor_user_id"), "audit_logs", ["actor_user_id"])
    op.create_index(op.f("ix_audit_logs_actor_role_id"), "audit_logs", ["actor_role_id"])
    op.create_index(op.f("ix_audit_logs_source_document_id"), "audit_logs", ["source_document_id"])
    op.create_index(op.f("ix_audit_logs_occurred_at"), "audit_logs", ["occurred_at"])
    op.create_index(
        "ix_audit_logs_target_type_target_id", "audit_logs", ["target_type", "target_id"]
    )

    op.execute(_APPEND_ONLY_FUNCTION)
    op.execute(_APPEND_ONLY_TRIGGER)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_append_only ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS audit_logs_append_only()")
    op.drop_index("ix_audit_logs_target_type_target_id", table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_occurred_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_source_document_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_role_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
    actor_type.drop(op.get_bind(), checkfirst=False)

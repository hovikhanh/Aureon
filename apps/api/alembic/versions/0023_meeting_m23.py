"""M2.3 D12 Meeting transcript → việc: meeting_summaries + action_items (05 §2.9, R-DEC-100).

Revision ID: 0023_meeting_m23
Revises: 0022_m21_metric_store
Create Date: 2026-10-31

- T-720: ENT-MeetingSummary (`execution.meeting_summaries`, 1-1 Meeting) + ENT-ActionItem
  (`execution.action_items`). Enum mới `summary_origin`, `name_match_status` (schema execution).
  BusinessModel: id/tenant_id/created_at/updated_at/deleted_at/created_by/updated_by/version/
  data_classification. FK cùng schema execution (meetings/decisions/tasks); soft ref (owner_id,
  source_document_id, model_call_id) không FK chéo schema (C7).

Reversible: downgrade drop 2 bảng + 2 enum.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023_meeting_m23"
down_revision: str | Sequence[str] | None = "0022_m21_metric_store"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
S = "execution"


def _tenant() -> sa.Column[sa.Uuid]:
    return sa.Column(
        "tenant_id", sa.UUID(), server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"), nullable=False
    )


def _ts(name: str) -> sa.Column[sa.DateTime]:
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def _common() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        _tenant(),
        _ts("created_at"),
        _ts("updated_at"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "data_classification",
            postgresql.ENUM(name="data_classification", schema="platform", create_type=False),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.Column(
            "source",
            postgresql.ENUM(name="record_source", schema="platform", create_type=False),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    summary_origin = postgresql.ENUM("ai", "human", name="summary_origin", schema=S)
    match_status = postgresql.ENUM(
        "matched", "ambiguous", "unmatched", name="name_match_status", schema=S
    )
    summary_origin.create(op.get_bind(), checkfirst=True)
    match_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "meeting_summaries",
        *_common(),
        sa.Column("meeting_id", sa.UUID(), nullable=False),
        sa.Column("source_document_id", sa.UUID(), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column(
            "key_points", postgresql.JSONB(), server_default=sa.text("'[]'"), nullable=False
        ),
        sa.Column(
            "generated_by",
            postgresql.ENUM(name="summary_origin", schema=S, create_type=False),
            nullable=False,
        ),
        sa.Column("model_call_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'draft'"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meeting_summaries")),
        sa.ForeignKeyConstraint(
            ["meeting_id"], [f"{S}.meetings.id"],
            name=op.f("fk_meeting_summaries_meeting_id_meetings"), ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("meeting_id", name="uq_meeting_summaries_meeting_id"),
        schema=S,
    )  # fmt: skip
    op.create_index("ix_meeting_summaries_tenant_id", "meeting_summaries", ["tenant_id"], schema=S)
    op.create_index(
        "ix_meeting_summaries_meeting_id", "meeting_summaries", ["meeting_id"], schema=S
    )
    op.create_index(
        "ix_meeting_summaries_source_document_id",
        "meeting_summaries", ["source_document_id"], schema=S,
    )  # fmt: skip
    op.create_index(
        "ix_meeting_summaries_model_call_id", "meeting_summaries", ["model_call_id"], schema=S
    )

    op.create_table(
        "action_items",
        *_common(),
        sa.Column("meeting_id", sa.UUID(), nullable=True),
        sa.Column("decision_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("owner_name_raw", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column(
            "match_status",
            postgresql.ENUM(name="name_match_status", schema=S, create_type=False),
            nullable=False,
        ),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("source_document_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'open'"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_action_items")),
        sa.ForeignKeyConstraint(
            ["meeting_id"], [f"{S}.meetings.id"],
            name=op.f("fk_action_items_meeting_id_meetings"), ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["decision_id"], [f"{S}.decisions.id"],
            name=op.f("fk_action_items_decision_id_decisions"), ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], [f"{S}.tasks.id"],
            name=op.f("fk_action_items_task_id_tasks"), ondelete="SET NULL",
        ),
        sa.UniqueConstraint("task_id", name="uq_action_items_task_id"),
        schema=S,
    )  # fmt: skip
    op.create_index("ix_action_items_tenant_id", "action_items", ["tenant_id"], schema=S)
    op.create_index("ix_action_items_meeting_id", "action_items", ["meeting_id"], schema=S)
    op.create_index("ix_action_items_decision_id", "action_items", ["decision_id"], schema=S)
    op.create_index("ix_action_items_owner_id", "action_items", ["owner_id"], schema=S)
    op.create_index("ix_action_items_task_id", "action_items", ["task_id"], schema=S)
    op.create_index(
        "ix_action_items_source_document_id", "action_items", ["source_document_id"], schema=S
    )


def downgrade() -> None:
    op.drop_table("action_items", schema=S)
    op.drop_table("meeting_summaries", schema=S)
    postgresql.ENUM(name="name_match_status", schema=S).drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="summary_origin", schema=S).drop(op.get_bind(), checkfirst=True)

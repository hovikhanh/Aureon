"""M3.3 D27 CEO Daily Briefing: ai.briefings snapshot entity (05 §2.11, R-DEC-131).

Revision ID: 0025_briefing_m33
Revises: 0024_calendar_m31
Create Date: 2026-11-02

- T-819: ENT-Briefing (`ai.briefings`) — one snapshot per (recipient_id, briefing_date)
  (UQ `uq_briefing_recipient_date` → idempotent beat job per user/day). `payload` JSONB snapshots
  `ExecutiveDashboardOut` + recommendations/calendar/stale (grounded numbers only, FR-AIQ-01);
  `opened_at` drives G1 tracking; email summary = `summary_line` only (no level-3/4, 02 §5.3).
  New enum `ai.briefing_status` (generated/opened). Soft ref `recipient_id` (no cross-schema FK, C7).

Reversible: downgrade drop 1 table + 1 enum.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025_briefing_m33"
down_revision: str | Sequence[str] | None = "0024_calendar_m31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
AI = "ai"
PLAT = "platform"


def _ts(name: str, *, nullable: bool = False) -> sa.Column[sa.DateTime]:
    default = sa.text("now()") if not nullable else None
    return sa.Column(name, sa.DateTime(timezone=True), server_default=default, nullable=nullable)


def _business() -> list[sa.Column]:
    """BusinessModel common columns (05 §2.1 group 1): id/tenant/ts/soft-delete/actor/C19."""
    return [
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "tenant_id", sa.UUID(), server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"), nullable=False
        ),
        _ts("created_at"),
        _ts("updated_at"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "data_classification",
            postgresql.ENUM(name="data_classification", schema=PLAT, create_type=False),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.Column(
            "source",
            postgresql.ENUM(name="record_source", schema=PLAT, create_type=False),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    status = postgresql.ENUM("generated", "opened", name="briefing_status", schema=AI)
    status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "briefings",
        *_business(),
        sa.Column("recipient_id", sa.UUID(), nullable=False),
        sa.Column("briefing_date", sa.Date(), nullable=False),
        _ts("generated_at"),
        sa.Column("summary_line", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "stale_metric_codes",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_email_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="briefing_status", schema=AI, create_type=False),
            server_default=sa.text("'generated'"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_briefings")),
        sa.UniqueConstraint("recipient_id", "briefing_date", name="uq_briefing_recipient_date"),
        schema=AI,
    )
    op.create_index("ix_briefings_tenant_id", "briefings", ["tenant_id"], schema=AI)
    op.create_index("ix_briefings_recipient_id", "briefings", ["recipient_id"], schema=AI)
    op.create_index("ix_briefings_briefing_date", "briefings", ["briefing_date"], schema=AI)


def downgrade() -> None:
    op.drop_index("ix_briefings_briefing_date", table_name="briefings", schema=AI)
    op.drop_index("ix_briefings_recipient_id", table_name="briefings", schema=AI)
    op.drop_index("ix_briefings_tenant_id", table_name="briefings", schema=AI)
    op.drop_table("briefings", schema=AI)
    postgresql.ENUM(name="briefing_status", schema=AI).drop(op.get_bind(), checkfirst=True)

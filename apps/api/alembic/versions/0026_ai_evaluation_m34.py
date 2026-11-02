"""M3.4 D26 Evaluation Engine: ai.ai_evaluations standard-suite runs (05 §2.12, R-DEC-138).

Revision ID: 0026_ai_evaluation_m34
Revises: 0025_briefing_m33
Create Date: 2026-11-02

- T-827: ENT-AIEvaluation (`ai.ai_evaluations`) — one row per standard-suite run scoring an agent
  prompt/model version on grounding (FR-AIQ-01) / accuracy / tool-choice over a fixture corpus
  (CI always `fixture`, no live LLM). `cases` JSONB keeps per-case pass/detail only (no raw
  prompt, no PII, §5.5). Soft ref `triggered_by` (no cross-schema FK, C7). No new enum.

Reversible: downgrade drop 1 table (+ its 2 indexes).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026_ai_evaluation_m34"
down_revision: str | Sequence[str] | None = "0025_briefing_m33"
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
    op.create_table(
        "ai_evaluations",
        *_business(),
        sa.Column("suite", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("gateway_mode", sa.Text(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Integer(), nullable=False),
        sa.Column("grounding_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("accuracy_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("tool_choice_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("score_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("cases", postgresql.JSONB(), nullable=False),
        _ts("started_at"),
        _ts("finished_at"),
        sa.Column("triggered_by", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_evaluations")),
        schema=AI,
    )
    op.create_index("ix_ai_evaluations_suite", "ai_evaluations", ["suite"], schema=AI)
    op.create_index("ix_ai_evaluations_finished_at", "ai_evaluations", ["finished_at"], schema=AI)


def downgrade() -> None:
    op.drop_index("ix_ai_evaluations_finished_at", table_name="ai_evaluations", schema=AI)
    op.drop_index("ix_ai_evaluations_suite", table_name="ai_evaluations", schema=AI)
    op.drop_table("ai_evaluations", schema=AI)

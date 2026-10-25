"""M1.5 T-639: `platform.dq_domain_scores` — DQ score per domain per month (R-DEC-68).

Revision ID: 0020_capture_dq
Revises: 0019_capture_seed_doctypes
Create Date: 2026-10-24

05 §2.7 ENT-DQDomainScore: LogModel + `tenant_id`; unique `(tenant_id, domain, period_key)`;
`completeness/accuracy/freshness/score` numeric(5,2) CHECK 0..100; `rows`; `computed_at`.
Downgrade drops the table (scores are recomputed by the next metric run).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_capture_dq"
down_revision: str | None = "0019_capture_seed_doctypes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
S, T = "platform", "dq_domain_scores"
SCORES = ("completeness", "accuracy", "freshness", "score")


def upgrade() -> None:
    op.create_table(
        T,
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                  nullable=False),
        sa.Column("tenant_id", sa.UUID(), server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"),
                  nullable=False),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("period_key", sa.Text(), nullable=False),
        *[sa.Column(c, sa.Numeric(5, 2), nullable=False) for c in SCORES],
        sa.Column("rows", sa.Integer(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        *[sa.CheckConstraint(f"{c} BETWEEN 0 AND 100", name=op.f(f"ck_{T}_{c}_range"))
          for c in SCORES],
        sa.CheckConstraint("rows >= 0", name=op.f(f"ck_{T}_rows_nonneg")),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{T}")),
        schema=S,
    )  # fmt: skip
    op.create_index(op.f(f"ix_{T}_tenant_id"), T, ["tenant_id"], schema=S)
    op.create_index("uq_dq_domain_scores_tenant_domain_period", T,
                    ["tenant_id", "domain", "period_key"], unique=True, schema=S)  # fmt: skip


def downgrade() -> None:
    op.drop_table(T, schema=S)

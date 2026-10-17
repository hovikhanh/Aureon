"""Baseline: enable pgcrypto + vector extensions (T-004; 05 §11, §12 G1; 07 docker services).

Entity tables, enum types and the audit_logs trigger from 05 §12 G1 are added by later
tasks (T-101, T-102, T-201, T-301) as follow-up revisions.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pgcrypto: gen_random_uuid() server default (05 §1 C3; built-in on PG13+, kept per G1).
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    # vector: pgvector 0.7+, extension only — no vector columns in MVP (05 §11, OQ-06).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")

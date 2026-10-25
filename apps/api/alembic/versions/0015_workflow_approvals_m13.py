"""M1.3 T-622: approval_requests `target_kind` + `department_id` (05 §2.5, R-DEC-45).

Revision ID: 0015_workflow_approvals_m13
Revises: 0014_work_tasks_m13
Create Date: 2026-10-24

- `platform.approval_requests.target_kind` text NOT NULL — backfilled from the rule's
  `approval_rules.target_kind` (v2.1 rows = `ai_action`); the API stops returning a constant.
- `platform.approval_requests.department_id` UUID NULL (soft ref, no FK — cross-schema) for the
  MGR `d` inbox scope; backfill NULL (v2.1 AI actions are company-level).
- index `(tenant_id, status, department_id)`.
- `RULE-task_reassign` is created lazily by the service (like the finance rules) — no seed here.

Reversible: downgrade drops the index and both columns.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_workflow_approvals_m13"
down_revision: str | None = "0014_work_tasks_m13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "platform"
T = "approval_requests"


def upgrade() -> None:
    op.add_column(T, sa.Column("target_kind", sa.Text(), nullable=True), schema=S)
    op.execute(
        "UPDATE platform.approval_requests q SET target_kind = r.target_kind "
        "FROM platform.approval_rules r WHERE r.id = q.rule_id"
    )
    op.alter_column(T, "target_kind", nullable=False, schema=S)
    op.add_column(
        T, sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True), schema=S
    )
    op.create_index(
        "ix_approval_requests_tenant_id_status_department_id",
        T,
        ["tenant_id", "status", "department_id"],
        schema=S,
    )


def downgrade() -> None:
    op.drop_index("ix_approval_requests_tenant_id_status_department_id", T, schema=S)
    op.drop_column(T, "department_id", schema=S)
    op.drop_column(T, "target_kind", schema=S)

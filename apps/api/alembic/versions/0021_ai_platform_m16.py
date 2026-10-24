"""M1.6 AI Platform nền (05 §2.8): tool kind + audit columns + agent/policy tenant.

Revision ID: 0021_ai_platform_m16
Revises: 0020_capture_dq
Create Date: 2026-10-24

T-644 part: enum `ai.tool_kind` (READ/WRITE/APPROVAL/EXECUTION) + `tool_call_logs.tool_kind`
NOT NULL, backfilled from the registry (`TOOL-*` → kind; unknown → `READ`).
Reversible: downgrade drops the column and the type.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_ai_platform_m16"
down_revision: str | None = "0020_capture_dq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

S = "ai"
TOOL_KINDS = ("READ", "WRITE", "APPROVAL", "EXECUTION")
# Snapshot of the registry kinds at 0021 (migrations must not import app code). Tools not
# listed (v2.1 READ/COMPUTE, unknown names) backfill as READ.
NON_READ_TOOLS: dict[str, str] = {
    **{f"TOOL-{n}": "WRITE" for n in (
        "create_task", "record_decision", "create_meeting", "record_kpi_measurement",
        "record_expense", "create_invoice", "upsert_deal", "upsert_risk", "create_mitigation",
        "submit_document", "assign_task", "generate_report", "request_approval",
        "update_task", "record_kr_checkin", "upsert_kpi", "upsert_objective",
        "create_department", "create_team",
    )},
    "TOOL-send_notification": "EXECUTION",
    "TOOL-approve_request": "APPROVAL",
    "TOOL-reject_request": "APPROVAL",
}  # fmt: skip


def _tool_kind() -> postgresql.ENUM:
    return postgresql.ENUM(*TOOL_KINDS, name="tool_kind", schema=S, create_type=False)


def upgrade() -> None:
    postgresql.ENUM(*TOOL_KINDS, name="tool_kind", schema=S).create(op.get_bind())
    op.add_column("tool_call_logs", sa.Column("tool_kind", _tool_kind(), nullable=True), schema=S)
    for name, kind in NON_READ_TOOLS.items():
        op.execute(
            sa.text("UPDATE ai.tool_call_logs SET tool_kind = CAST(:k AS ai.tool_kind) "
                    "WHERE tool_name = :n").bindparams(k=kind, n=name)
        )  # fmt: skip
    op.execute("UPDATE ai.tool_call_logs SET tool_kind = 'READ' WHERE tool_kind IS NULL")
    op.alter_column("tool_call_logs", "tool_kind", nullable=False, schema=S)


def downgrade() -> None:
    op.drop_column("tool_call_logs", "tool_kind", schema=S)
    postgresql.ENUM(name="tool_kind", schema=S).drop(op.get_bind())

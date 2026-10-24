"""M1.6 AI Platform nền (05 §2.8): tool kind + audit columns + agent/policy tenant.

Revision ID: 0021_ai_platform_m16
Revises: 0020_capture_dq
Create Date: 2026-10-24

* T-644: enum `ai.tool_kind` (READ/WRITE/APPROVAL/EXECUTION) + `tool_call_logs.tool_kind`
  NOT NULL, backfilled from the registry (`TOOL-*` → kind; unknown → `READ`).
* T-647: `tool_call_logs` + tenant_id, request_id, user_id, ai_action_id (FK RESTRICT),
  error_code, result_refs; `message_id` nullable (R-DEC-74).
* T-646: `model_call_logs` + `tenant_id`, `request_id`, `agent_profile_code` (per-agent
  spend). `agent_profiles` + `agent_ref` (unique), `description_vi/en`, `tenant_id`; unique
  `code` → `(tenant_id, code)`. `autonomy_policies` + `tool_name` (backfill from `action_name`),
  `agent_profile_code`, `reason`, `tenant_id`; unique NULLS NOT DISTINCT on
  `(tenant_id, action_name, agent_profile_code, role_code, max_amount)` live rows; CHECK
  `level <= max_level` (enum order L0 < L1 < L2 < L3).
Reversible: downgrade drops the new columns/constraints and restores the v2.1 ones.
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
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
UQ_POLICY = "uq_autonomy_policies_tenant_action_agent_role_amount"
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
    _upgrade_agents()
    _upgrade_policies()
    _upgrade_model_calls()
    _upgrade_tool_calls()


def _tenant_col() -> sa.Column[sa.UUID]:
    return sa.Column("tenant_id", sa.UUID(), server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"),
                     nullable=False)  # fmt: skip


def _upgrade_agents() -> None:
    t = "agent_profiles"
    op.add_column(t, _tenant_col(), schema=S)
    op.add_column(t, sa.Column("agent_ref", sa.Text(), nullable=True), schema=S)
    op.add_column(t, sa.Column("description_vi", sa.Text(), nullable=False,
                               server_default=""), schema=S)  # fmt: skip
    op.add_column(t, sa.Column("description_en", sa.Text(), nullable=False,
                               server_default=""), schema=S)  # fmt: skip
    op.execute("UPDATE ai.agent_profiles SET agent_ref = 'AGT-' || upper(code)")
    op.alter_column(t, "agent_ref", nullable=False, schema=S)
    op.create_index(op.f(f"ix_{t}_tenant_id"), t, ["tenant_id"], schema=S)
    op.create_unique_constraint(op.f(f"uq_{t}_agent_ref"), t, ["agent_ref"], schema=S)
    op.drop_constraint("uq_agent_profiles_code", t, schema=S)
    op.create_unique_constraint("uq_agent_profiles_tenant_code", t, ["tenant_id", "code"],
                                schema=S)  # fmt: skip


def _upgrade_policies() -> None:
    t = "autonomy_policies"
    op.add_column(t, _tenant_col(), schema=S)
    op.add_column(t, sa.Column("tool_name", sa.Text(), nullable=True), schema=S)
    op.add_column(t, sa.Column("agent_profile_code", sa.Text(), nullable=True), schema=S)
    op.add_column(t, sa.Column("reason", sa.Text(), nullable=False, server_default=""), schema=S)
    op.execute("UPDATE ai.autonomy_policies SET tool_name = 'TOOL-' || substr(action_name, 5) "
               "WHERE action_name LIKE 'ACT-%'")  # fmt: skip
    op.execute("UPDATE ai.autonomy_policies SET tool_name = action_name WHERE tool_name IS NULL")
    op.alter_column(t, "tool_name", nullable=False, schema=S)
    op.create_index(op.f(f"ix_{t}_tenant_id"), t, ["tenant_id"], schema=S)
    op.create_index(op.f(f"ix_{t}_tool_name"), t, ["tool_name"], schema=S)
    op.drop_index("uq_autonomy_policies_action_role_amount", table_name=t, schema=S)
    op.create_index(
        UQ_POLICY, t, ["tenant_id", "action_name", "agent_profile_code", "role_code", "max_amount"],
        unique=True, postgresql_nulls_not_distinct=True,
        postgresql_where=sa.text("deleted_at IS NULL"), schema=S,
    )  # fmt: skip
    op.create_check_constraint(op.f(f"ck_{t}_level_le_max"), t, "level <= max_level", schema=S)


def _upgrade_model_calls() -> None:
    t = "model_call_logs"
    op.add_column(t, _tenant_col(), schema=S)
    op.add_column(t, sa.Column("request_id", sa.UUID(), nullable=True), schema=S)
    op.add_column(t, sa.Column("agent_profile_code", sa.Text(), nullable=True), schema=S)
    op.create_index(op.f(f"ix_{t}_tenant_created"), t,
                    ["tenant_id", sa.text("created_at DESC")], schema=S)  # fmt: skip
    op.create_index(op.f(f"ix_{t}_request_id"), t, ["request_id"], schema=S)
    op.create_index(op.f(f"ix_{t}_agent_profile_code"), t, ["agent_profile_code"], schema=S)


def _downgrade_model_calls() -> None:
    t = "model_call_logs"
    for ix in ("agent_profile_code", "request_id", "tenant_created"):
        op.drop_index(op.f(f"ix_{t}_{ix}"), table_name=t, schema=S)
    for c in ("agent_profile_code", "request_id", "tenant_id"):
        op.drop_column(t, c, schema=S)


def _upgrade_tool_calls() -> None:
    t = "tool_call_logs"
    op.add_column(t, _tenant_col(), schema=S)
    op.add_column(t, sa.Column("request_id", sa.UUID(), nullable=True), schema=S)
    op.add_column(t, sa.Column("user_id", sa.UUID(), nullable=True), schema=S)
    op.add_column(t, sa.Column("ai_action_id", sa.UUID(), nullable=True), schema=S)
    op.add_column(t, sa.Column("error_code", sa.Text(), nullable=True), schema=S)
    op.add_column(t, sa.Column("result_refs", postgresql.JSONB(), nullable=False,
                               server_default=sa.text("'[]'::jsonb")), schema=S)  # fmt: skip
    op.alter_column(t, "message_id", nullable=True, schema=S)
    op.create_foreign_key(op.f(f"fk_{t}_ai_action_id_ai_actions"), t, "ai_actions",
                          ["ai_action_id"], ["id"], source_schema=S, referent_schema=S,
                          ondelete="RESTRICT")  # fmt: skip
    op.create_index(op.f(f"ix_{t}_tenant_created"), t,
                    ["tenant_id", sa.text("created_at DESC")], schema=S)  # fmt: skip
    for c in ("request_id", "user_id", "ai_action_id"):
        op.create_index(op.f(f"ix_{t}_{c}"), t, [c], schema=S)
    # 05 §2.8 lists `ai_actions.request_id` as existing; the v2.1 table lacked it → add here.
    op.add_column("ai_actions", sa.Column("request_id", sa.UUID(), nullable=True), schema=S)
    op.create_index(op.f("ix_ai_actions_request_id"), "ai_actions", ["request_id"], schema=S)


def _downgrade_tool_calls() -> None:
    t = "tool_call_logs"
    op.drop_index(op.f("ix_ai_actions_request_id"), table_name="ai_actions", schema=S)
    op.drop_column("ai_actions", "request_id", schema=S)
    for ix in ("ai_action_id", "user_id", "request_id", "tenant_created"):
        op.drop_index(op.f(f"ix_{t}_{ix}"), table_name=t, schema=S)
    op.drop_constraint(op.f(f"fk_{t}_ai_action_id_ai_actions"), t, schema=S, type_="foreignkey")
    op.execute("DELETE FROM ai.tool_call_logs WHERE message_id IS NULL")
    op.alter_column(t, "message_id", nullable=False, schema=S)
    for c in ("result_refs", "error_code", "ai_action_id", "user_id", "request_id", "tenant_id"):
        op.drop_column(t, c, schema=S)


def downgrade() -> None:
    _downgrade_tool_calls()
    _downgrade_model_calls()
    t = "autonomy_policies"
    op.drop_constraint(op.f(f"ck_{t}_level_le_max"), t, type_="check", schema=S)
    op.drop_index(UQ_POLICY, table_name=t, schema=S)
    op.create_index(
        "uq_autonomy_policies_action_role_amount", t, ["action_name", "role_code", "max_amount"],
        unique=True, postgresql_nulls_not_distinct=True,
        postgresql_where=sa.text("deleted_at IS NULL"), schema=S,
    )  # fmt: skip
    op.drop_index(op.f(f"ix_{t}_tool_name"), table_name=t, schema=S)
    op.drop_index(op.f(f"ix_{t}_tenant_id"), table_name=t, schema=S)
    for c in ("reason", "agent_profile_code", "tool_name", "tenant_id"):
        op.drop_column(t, c, schema=S)
    t = "agent_profiles"
    op.drop_constraint("uq_agent_profiles_tenant_code", t, schema=S)
    op.create_unique_constraint("uq_agent_profiles_code", t, ["code"], schema=S)
    op.drop_constraint(op.f(f"uq_{t}_agent_ref"), t, schema=S)
    op.drop_index(op.f(f"ix_{t}_tenant_id"), table_name=t, schema=S)
    for c in ("description_en", "description_vi", "agent_ref", "tenant_id"):
        op.drop_column(t, c, schema=S)
    op.drop_column("tool_call_logs", "tool_kind", schema=S)
    postgresql.ENUM(name="tool_kind", schema=S).drop(op.get_bind())

"""Schema `ai` — 9 tables (05 §4.8). Column groups follow 05 §2.1.

- business: insights, ai_actions
- config:   autonomy_policies (+ soft delete — its UQ is `WHERE deleted_at IS NULL`),
            agent_profiles (no `deleted_at`; disable via `is_enabled`)
- log:      conversations (+ soft delete — "xóa hội thoại = xóa mềm ở conversations"),
            messages (no `deleted_at`), tool_call_logs, feedback, model_call_logs
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BusinessModel, ConfigModel, LogModel, SoftDeleteMixin
from app.core.columns import fk, money, schema_args, sr, txt
from app.core.enums import (
    ALERT_SEVERITY,
    AUTONOMY_LEVEL,
    CONFIDENCE_BAND,
    PILLAR,
    ROLE_CODE,
    pg_enum,
)

S = "ai"
TS = DateTime(timezone=True)

# ---------- enums owned by `ai` (05 §6; ai.autonomy_level lives in core/enums.py) ----------
MESSAGE_SENDER = pg_enum(S, "message_sender", "user", "assistant", "system")
TOOL_CALL_STATUS = pg_enum(S, "tool_call_status", "ok", "error", "forbidden", "timeout")
FEEDBACK_RATING = pg_enum(S, "feedback_rating", "up", "down")
INSIGHT_KIND = pg_enum(S, "insight_kind", "anomaly", "trend", "risk", "recommendation", "briefing")
INSIGHT_STATUS = pg_enum(S, "insight_status", "active", "dismissed", "expired")
AI_ACTION_STATUS = pg_enum(
    S, "ai_action_status", "proposed", "confirmed", "executed", "rejected", "undone", "failed"
)

MODULE_ENUMS: tuple[ENUM, ...] = (
    MESSAGE_SENDER,
    TOOL_CALL_STATUS,
    FEEDBACK_RATING,
    INSIGHT_KIND,
    INSIGHT_STATUS,
    AI_ACTION_STATUS,
)


# ---------- config ----------
class AutonomyPolicy(ConfigModel, SoftDeleteMixin):
    """ENT-AutonomyPolicy — config + soft delete (spec UQ is partial on `deleted_at IS NULL`).

    "L4 cấm bằng CK": `ai.autonomy_level` has no L4 value, so the enum itself forbids it.
    `currency` is nullable per the 05 row (`max_amount / currency`, Null = Y).
    """

    __tablename__ = "autonomy_policies"
    __table_args__ = (
        # 05 writes the key as COALESCE(role_code::text,'*'), COALESCE(max_amount,-1); PG rejects
        # it (enum→text cast is not IMMUTABLE). NULLS NOT DISTINCT (PG15+) is the equivalent:
        # NULL role / NULL amount each act as one value. Proposed DEC, T-003 report.
        Index(
            "uq_autonomy_policies_action_role_amount",
            "action_name",
            "role_code",
            "max_amount",
            unique=True,
            postgresql_nulls_not_distinct=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": S},
    )

    action_name: Mapped[str] = txt()
    role_code: Mapped[str | None] = mapped_column(ROLE_CODE, nullable=True)
    max_amount: Mapped[int | None] = money(nullable=True)
    currency: Mapped[str | None] = mapped_column(CHAR(3), nullable=True)
    level: Mapped[str] = mapped_column(AUTONOMY_LEVEL, nullable=False)
    max_level: Mapped[str] = mapped_column(AUTONOMY_LEVEL, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class AgentProfile(ConfigModel):
    """ENT-AIAgentProfile — config, no `deleted_at` (disable = `is_enabled = false`)."""

    __tablename__ = "agent_profiles"
    __table_args__ = schema_args(S)

    code: Mapped[str] = txt(unique=True)
    name_vi: Mapped[str] = txt()
    name_en: Mapped[str] = txt()
    allowed_tools: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    max_autonomy_level: Mapped[str] = mapped_column(AUTONOMY_LEVEL, nullable=False)
    model_task: Mapped[str] = txt()
    prompt_version: Mapped[str | None] = txt(nullable=True)
    monthly_budget_usd: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


# ---------- append-only / log ----------
class Conversation(LogModel, SoftDeleteMixin):
    """ENT-Conversation — log group (05 §2.1) + soft delete (05 §4.8 note on messages)."""

    __tablename__ = "conversations"
    __table_args__ = schema_args(S)

    user_id: Mapped[uuid.UUID] = sr(nullable=False)
    role_code: Mapped[str] = mapped_column(ROLE_CODE, nullable=False)
    title: Mapped[str | None] = txt(nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class Message(LogModel):
    """ENT-Message — append-only, no `deleted_at`."""

    __tablename__ = "messages"
    __table_args__ = schema_args(S)

    conversation_id: Mapped[uuid.UUID] = fk(f"{S}.conversations.id")
    sender: Mapped[str] = mapped_column(MESSAGE_SENDER, nullable=False)
    content: Mapped[str] = txt()
    sources: Mapped[Any] = mapped_column(JSONB, nullable=False)
    function_calls: Mapped[Any] = mapped_column(JSONB, nullable=False)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ToolCallLog(LogModel):
    """ENT-ToolCallLog — append-only."""

    __tablename__ = "tool_call_logs"
    __table_args__ = schema_args(S)

    message_id: Mapped[uuid.UUID] = fk(f"{S}.messages.id")
    tool_name: Mapped[str] = txt()
    arguments: Mapped[Any] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(TOOL_CALL_STATUS, nullable=False)
    http_status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_profile_code: Mapped[str] = txt()
    autonomy_level: Mapped[str | None] = mapped_column(AUTONOMY_LEVEL, nullable=True)
    why: Mapped[str | None] = txt(nullable=True)
    approval_request_id: Mapped[uuid.UUID | None] = sr()


class Feedback(LogModel):
    """ENT-Feedback — append-only; CK "một trong hai bắt buộc" = at least one target."""

    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint("num_nonnulls(message_id, insight_id) >= 1", name="has_target"),
        {"schema": S},
    )

    message_id: Mapped[uuid.UUID | None] = fk(f"{S}.messages.id", nullable=True)
    insight_id: Mapped[uuid.UUID | None] = fk(f"{S}.insights.id", nullable=True)
    user_id: Mapped[uuid.UUID] = sr(nullable=False)
    rating: Mapped[str] = mapped_column(FEEDBACK_RATING, nullable=False)
    reason: Mapped[str | None] = txt(nullable=True)
    comment: Mapped[str | None] = txt(nullable=True)


class ModelCallLog(LogModel):
    """ENT-ModelCallLog — append-only; only `prompt_sha256`, never the raw prompt."""

    __tablename__ = "model_call_logs"
    __table_args__ = schema_args(S)

    caller_module: Mapped[str] = txt()
    task_kind: Mapped[str] = txt()
    provider: Mapped[str] = txt()
    model: Mapped[str] = txt()
    fallback_from: Mapped[str | None] = txt(nullable=True)
    message_id: Mapped[uuid.UUID | None] = fk(f"{S}.messages.id", nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()
    user_id: Mapped[uuid.UUID | None] = sr()
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost_micro_usd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(TOOL_CALL_STATUS, nullable=False)
    error_code: Mapped[str | None] = txt(nullable=True)
    prompt_sha256: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)


# ---------- business ----------
class Insight(BusinessModel):
    """ENT-Insight — business (C19).

    "≥ 1 nguồn" and "`structured` bắt buộc với kind ∈ (anomaly, risk, recommendation)" are not
    marked CK in 05 → enforced in the service layer, not as DB constraints.
    """

    __tablename__ = "insights"
    __table_args__ = schema_args(S)

    kind: Mapped[str] = mapped_column(INSIGHT_KIND, nullable=False)
    pillar: Mapped[str | None] = mapped_column(PILLAR, nullable=True)
    title: Mapped[str] = txt()
    body: Mapped[str] = txt()
    severity: Mapped[str | None] = mapped_column(ALERT_SEVERITY, nullable=True)
    confidence: Mapped[str] = mapped_column(CONFIDENCE_BAND, nullable=False)
    sources: Mapped[Any] = mapped_column(JSONB, nullable=False)
    structured: Mapped[Any] = mapped_column(JSONB, nullable=True)
    decision_id: Mapped[uuid.UUID | None] = sr()
    trigger_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    audience_roles: Mapped[list[str]] = mapped_column(ARRAY(ROLE_CODE), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    status: Mapped[str] = mapped_column(INSIGHT_STATUS, nullable=False)


class AIAction(BusinessModel):
    """ENT-AIAction — business (C19); feed source for SCR-17."""

    __tablename__ = "ai_actions"
    __table_args__ = (
        Index("ix_ai_actions_status_undo_deadline", "status", "undo_deadline"),
        {"schema": S},
    )

    action_name: Mapped[str] = txt()
    tool_name: Mapped[str | None] = txt(nullable=True)
    agent_profile_code: Mapped[str] = txt()
    autonomy_level: Mapped[str] = mapped_column(AUTONOMY_LEVEL, nullable=False)
    confidence: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=True)
    why: Mapped[str | None] = txt(nullable=True)
    approval_request_id: Mapped[uuid.UUID | None] = sr()
    status: Mapped[str] = mapped_column(AI_ACTION_STATUS, nullable=False)
    on_behalf_of: Mapped[uuid.UUID] = sr(nullable=False)
    message_id: Mapped[uuid.UUID | None] = fk(f"{S}.messages.id", nullable=True)
    insight_id: Mapped[uuid.UUID | None] = fk(f"{S}.insights.id", nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()
    input: Mapped[Any] = mapped_column(JSONB, nullable=False)
    result_refs: Mapped[Any] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[str] = txt(unique=True)
    executed_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    undo_deadline: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    undone_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    undone_by: Mapped[uuid.UUID | None] = sr()
    verification: Mapped[Any] = mapped_column(JSONB, nullable=True)

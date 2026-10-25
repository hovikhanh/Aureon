"""`ai` Pydantic schemas — EP-AI-01..23 contract (10 §7.2.5; v2.1 EP-110..119 kept)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# M1.6 AI Control Center schemas live in `admin.py` (self-contained, 10 §7.2.5).
from app.modules.ai.schemas.admin import (
    AgentPatchIn,
    AIAgentOut,
    AutonomyPolicyCreateIn,
    AutonomyPolicyOut,
    AutonomyPolicyPatchIn,
    ModelCallLogOut,
    PolicyDefaultOut,
    ToolCallLogOut,
    ToolOut,
)


class ChatContext(BaseModel):
    screen: str | None = None
    entity_ref: str | None = None
    metric_code: str | None = None
    period: str | None = None


class ChatRequestIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: uuid.UUID | None = None
    context: ChatContext | None = None
    locale: Literal["vi", "en"] = "vi"


class SourceRefOut(BaseModel):
    type: Literal["metric_value", "record", "document_page", "tool_result"]
    id: str
    label: str
    period_key: str | None = None
    value: float | int | None = None
    lineage_url: str | None = None


class FunctionCallOut(BaseModel):
    tool: str
    status: Literal["ok", "error", "forbidden", "timeout"]
    latency_ms: int


class ChatAnswerOut(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    sources: list[SourceRefOut] = Field(default_factory=list)
    function_calls: list[FunctionCallOut] = Field(default_factory=list)
    suggested_actions: list[dict[str, Any]] = Field(default_factory=list)
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str | None
    last_message_at: datetime | None


class MessageOut(BaseModel):
    id: uuid.UUID
    sender: Literal["user", "assistant", "system"]
    content: str
    sources: list[SourceRefOut] = Field(default_factory=list)
    function_calls: list[FunctionCallOut] = Field(default_factory=list)
    truncated: bool = False
    created_at: datetime


class AIActionOut(BaseModel):
    """EP-115/116 AIActionOut (10 §4.11)."""

    id: uuid.UUID
    action_name: str
    tool_name: str | None = None
    autonomy_level: Literal["L0", "L1", "L2", "L3"]
    status: Literal["proposed", "confirmed", "executed", "rejected", "undone", "failed"]
    input_preview: dict[str, Any] = Field(default_factory=dict)
    result_refs: list[dict[str, Any]] = Field(default_factory=list)
    on_behalf_of: uuid.UUID
    approval_request_id: uuid.UUID | None = None
    executed_at: datetime | None = None
    undo_deadline: datetime | None = None
    can_undo: bool = False
    # M1.6 (EP-AI-08, 10 §7.2.5) — additive only
    agent_profile_code: str | None = None
    request_id: str | None = None
    created_at: datetime | None = None


class ConfirmActionIn(BaseModel):
    edited_input: dict[str, Any] | None = None


class RejectActionIn(BaseModel):
    reason: str


class UndoActionIn(BaseModel):
    reason: str | None = None


class KillSwitchOut(BaseModel):
    enabled: bool
    mode: Literal["WRITE_OFF", "L0"]
    agents: list[str] = Field(default_factory=list)
    changed_by: uuid.UUID | None = None
    changed_at: datetime | None = None
    # M1.6 (EP-AI-12, R-DEC-72) — additive only
    autonomy_ceiling: Literal["L0", "L1", "L2", "L3"] = "L2"
    reason: str | None = None


class KillSwitchIn(BaseModel):
    enabled: bool
    mode: Literal["WRITE_OFF", "L0"] = "WRITE_OFF"
    agents: list[str] = Field(default_factory=list)
    reason: str


class ConfidenceOut(BaseModel):
    band: Literal["high", "medium", "low"]
    reason: str


class RecommendationOut(BaseModel):
    text: str
    action: dict[str, Any] | None = None


class InsightOut(BaseModel):
    id: uuid.UUID
    kind: Literal["anomaly", "trend", "risk", "recommendation", "briefing"]
    pillar: str | None
    severity: Literal["info", "warning", "critical"] | None
    observation: str
    evidence: list[SourceRefOut] = Field(default_factory=list)
    impact: str | None = None
    recommendations: list[RecommendationOut] = Field(default_factory=list)
    confidence: ConfidenceOut
    structured: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    expires_at: datetime | None = None


class CostRowOut(BaseModel):
    key: str
    calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    error_rate: float
    p95_ms: int = 0


class CostSummaryOut(BaseModel):
    budget_usd: float
    used_usd: float
    used_pct: float
    period: str
    over_budget: bool
    warn_80pct: bool
    rows: list[CostRowOut] = Field(default_factory=list)


__all__ = [
    "AIActionOut", "AIAgentOut", "AgentPatchIn", "AutonomyPolicyCreateIn", "AutonomyPolicyOut",
    "AutonomyPolicyPatchIn", "ChatAnswerOut", "ChatContext", "ChatRequestIn", "ConfidenceOut",
    "ConfirmActionIn", "ConversationOut", "CostRowOut", "CostSummaryOut", "FunctionCallOut",
    "InsightOut", "KillSwitchIn", "KillSwitchOut", "MessageOut", "ModelCallLogOut",
    "PolicyDefaultOut", "RecommendationOut", "RejectActionIn", "SourceRefOut", "ToolCallLogOut",
    "ToolOut", "UndoActionIn",
]  # fmt: skip

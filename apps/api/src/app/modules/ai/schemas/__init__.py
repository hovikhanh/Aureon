"""`ai` Pydantic schemas — EP-110..119 contract (10 §4.10)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


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


class ToolOut(BaseModel):
    name: str
    kind: Literal["READ", "WRITE", "COMPUTE", "APPROVAL", "EXECUTION"]
    autonomy_default: str
    available: bool
    data_scope: str
    classification: str
    reversible: str
    cost_estimate: str


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


class CostSummaryOut(BaseModel):
    budget_usd: float
    used_usd: float
    used_pct: float
    period: str
    over_budget: bool
    warn_80pct: bool
    rows: list[CostRowOut] = Field(default_factory=list)

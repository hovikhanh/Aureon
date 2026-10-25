"""AI Control Center schemas — EP-AI-14..23 (10 §7.2.5, 05 §2.8, R-DEC-70..74).

`ToolOut` only **adds** fields to the v2.1 shape (EP-119 → EP-AI-14, 10 §7.2.5 last bullets), so
FE v2.1 keeps working; the 13 metadata of 10 §2.1 are exposed one-to-one.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

Level = Literal["L0", "L1", "L2", "L3"]
ToolKindOut = Literal["READ", "WRITE", "APPROVAL", "EXECUTION"]
RoleCode = Literal["CEO", "DIR", "MGR", "EMP", "REV", "ADM", "AI"]
ToolCallStatus = Literal["ok", "error", "forbidden", "timeout"]


class ToolOut(BaseModel):
    """EP-AI-14 row: v2.1 fields (kept) + 13 metadata + M1.6 extras."""

    # --- v2.1 (kept, not renamed) ---
    name: str
    kind: ToolKindOut
    autonomy_default: str
    available: bool
    data_scope: str
    classification: str
    reversible: str  # "true" | "false" | "n/a"
    cost_estimate: str
    # --- M1.6 additive (10 §2.1 13 metadata + 10 §7.2.5) ---
    tool_id: str | None = None  # registry id `TOOL-*` (= `name`)
    brd_name: str | None = None
    description: str | None = None
    domain: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    permission: list[str] = Field(default_factory=list)  # `required_permissions`
    risk_level: Literal["low", "medium", "high"] | None = None
    data_classification: Literal["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"] | None = None
    autonomy_max: Level | None = None
    approval_required: Literal["never", "threshold", "always"] | None = None
    audit_required: bool | None = None
    owner: str | None = None
    compute: bool = False
    agents: list[str] = Field(default_factory=list)
    effective_level: Level | None = None
    p1_frozen: bool = False
    action_name: str | None = None
    endpoint_ref: str | None = None


class AIAgentOut(BaseModel):
    """EP-AI-16/17 (ENT-AIAgent ≡ `ai.agent_profiles`, R-DEC-71).

    `month_spend_usd` is only present for `ai:admin` callers (the key is absent otherwise).
    """

    code: str
    agent_ref: str
    name_vi: str
    name_en: str
    description_vi: str
    description_en: str
    allowed_tools: list[str] = Field(default_factory=list)
    max_autonomy_level: Level
    effective_max_level: Level
    model_task: str
    prompt_version: str | None = None
    monthly_budget_usd: Decimal | None = None
    month_spend_usd: float | None = None
    is_enabled: bool
    kill_switched: bool
    version: int
    updated_at: datetime | None = None


class AgentPatchIn(BaseModel):
    """EP-AI-17 body — every change needs `reason` + optimistic `version`."""

    is_enabled: bool | None = None
    max_autonomy_level: Level | None = None
    monthly_budget_usd: Decimal | None = Field(default=None, ge=0)
    allowed_tools: list[str] | None = None
    reason: str = Field(min_length=1, max_length=500)
    version: int


class AutonomyPolicyOut(BaseModel):
    """EP-AI-18..20 row (05 §2.8 ENT-AutonomyPolicy)."""

    id: uuid.UUID
    tool_name: str
    action_name: str
    agent_profile_code: str | None = None
    role_code: RoleCode | None = None
    max_amount: int | None = None
    currency: str | None = None
    level: Level
    max_level: Level
    is_active: bool
    reason: str
    version: int
    updated_by: uuid.UUID | None = None
    updated_at: datetime | None = None


class PolicyDefaultOut(BaseModel):
    """EP-AI-18 `meta.defaults[]` — registry/seed default after the ceiling."""

    tool_name: str
    action_name: str
    default_level: Level
    max_level: Level


class AutonomyPolicyCreateIn(BaseModel):
    """EP-AI-19 body — `action_name` is derived server-side from `ToolDef.action_name`."""

    tool_name: str = Field(min_length=1)
    agent_profile_code: str | None = None
    role_code: RoleCode | None = None
    max_amount: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    level: Level
    max_level: Level
    is_active: bool = True
    reason: str = Field(min_length=1, max_length=500)


class AutonomyPolicyPatchIn(BaseModel):
    """EP-AI-20 body — tool/agent/role are immutable (create a new row instead)."""

    level: Level | None = None
    max_level: Level | None = None
    max_amount: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None
    reason: str = Field(min_length=1, max_length=500)
    version: int


class ToolCallLogOut(BaseModel):
    """EP-AI-22 row (`ai.tool_call_logs`, R-DEC-74). `arguments` are PII-scrubbed at write."""

    id: uuid.UUID
    created_at: datetime
    request_id: str | None = None
    user_id: uuid.UUID | None = None
    agent_profile_code: str
    tool_name: str
    tool_kind: Literal["READ", "WRITE", "APPROVAL", "EXECUTION"]
    status: ToolCallStatus
    error_code: str | None = None
    latency_ms: int
    autonomy_level: Level | None = None
    ai_action_id: uuid.UUID | None = None
    message_id: uuid.UUID | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_refs: list[dict[str, Any]] = Field(default_factory=list)


class ModelCallLogOut(BaseModel):
    """EP-AI-23 row (`ai.model_call_logs`). Never the raw prompt — only `prompt_sha256`."""

    id: uuid.UUID
    created_at: datetime
    request_id: str | None = None
    caller_module: str
    task_kind: str
    provider: str
    model: str
    fallback_from: str | None = None
    agent_profile_code: str | None = None
    user_id: uuid.UUID | None = None
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int
    status: ToolCallStatus
    error_code: str | None = None
    prompt_sha256: str | None = None

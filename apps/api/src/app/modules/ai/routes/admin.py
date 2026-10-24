"""AI Control Center — EP-AI-16..23 (10 §7.2.5, R-DEC-71..74).

`ai:query` reads agents (EP-AI-16); everything else is `ai:admin` (CEO scope `k`, ADM). Every
mutation needs `reason` (audit `why`) and writes `ai.policy_changed` to the outbox in the same
transaction. Static paths come before `{id}` paths. Endpoints whose behaviour lands in a later
M1.6 task answer `501` (`core/stub.py`).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import Depends, Query, Response

from app.core.deps import Principal, require_permission
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.core.stub import not_implemented
from app.modules.ai.schemas.admin import (
    AgentPatchIn,
    AIAgentOut,
    AutonomyPolicyCreateIn,
    AutonomyPolicyOut,
    AutonomyPolicyPatchIn,
    ModelCallLogOut,
    RoleCode,
    ToolCallLogOut,
)

router = EnvelopeRouter(prefix="/ai", tags=["ai-admin"])

AiUser = Annotated[Principal, Depends(require_permission("ai", "query"))]
AiAdmin = Annotated[Principal, Depends(require_permission("ai", "admin"))]
From = Annotated[datetime | None, Query(alias="from")]
To = Annotated[datetime | None, Query(alias="to")]


# ---------- EP-AI-16/17 agents ----------
@router.get("/agents", response_model=list[AIAgentOut], summary="EP-AI-16 AI agents")
async def list_agents(user: AiUser) -> Any:
    not_implemented("EP-AI-16", "T-646")


@router.patch("/agents/{code}", response_model=AIAgentOut, summary="EP-AI-17 Update AI agent")
async def patch_agent(code: str, body: AgentPatchIn, admin: AiAdmin) -> Any:
    not_implemented("EP-AI-17", "T-646")


# ---------- EP-AI-18..21 autonomy policies ----------
@router.get(
    "/autonomy-policies", response_model=list[AutonomyPolicyOut],
    summary="EP-AI-18 Autonomy policies",
)  # fmt: skip
async def list_policies(
    admin: AiAdmin,
    page: Annotated[PageParams, Depends(page_params("tool_name", "updated_at"))],
    tool_name: str | None = None, agent_profile_code: str | None = None,
    role_code: RoleCode | None = None, is_active: bool | None = None,
    include_deleted: bool = False,
) -> Any:  # fmt: skip
    not_implemented("EP-AI-18", "T-646")


@router.post(
    "/autonomy-policies", response_model=AutonomyPolicyOut, status_code=201,
    summary="EP-AI-19 Create autonomy policy",
)  # fmt: skip
async def create_policy(body: AutonomyPolicyCreateIn, admin: AiAdmin, idem: Idem) -> Any:
    not_implemented("EP-AI-19", "T-646")


@router.patch(
    "/autonomy-policies/{policy_id}", response_model=AutonomyPolicyOut,
    summary="EP-AI-20 Update autonomy policy",
)  # fmt: skip
async def patch_policy(policy_id: uuid.UUID, body: AutonomyPolicyPatchIn, admin: AiAdmin) -> Any:
    not_implemented("EP-AI-20", "T-646")


@router.delete(
    "/autonomy-policies/{policy_id}", status_code=204, response_class=Response,
    summary="EP-AI-21 Delete autonomy policy",
)  # fmt: skip
async def delete_policy(
    policy_id: uuid.UUID, admin: AiAdmin, reason: Annotated[str, Query(min_length=1)]
) -> Response:
    not_implemented("EP-AI-21", "T-646")


# ---------- EP-AI-22/23 logs ----------
@router.get("/tool-calls", response_model=list[ToolCallLogOut], summary="EP-AI-22 Tool call log")
async def list_tool_calls(
    admin: AiAdmin,
    page: Annotated[PageParams, Depends(page_params())],
    date_from: From = None, date_to: To = None,
    tool_name: str | None = None,
    tool_kind: Literal["READ", "WRITE", "APPROVAL", "EXECUTION"] | None = None,
    agent_profile_code: str | None = None,
    status: Literal["ok", "error", "forbidden", "timeout"] | None = None,
    user_id: uuid.UUID | None = None, request_id: str | None = None,
    ai_action_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    not_implemented("EP-AI-22", "T-647")


@router.get("/model-calls", response_model=list[ModelCallLogOut], summary="EP-AI-23 Model call log")
async def list_model_calls(
    admin: AiAdmin,
    page: Annotated[
        PageParams, Depends(page_params("estimated_cost_micro_usd", "latency_ms"))
    ],
    date_from: From = None, date_to: To = None,
    provider: str | None = None, model: str | None = None, task_kind: str | None = None,
    caller_module: str | None = None, agent_profile_code: str | None = None,
    status: Literal["ok", "error", "forbidden", "timeout"] | None = None,
    request_id: str | None = None,
) -> Any:  # fmt: skip
    not_implemented("EP-AI-23", "T-647")

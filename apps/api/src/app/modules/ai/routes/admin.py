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

from app.core.deps import DbSession, Principal, require_permission
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
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
from app.modules.ai.services.agent_service import AgentService
from app.modules.ai.services.call_log_service import CallLogService
from app.modules.ai.services.policy_service import PolicyService

router = EnvelopeRouter(prefix="/ai", tags=["ai-admin"])

AiUser = Annotated[Principal, Depends(require_permission("ai", "query"))]
AiAdmin = Annotated[Principal, Depends(require_permission("ai", "admin"))]
From = Annotated[datetime | None, Query(alias="from")]
To = Annotated[datetime | None, Query(alias="to")]


# ---------- EP-AI-16/17 agents ----------
@router.get(
    "/agents", response_model=list[AIAgentOut], summary="EP-AI-16 AI agents",
    response_model_exclude_unset=True,  # `month_spend_usd` key absent for non-admin (10 §7.2.5)
)  # fmt: skip
async def list_agents(user: AiUser, db: DbSession) -> Any:
    return await AgentService(db).list(user)


@router.patch("/agents/{code}", response_model=AIAgentOut, summary="EP-AI-17 Update AI agent")
async def patch_agent(code: str, body: AgentPatchIn, admin: AiAdmin, db: DbSession) -> Any:
    out = await AgentService(db).patch(admin, code, body)
    await db.commit()
    return out


# ---------- EP-AI-18..21 autonomy policies ----------
@router.get(
    "/autonomy-policies", response_model=list[AutonomyPolicyOut],
    summary="EP-AI-18 Autonomy policies",
)  # fmt: skip
async def list_policies(
    admin: AiAdmin, db: DbSession,
    page: Annotated[PageParams, Depends(page_params("tool_name", "updated_at"))],
    tool_name: str | None = None, agent_profile_code: str | None = None,
    role_code: RoleCode | None = None, is_active: bool | None = None,
    include_deleted: bool = False,
) -> Any:  # fmt: skip
    return await PolicyService(db).list(
        page, tool_name=tool_name, agent_profile_code=agent_profile_code, role_code=role_code,
        is_active=is_active, include_deleted=include_deleted,
    )  # fmt: skip


@router.post(
    "/autonomy-policies", response_model=AutonomyPolicyOut, status_code=201,
    summary="EP-AI-19 Create autonomy policy",
)  # fmt: skip
async def create_policy(
    body: AutonomyPolicyCreateIn, admin: AiAdmin, idem: Idem, db: DbSession
) -> Any:
    out = await PolicyService(db).create(admin, body)
    await db.commit()
    return out


@router.patch(
    "/autonomy-policies/{policy_id}", response_model=AutonomyPolicyOut,
    summary="EP-AI-20 Update autonomy policy",
)  # fmt: skip
async def patch_policy(
    policy_id: uuid.UUID, body: AutonomyPolicyPatchIn, admin: AiAdmin, db: DbSession
) -> Any:
    out = await PolicyService(db).patch(admin, policy_id, body)
    await db.commit()
    return out


@router.delete(
    "/autonomy-policies/{policy_id}", status_code=204, response_class=Response,
    summary="EP-AI-21 Delete autonomy policy",
)  # fmt: skip
async def delete_policy(
    policy_id: uuid.UUID,
    admin: AiAdmin,
    db: DbSession,
    reason: Annotated[str, Query(min_length=1)],
) -> Response:
    await PolicyService(db).delete(admin, policy_id, reason)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-AI-22/23 logs ----------
@router.get("/tool-calls", response_model=list[ToolCallLogOut], summary="EP-AI-22 Tool call log")
async def list_tool_calls(
    admin: AiAdmin, db: DbSession,
    page: Annotated[PageParams, Depends(page_params())],
    date_from: From = None, date_to: To = None,
    tool_name: str | None = None,
    tool_kind: Literal["READ", "WRITE", "APPROVAL", "EXECUTION"] | None = None,
    agent_profile_code: str | None = None,
    status: Literal["ok", "error", "forbidden", "timeout"] | None = None,
    user_id: uuid.UUID | None = None, request_id: str | None = None,
    ai_action_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    return await CallLogService(db).tool_calls(
        page, start=date_from, end=date_to, request_id=request_id, tool_name=tool_name,
        tool_kind=tool_kind, agent_profile_code=agent_profile_code, status=status,
        user_id=user_id, ai_action_id=ai_action_id,
    )  # fmt: skip


@router.get("/model-calls", response_model=list[ModelCallLogOut], summary="EP-AI-23 Model call log")
async def list_model_calls(
    admin: AiAdmin, db: DbSession,
    page: Annotated[
        PageParams, Depends(page_params("estimated_cost_micro_usd", "latency_ms"))
    ],
    date_from: From = None, date_to: To = None,
    provider: str | None = None, model: str | None = None, task_kind: str | None = None,
    caller_module: str | None = None, agent_profile_code: str | None = None,
    status: Literal["ok", "error", "forbidden", "timeout"] | None = None,
    request_id: str | None = None,
) -> Any:  # fmt: skip
    return await CallLogService(db).model_calls(
        page, start=date_from, end=date_to, request_id=request_id, provider=provider,
        model=model, task_kind=task_kind, caller_module=caller_module,
        agent_profile_code=agent_profile_code, status=status,
    )  # fmt: skip

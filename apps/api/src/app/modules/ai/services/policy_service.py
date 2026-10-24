"""EP-AI-18..21 — autonomy policies per tool × agent × role × amount (R-DEC-73, 10 §7.2.5).

Only WRITE/EXECUTION tools are configurable. Validation order (first failure wins):
`not_configurable` → `level > max_level` / `max_level > ToolDef.autonomy_max` (`above_tool_max`)
→ ceiling (`above_ceiling`) → EXECUTION `max_level > L2` (`execution_max_l2`) → finance
(`critical_field`, level > L2). Every mutation writes audit `ai.autonomy_policy_*` + outbox
`ai.policy_changed` (`change=autonomy_policy`) in the request transaction.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.envelope import Page
from app.core.errors import (
    BusinessRuleError,
    ConflictStateError,
    DuplicateResourceError,
    NotFoundError,
    ValidationError,
)
from app.core.pagination import PageParams
from app.modules.ai.models import AutonomyPolicy
from app.modules.ai.repositories import AutonomyPolicyRepository
from app.modules.ai.schemas.admin import (
    AutonomyPolicyCreateIn,
    AutonomyPolicyOut,
    AutonomyPolicyPatchIn,
    PolicyDefaultOut,
)
from app.modules.ai.services.action_registry import is_finance_action
from app.modules.ai.services.agent_service import AgentService, publish_policy_changed
from app.modules.ai.services.autonomy import (
    autonomy_ceiling,
    default_levels,
    level_le,
    level_min,
)
from app.modules.ai.tools import ToolDef, all_tools, get_tool

CONFIGURABLE = ("WRITE", "EXECUTION")


def _rule(reason: str, message: str, **details: Any) -> BusinessRuleError:
    return BusinessRuleError(message, details={"reason": reason, **details})


def _check_levels(tool: ToolDef, level: str, max_level: str) -> None:
    if not level_le(level, max_level) or not level_le(max_level, tool.autonomy_max):
        raise _rule("above_tool_max", "level above max_level / tool autonomy_max",
                    tool_max=tool.autonomy_max)  # fmt: skip
    ceiling = autonomy_ceiling()
    if not level_le(level, ceiling) or not level_le(max_level, ceiling):
        raise _rule("above_ceiling", "level above autonomy ceiling", ceiling=ceiling)
    if tool.kind == "EXECUTION" and not level_le(max_level, "L2"):
        raise _rule("execution_max_l2", "EXECUTION tools are capped at L2 (02 §6)")
    critical = tool.domain == "finance" or (
        tool.action_name is not None and is_finance_action(tool.action_name)
    )
    if critical and not level_le(level, "L2"):
        raise _rule("critical_field", "finance / critical-field actions stay ≤ L2")


def _check_amount(max_amount: int | None, currency: str | None) -> None:
    if max_amount is not None and not currency:
        raise ValidationError("max_amount requires currency", details={"field": "currency"})


def policy_defaults() -> list[dict[str, Any]]:
    """`meta.defaults[]` — registry/seed defaults after the ceiling (EP-AI-18)."""
    ceiling = autonomy_ceiling()
    out = []
    for t in all_tools():
        if t.kind not in CONFIGURABLE or t.action_name is None:
            continue
        d, m = default_levels(t.action_name)
        out.append(PolicyDefaultOut(
            tool_name=t.name, action_name=t.action_name, default_level=level_min(d, ceiling),
            max_level=level_min(level_min(m, t.autonomy_max), ceiling),
        ).model_dump())  # fmt: skip
    return out


class PolicyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AutonomyPolicyRepository(db)

    @staticmethod
    def out(p: AutonomyPolicy) -> AutonomyPolicyOut:
        return AutonomyPolicyOut.model_validate(p, from_attributes=True)

    async def list(
        self, page: PageParams, *, tool_name: str | None = None,
        agent_profile_code: str | None = None, role_code: str | None = None,
        is_active: bool | None = None, include_deleted: bool = False,
    ) -> Page[AutonomyPolicyOut]:  # fmt: skip
        rows, total = await self.repo.page(
            filters={"tool_name": tool_name, "agent_profile_code": agent_profile_code,
                     "role_code": role_code, "is_active": is_active},
            include_deleted=include_deleted, sort_by=page.sort_by, order=page.order,
            limit=page.limit, offset=page.offset,
        )  # fmt: skip
        return Page(items=[self.out(p) for p in rows], total=total, limit=page.limit,
                    offset=page.offset, defaults=policy_defaults())  # fmt: skip

    async def create(self, admin: Principal, body: AutonomyPolicyCreateIn) -> AutonomyPolicyOut:
        tool = get_tool(body.tool_name)
        if tool is None:
            raise ValidationError("unknown tool", details={"field": "tool_name"})
        if tool.kind not in CONFIGURABLE or tool.action_name is None:
            raise _rule("not_configurable", "only WRITE/EXECUTION tools are configurable")
        if body.agent_profile_code is not None and body.agent_profile_code not in (
            await AgentService(self.db).codes()
        ):
            raise ValidationError("unknown agent", details={"field": "agent_profile_code"})
        _check_levels(tool, body.level, body.max_level)
        _check_amount(body.max_amount, body.currency)
        await self._ensure_unique(tool.action_name, body.agent_profile_code, body.role_code,
                                  body.max_amount)  # fmt: skip
        p = AutonomyPolicy(
            tool_name=tool.name, action_name=tool.action_name,
            agent_profile_code=body.agent_profile_code, role_code=body.role_code,
            max_amount=body.max_amount, currency=body.currency, level=body.level,
            max_level=body.max_level, is_active=body.is_active, reason=body.reason,
            created_by=admin.user_id, updated_by=admin.user_id,
        )  # fmt: skip
        self.db.add(p)
        await self.db.flush()
        await self.db.refresh(p)
        await self._trail(p, "ai.autonomy_policy_create", None, body.reason)
        return self.out(p)

    async def patch(
        self, admin: Principal, policy_id: uuid.UUID, body: AutonomyPolicyPatchIn
    ) -> AutonomyPolicyOut:
        p = await self._live(policy_id)
        if body.version != p.version:
            raise ConflictStateError("version mismatch", details={"current_version": p.version})
        tool = get_tool(p.tool_name)
        if tool is None or tool.kind not in CONFIGURABLE:
            raise _rule("not_configurable", "tool no longer configurable")
        changes = body.model_dump(exclude_unset=True, exclude={"reason", "version"})
        level = changes.get("level", p.level)
        max_level = changes.get("max_level", p.max_level)
        _check_levels(tool, level, max_level)
        _check_amount(changes.get("max_amount", p.max_amount),
                      changes.get("currency", p.currency))  # fmt: skip
        if "max_amount" in changes and changes["max_amount"] != p.max_amount:
            await self._ensure_unique(p.action_name, p.agent_profile_code, p.role_code,
                                      changes["max_amount"], exclude=p.id)  # fmt: skip
        before = self._snapshot(p)
        for k, v in changes.items():
            setattr(p, k, v)
        p.reason, p.version = body.reason, p.version + 1
        p.updated_by, p.updated_at = admin.user_id, datetime.now(UTC)
        await self.db.flush()
        await self._trail(p, "ai.autonomy_policy_update", before, body.reason)
        return self.out(p)

    async def delete(self, admin: Principal, policy_id: uuid.UUID, reason: str) -> None:
        p = await self._live(policy_id)
        before = self._snapshot(p)
        p.deleted_at = datetime.now(UTC)
        p.updated_by, p.version = admin.user_id, p.version + 1
        await self.db.flush()
        await self._trail(p, "ai.autonomy_policy_delete", before, reason)

    async def _live(self, policy_id: uuid.UUID) -> AutonomyPolicy:
        p = await self.repo.live(policy_id)
        if p is None:
            raise NotFoundError("autonomy policy not found")
        return p

    async def _ensure_unique(
        self, action: str, agent: str | None, role: str | None, amount: int | None,
        *, exclude: uuid.UUID | None = None,
    ) -> None:  # fmt: skip
        if await self.repo.key_taken(action, agent, role, amount, exclude=exclude):
            raise DuplicateResourceError("policy already exists for this key")

    @staticmethod
    def _snapshot(p: AutonomyPolicy) -> dict[str, Any]:
        return {"level": p.level, "max_level": p.max_level, "max_amount": p.max_amount,
                "currency": p.currency, "is_active": p.is_active}  # fmt: skip

    async def _trail(
        self, p: AutonomyPolicy, action: str, before: dict[str, Any] | None, why: str
    ) -> None:
        await record_audit(
            self.db, action=action, target_schema="ai", target_table="autonomy_policies",
            target_id=p.id, before=before,
            after=None if p.deleted_at else self._snapshot(p), why=why,
        )  # fmt: skip
        await publish_policy_changed(self.db, p, {
            "change": "autonomy_policy", "ref_id": str(p.id), "agent_code": p.agent_profile_code,
            "tool_name": p.tool_name, "level": None if p.deleted_at else p.level,
        })  # fmt: skip

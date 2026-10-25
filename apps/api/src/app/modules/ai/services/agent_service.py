"""EP-AI-16/17 — AI agents (R-DEC-71, 10 §7.2.5).

The catalog is fixed (6 P0 agents, seeded); the API only edits. Every edit needs `reason` +
optimistic `version`, writes `ai.agent_update` audit and the `ai.policy_changed`
(`change=agent`) outbox event in the request transaction. Effective tools of an agent =
`allowed_tools` ∩ the asker's `available_for(permissions)` (see `effective_tools`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ConflictStateError, NotFoundError
from app.core.events.outbox import publish_in_tx
from app.modules.ai.models import AgentProfile
from app.modules.ai.repositories import AgentProfileRepository
from app.modules.ai.schemas.admin import AgentPatchIn, AIAgentOut
from app.modules.ai.services.agent_catalog import assignable
from app.modules.ai.services.autonomy import (
    Level,
    autonomy_ceiling,
    level_le,
    level_min,
    read_kill_switch,
)
from app.modules.ai.services.cost_service import CostService
from app.modules.ai.tools import ToolDef, advertisable_for


async def publish_policy_changed(db: AsyncSession, aggregate: Any, payload: dict[str, Any]) -> None:
    """`ai.policy_changed` (10 §9.2) — payload carries codes/levels only (no PII, no reason)."""
    await publish_in_tx(
        db, event_type="ai.policy_changed", producer="ai", aggregate_schema="ai",
        aggregate_table=aggregate.__tablename__, aggregate_id=aggregate.id,
        payload={k: v for k, v in payload.items() if v is not None},
    )  # fmt: skip


class AgentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AgentProfileRepository(db)

    async def get(self, code: str) -> AgentProfile | None:
        return await self.repo.by_code(code)

    async def codes(self) -> set[str]:
        return {a.code for a in await self.repo.all()}

    async def effective_tools(
        self, code: str, permissions: frozenset[str], **kw: Any
    ) -> tuple[ToolDef, ...]:
        """Tools advertised to the model for `code` serving this user (FR-ADM-03).

        Disabled or unknown agent → no tool at all (never fall back to the full catalog).
        """
        agent = await self.get(code)
        if agent is None or not agent.is_enabled:
            return ()
        return advertisable_for(permissions, allowed=frozenset(agent.allowed_tools), **kw)

    async def list(self, user: Principal) -> list[AIAgentOut]:
        rows = await self.repo.all()
        admin = "ai:admin" in user.permissions
        spend = await CostService(self.db).spend_by_agent() if admin else {}
        ks = await read_kill_switch(self.db)
        out = []
        for a in rows:
            item = self._out(a, kill_switched=ks.applies_to(a.code))
            if admin:
                item.month_spend_usd = spend.get(a.code, 0.0)
            out.append(item)
        return out

    @staticmethod
    def _out(a: AgentProfile, *, kill_switched: bool) -> AIAgentOut:
        level: Level = a.max_autonomy_level  # type: ignore[assignment]
        return AIAgentOut(
            code=a.code, agent_ref=a.agent_ref, name_vi=a.name_vi, name_en=a.name_en,
            description_vi=a.description_vi, description_en=a.description_en,
            allowed_tools=list(a.allowed_tools), max_autonomy_level=level,
            effective_max_level=level_min(level, autonomy_ceiling()), model_task=a.model_task,
            prompt_version=a.prompt_version,
            monthly_budget_usd=Decimal(a.monthly_budget_usd)
            if a.monthly_budget_usd is not None else None,
            is_enabled=a.is_enabled, kill_switched=kill_switched, version=a.version,
            updated_at=a.updated_at,
        )  # fmt: skip

    async def patch(self, admin: Principal, code: str, body: AgentPatchIn) -> AIAgentOut:
        a = await self.get(code)
        if a is None:
            raise NotFoundError("agent not found", details={"code": code})
        if body.version != a.version:
            raise ConflictStateError("version mismatch",
                                     details={"current_version": a.version})  # fmt: skip
        if body.max_autonomy_level and not level_le(body.max_autonomy_level, autonomy_ceiling()):
            raise BusinessRuleError(
                "max_autonomy_level above ceiling",
                details={"reason": "above_ceiling", "ceiling": autonomy_ceiling()},
            )
        if body.allowed_tools is not None:
            bad = sorted({t for t in body.allowed_tools if not assignable(t)})
            if bad:
                raise BusinessRuleError(
                    "invalid tools", details={"reason": "invalid_tool", "tools": bad}
                )
        before = self._snapshot(a)
        changes = body.model_dump(exclude_unset=True, exclude={"reason", "version"})
        for k, v in changes.items():
            setattr(a, k, list(dict.fromkeys(v)) if k == "allowed_tools" else v)
        a.version += 1
        a.updated_by = admin.user_id
        a.updated_at = datetime.now(UTC)
        await self.db.flush()
        await record_audit(
            self.db, action="ai.agent_update", target_schema="ai", target_table="agent_profiles",
            target_id=a.id, before=before, after=self._snapshot(a), why=body.reason,
        )  # fmt: skip
        await publish_policy_changed(self.db, a, {
            "change": "agent", "ref_id": str(a.id), "agent_code": a.code,
            "enabled": a.is_enabled, "level": a.max_autonomy_level,
        })  # fmt: skip
        ks = await read_kill_switch(self.db)
        out = self._out(a, kill_switched=ks.applies_to(a.code))
        out.month_spend_usd = (await CostService(self.db).spend_by_agent()).get(a.code, 0.0)
        return out

    @staticmethod
    def _snapshot(a: AgentProfile) -> dict[str, Any]:
        return {
            "is_enabled": a.is_enabled, "max_autonomy_level": a.max_autonomy_level,
            "monthly_budget_usd": str(a.monthly_budget_usd)
            if a.monthly_budget_usd is not None else None,
            "allowed_tools": list(a.allowed_tools),
        }  # fmt: skip

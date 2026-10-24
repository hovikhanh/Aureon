"""Autonomy policy resolution (04 §9.1, 10 §7.2.5 M1.6) and the AI kill switch (04 §9.2).

`resolve_level` order (R-DEC-72/73, T-646):

1. seed default `AUTONOMY_DEFAULTS[action]` (unchanged — L3 kept for M3.2);
2. the most specific matching `ENT-AutonomyPolicy` row (agent+role+amount > agent > role >
   general; several rows of the same rank → the **lowest** level, fail safe);
3. `min(level, agent.max_autonomy_level)`;
4. `min(level, AI_AUTONOMY_CEILING)` (`ConfigService`, L2 through M1 — L3 cannot happen);
5. kill switch for this agent: `WRITE_OFF` → `min(level, L2)`, `L0` → `L0`.

The kill switch is a `platform.system_settings` row (`key = "ai.kill_switch"`) and may target
specific agents (per-agent — DEC-149) or act globally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.modules.ai.models import AutonomyPolicy
from app.modules.ai.repositories import AgentProfileRepository, AutonomyPolicyRepository
from app.modules.platform.services.settings_service import SystemSettingService

KILL_SWITCH_KEY = "ai.kill_switch"
Level = Literal["L0", "L1", "L2", "L3"]
_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}

# seed defaults — 04 §9.1 "Mặc định seed v2": (default_level, max_level)
AUTONOMY_DEFAULTS: dict[str, tuple[Level, Level]] = {
    "ACT-create_task": ("L3", "L3"),
    "ACT-create_meeting": ("L3", "L3"),
    "ACT-record_decision": ("L3", "L3"),
    "ACT-record_kpi_measurement": ("L2", "L3"),
    "ACT-record_product_metric": ("L2", "L3"),
    "ACT-create_invoice": ("L2", "L3"),
    "ACT-record_expense": ("L2", "L3"),
    "ACT-record_revenue": ("L2", "L3"),
    "ACT-record_cash_position": ("L2", "L3"),
    "ACT-upsert_budget": ("L2", "L3"),
    "ACT-create_contract": ("L2", "L2"),
    "ACT-upsert_deal": ("L2", "L2"),
    "ACT-upsert_sales_target": ("L2", "L2"),
    "ACT-upsert_employee": ("L2", "L2"),
    "ACT-upsert_department": ("L2", "L2"),
    "ACT-upsert_risk": ("L2", "L2"),
    "ACT-create_mitigation": ("L2", "L2"),
    "ACT-upsert_objective": ("L2", "L2"),
    "ACT-upsert_kpi": ("L2", "L2"),
    "ACT-upsert_metric_value": ("L2", "L2"),
    "ACT-upsert_client": ("L2", "L2"),
}
DEFAULT_LEVEL: tuple[Level, Level] = ("L2", "L2")  # unknown write action → safe L2


@dataclass(frozen=True)
class KillSwitch:
    enabled: bool
    mode: str  # "WRITE_OFF" | "L0"
    agents: tuple[str, ...]  # empty = global

    def applies_to(self, agent_code: str) -> bool:
        if not self.enabled:
            return False
        return not self.agents or agent_code in self.agents


def level_min(a: Level, b: Level) -> Level:
    return a if _ORDER[a] <= _ORDER[b] else b


async def read_kill_switch(db: AsyncSession) -> KillSwitch:
    row = await SystemSettingService(db).get(KILL_SWITCH_KEY)
    if row is None:
        return KillSwitch(enabled=False, mode="WRITE_OFF", agents=())
    v: dict[str, Any] = row.value
    return KillSwitch(
        enabled=bool(v.get("enabled", False)),
        mode=str(v.get("mode", "WRITE_OFF")),
        agents=tuple(v.get("agents", []) or ()),
    )


def autonomy_ceiling() -> Level:
    """R-DEC-72 system ceiling (`AI_AUTONOMY_CEILING`)."""
    return get_config().ai_autonomy_ceiling


def level_le(a: str, b: str) -> bool:
    return _ORDER[a] <= _ORDER[b]


def default_levels(action_name: str) -> tuple[Level, Level]:
    return AUTONOMY_DEFAULTS.get(action_name, DEFAULT_LEVEL)


async def resolve_level(
    db: AsyncSession, *, action_name: str, role: str, amount: int | None,
    agent_code: str,
) -> Level:  # fmt: skip
    """Effective autonomy for a proposed action (10 §7.2.5 order, see module doc)."""
    default, _max = default_levels(action_name)
    level = await _policy_level(db, action_name, role, amount, agent_code) or default
    agent_max = await _agent_max(db, agent_code)
    if agent_max is not None:
        level = level_min(level, agent_max)
    level = level_min(level, autonomy_ceiling())
    ks = await read_kill_switch(db)
    if ks.applies_to(agent_code):
        if ks.mode == "L0":
            return "L0"
        level = level_min(level, "L2")  # WRITE_OFF: no auto-execute
    return level


async def _agent_max(db: AsyncSession, agent_code: str) -> Level | None:
    """`max_autonomy_level` of the agent; unknown (v2.1 `assistant`) → no extra cap."""
    return await AgentProfileRepository(db).max_level(agent_code)  # type: ignore[return-value]


def _rank(p: AutonomyPolicy) -> int:
    """Specificity: agent (4) > role (2) > amount (1); a general row ranks 0."""
    return (
        (4 if p.agent_profile_code else 0)
        + (2 if p.role_code else 0)
        + (1 if p.max_amount is not None else 0)
    )


async def _policy_level(
    db: AsyncSession, action_name: str, role: str, amount: int | None, agent_code: str
) -> Level | None:
    rows = await AutonomyPolicyRepository(db).active_for(action_name)
    best: tuple[int, Level] | None = None
    for p in rows:
        if p.agent_profile_code is not None and p.agent_profile_code != agent_code:
            continue
        if p.role_code is not None and p.role_code != role:
            continue
        if p.max_amount is not None and (amount is None or amount > p.max_amount):
            continue
        cand: Level = p.level  # type: ignore[assignment]
        rank = _rank(p)
        if best is None or rank > best[0] or (rank == best[0] and _ORDER[cand] < _ORDER[best[1]]):
            best = (rank, cand)
    return best[1] if best else None

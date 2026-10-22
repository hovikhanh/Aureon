"""Autonomy policy resolution (04 §9.1) and the AI kill switch (04 §9.2, T-306).

`ENT-AutonomyPolicy` rows (schema `ai`) override the seed defaults below per
`ACT-* × role × amount threshold`. With no row, the seed default applies. The effective level
is further capped by the **kill switch**: when engaged in `WRITE_OFF` mode every L3 drops to L2
(no auto-execute); `L0` additionally blocks L1/L2 preparation. The kill switch is a
`platform.system_settings` row (`key = "ai.kill_switch"`) and may target specific agents
(per-agent — DEC-149) or act globally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import AutonomyPolicy
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


def _min(a: Level, b: Level) -> Level:
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


async def resolve_level(
    db: AsyncSession, *, action_name: str, role: str, amount: int | None,
    agent_code: str,
) -> Level:  # fmt: skip
    """Effective autonomy for a proposed action after policy + kill switch (04 §9)."""
    default, _max = AUTONOMY_DEFAULTS.get(action_name, DEFAULT_LEVEL)
    level = await _policy_level(db, action_name, role, amount) or default
    ks = await read_kill_switch(db)
    if ks.applies_to(agent_code):
        if ks.mode == "L0":
            return "L0"
        level = _min(level, "L2")  # WRITE_OFF: no auto-execute
    return level


async def _policy_level(
    db: AsyncSession, action_name: str, role: str, amount: int | None
) -> Level | None:
    rows = (
        (
            await db.execute(
                select(AutonomyPolicy).where(
                    AutonomyPolicy.action_name == action_name,
                    AutonomyPolicy.is_active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    best: Level | None = None
    for p in rows:
        if p.role_code is not None and p.role_code != role:
            continue
        if p.max_amount is not None and (amount is None or amount > p.max_amount):
            continue
        cand: Level = p.level  # type: ignore[assignment]
        if best is None or _ORDER[cand] > _ORDER[best]:
            best = cand
    return best

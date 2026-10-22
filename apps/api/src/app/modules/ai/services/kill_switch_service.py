"""Kill switch admin (T-306, EP-118, 04 §9.2) — read + set the AI write kill switch.

Backed by a `platform.system_settings` row (`key = "ai.kill_switch"`) accessed through the
platform public `SystemSettingService` (DEC-125 — no cross-module model import). A PUT requires
`ai:admin` and a reason (audit `ai.kill_switch`); CEO may toggle it too (`ai:admin ◑k`). The
switch can target specific agents (per-agent — DEC-149) or act globally when `agents` is empty.
Reads are open to `ai:query`. Enforcement lives in `autonomy.resolve_level`.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.modules.ai.schemas import KillSwitchIn, KillSwitchOut
from app.modules.ai.services.autonomy import KILL_SWITCH_KEY, read_kill_switch
from app.modules.platform.services.settings_service import SystemSettingService


class KillSwitchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._settings = SystemSettingService(db)

    async def status(self) -> KillSwitchOut:
        ks = await read_kill_switch(self.db)
        row = await self._settings.get(KILL_SWITCH_KEY)
        return KillSwitchOut(
            enabled=ks.enabled, mode=ks.mode, agents=list(ks.agents),
            changed_by=row.updated_by if row else None,
            changed_at=row.updated_at if row else None,
        )  # fmt: skip

    async def set(self, admin: Principal, body: KillSwitchIn) -> KillSwitchOut:
        value = {"enabled": body.enabled, "mode": body.mode, "agents": body.agents}
        await self._settings.set(
            KILL_SWITCH_KEY, value, reason=body.reason, updated_by=admin.user_id
        )
        await record_audit(
            self.db, action="ai.kill_switch", target_schema="platform",
            target_table="system_settings",
            metadata={"key": KILL_SWITCH_KEY, "enabled": body.enabled, "mode": body.mode},
            why=body.reason,
        )  # fmt: skip
        return await self.status()

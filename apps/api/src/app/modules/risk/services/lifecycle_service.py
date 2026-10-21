"""Risk lifecycle — EP-104 accept (CEO) and EP-106 status transitions (BR-RSK-02, DEC-148).

Reasons (`accept`, `rejected`, any EP-106 `reason`) are kept in the audit row `why` (05 has
no reason column except `accepted_reason`) — DEC-216.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ConflictStateError
from app.modules.risk.models import Risk
from app.modules.risk.repositories import MitigationRepository, RiskRepository
from app.modules.risk.schemas import AcceptIn, RiskOut, StatusChange
from app.modules.risk.services import rules, scope
from app.modules.risk.services.common import (
    audit,
    now_utc,
    publish,
    publish_identified,
    risk_out,
)
from app.modules.risk.services.risk_service import RiskService


class RiskLifecycleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.risks = RiskRepository(db)
        self.mitigations = MitigationRepository(db)

    async def _locked(self, user: Principal, id_: uuid.UUID) -> Risk:
        obj = await RiskService(self.db).get_row(user, id_)
        await self.risks.lock(obj)
        return obj

    # ---------- EP-104 ----------
    async def accept(self, user: Principal, id_: uuid.UUID, body: AcceptIn) -> RiskOut:
        """CEO accepts the risk (`risk:approve`); `409` from `closed`/`rejected`/`proposed`."""
        obj = await self._locked(user, id_)
        if obj.status in ("closed", "rejected", "proposed", "accepted"):
            raise ConflictStateError(
                f"cannot accept a risk in status {obj.status}", details={"status": obj.status}
            )
        before = risk_out(obj)
        await self.risks.update(
            obj, status="accepted", accepted_by=user.user_id, accepted_reason=body.reason,
            accepted_at=now_utc(), updated_by=user.user_id,
        )  # fmt: skip
        await self.db.refresh(obj)
        out = risk_out(obj)
        await audit(self.db, "risk.risk_accept", "risks", obj, before, out, why=body.reason)
        return out

    # ---------- EP-106 ----------
    async def change_status(self, user: Principal, id_: uuid.UUID, body: StatusChange) -> RiskOut:
        obj = await self._locked(user, id_)
        scope.check_write(user, obj)
        target, current = body.to_status, obj.status
        if target == "accepted":
            raise ConflictStateError("use EP-104 /accept (risk:approve) to accept a risk")
        if not rules.can_transition(current, target):
            raise ConflictStateError(
                f"transition {current} -> {target} not allowed",
                details={"from_status": current, "to_status": target},
            )
        if target == "rejected" and not (body.reason and body.reason.strip()):
            raise BusinessRuleError(
                "reason is required to reject a proposed risk",
                details={"field": "reason", "rule": "BR-RSK-02"},
            )
        owner = body.owner_id or obj.owner_id
        if target in rules.OWNER_REQUIRED and owner is None:
            raise BusinessRuleError(
                f"owner_id is required before {target}",
                details={"field": "owner_id", "rule": "BR-RSK-02"},
            )
        if target == "closed" and await self.mitigations.count_status(obj.id, "in_progress"):
            raise BusinessRuleError(
                "cannot close a risk with mitigations in progress",
                details={"rule": "BR-RSK-02"},
            )
        before = risk_out(obj)
        values: dict[str, Any] = {"status": target, "owner_id": owner}
        if current == "proposed" and target == "identified":
            now = now_utc()
            values.update(confirmed_by=user.user_id, confirmed_at=now, identified_at=now)
        await self.risks.update(obj, updated_by=user.user_id, **values)
        await self.db.refresh(obj)
        out = risk_out(obj)
        await audit(self.db, "risk.risk_status_change", "risks", obj, before, out, why=body.reason)
        if current == "proposed" and target == "identified":
            await publish_identified(self.db, obj)
        if target in rules.MITIGATED_STATUSES:
            await publish(self.db, "risk.risk_mitigated", obj, {"status": target})
        return out

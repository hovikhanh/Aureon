"""Approval workflow (T-305, EP-123..125, DEC-155) — the 2-sided gate for high-value actions.

A finance action whose `amount ≥ APPROVAL_FINANCE_THRESHOLD_VND` (default 500M) needs **two**
distinct approvers (CEO then CFO — 10 §4.11); anything else needs one. The DB enforces
`second_decided_by ∉ {first_decided_by, requested_by}` (CK `distinct_approvers`); this service
additionally checks the decider holds `platform:approve`, is in the step's approver role, and has
not already decided. Rejecting at any step rejects the whole request. The final `APPROVED`
decision runs `on_approved` in the **same transaction** (Action Registry — 04 §10.4).

Lives in `platform` because `ENT-ApprovalRequest` is a platform table; the `ai` module opens a
request for an `ENT-AIAction` through `create_for_ai_action` (passing its own `AsyncSession`).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.config import get_config
from app.core.deps import Principal
from app.core.errors import AppError, PermissionDeniedError
from app.modules.platform.models import ApprovalRequest, ApprovalRule
from app.modules.platform.repositories import ApprovalRequestRepository
from app.modules.platform.schemas import ApprovalRequestOut

# step → approver roles for an AI-action finance approval (DEC-155; CFO→DIR theo R-DEC-12)
FINANCE_STEP_ROLES = {1: ("CEO",), 2: ("DIR",)}
SINGLE_STEP_ROLES = ("CEO", "DIR")
DEFAULT_SLA_HOURS = 8
RULE_SINGLE = "RULE-ai_action_single"
RULE_TWO_SIDED = "RULE-ai_action_two_sided"


class ApprovalConflictError(AppError):
    status_code, code = 409, "CONFLICT_STATE"


class ApprovalService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_for_ai_action(
        self, *, ai_action_id: uuid.UUID, requested_by: uuid.UUID, amount: int | None,
        currency: str, payload: dict[str, Any], is_finance: bool,
    ) -> ApprovalRequest:  # fmt: skip
        """Open an approval request for an AI action; 2-step iff finance ≥ threshold (DEC-155)."""
        threshold = get_config().approval_finance_threshold_vnd
        two_sided = is_finance and amount is not None and amount >= threshold
        rule = await self._finance_rule(two_sided)
        req = ApprovalRequest(
            rule_id=rule.id, ai_action_id=ai_action_id,
            payload=payload, amount=amount, currency=currency, requested_by=requested_by,
            status="PENDING", step=1, source="AI",
            due_at=datetime.now(UTC) + timedelta(hours=rule.sla_hours),
        )  # fmt: skip
        self.db.add(req)
        await self.db.flush()
        await record_audit(
            self.db, action="platform.approval_requested", target_schema="platform",
            target_table="approval_requests", target_id=req.id,
            metadata={"two_sided": two_sided, "ai_action_id": str(ai_action_id)},
        )  # fmt: skip
        return req

    async def decide(
        self, approver: Principal, request_id: uuid.UUID, *, decision: str,
        reason: str | None, on_approved: Callable[[ApprovalRequest], Awaitable[None]] | None = None,
    ) -> ApprovalRequestOut:  # fmt: skip
        if not approver.has("platform:approve"):
            raise PermissionDeniedError("approver lacks platform:approve")
        req = await self._locked(request_id)
        if req.status != "PENDING":
            raise ApprovalConflictError("request already decided or expired")
        if req.due_at < datetime.now(UTC):
            req.status = "EXPIRED"
            await self.db.flush()
            raise ApprovalConflictError("request expired")
        two_sided = await self._two_sided(req)
        self._check_step_role(req, approver, two_sided)
        if decision == "reject":
            return await self._reject(req, approver, reason)
        return await self._approve(req, approver, two_sided, on_approved)

    # ---------- internals ----------
    async def _approve(
        self, req: ApprovalRequest, approver: Principal, two_sided: bool,
        on_approved: Callable[[ApprovalRequest], Awaitable[None]] | None,
    ) -> ApprovalRequestOut:  # fmt: skip
        now = datetime.now(UTC)
        if req.step == 1:
            if req.requested_by == approver.user_id:
                raise self._biz("approver must differ from requester")
            req.first_decided_by = approver.user_id
            req.first_decided_at = now
            if two_sided:
                req.step = 2  # await the second approver; stays PENDING
                await self.db.flush()
                await self._audit_decision(req, approver, "approve", step=1)
                return self._to_out(req)
        else:  # step 2
            if approver.user_id in (req.requested_by, req.first_decided_by):
                raise self._biz("second approver must be distinct (DEC-155)")
            req.second_decided_by = approver.user_id
            req.second_decided_at = now
        req.status = "APPROVED"
        await self.db.flush()
        if on_approved is not None:
            await on_approved(req)  # Action Registry, same transaction (04 §10.4)
        await self._audit_decision(req, approver, "approve", step=req.step)
        return self._to_out(req)

    async def _reject(
        self, req: ApprovalRequest, approver: Principal, reason: str | None
    ) -> ApprovalRequestOut:
        if not reason:
            raise self._biz("reason required to reject")
        req.status = "REJECTED"
        req.decision_reason = reason
        if req.step == 1:
            req.first_decided_by = approver.user_id
            req.first_decided_at = datetime.now(UTC)
        else:
            req.second_decided_by = approver.user_id
            req.second_decided_at = datetime.now(UTC)
        await self.db.flush()
        await self._audit_decision(req, approver, "reject", step=req.step)
        return self._to_out(req)

    def _check_step_role(self, req: ApprovalRequest, approver: Principal, two_sided: bool) -> None:
        allowed: tuple[str, ...] = (
            FINANCE_STEP_ROLES.get(req.step, ()) if two_sided else SINGLE_STEP_ROLES
        )
        if approver.role not in allowed:
            raise PermissionDeniedError(f"role {approver.role} not an approver for step {req.step}")

    async def _finance_rule(self, two_sided: bool) -> ApprovalRule:
        code = RULE_TWO_SIDED if two_sided else RULE_SINGLE
        rule = (
            await self.db.execute(select(ApprovalRule).where(ApprovalRule.code == code))
        ).scalar_one_or_none()
        if rule is not None:
            return rule
        rule = ApprovalRule(
            code=code, target_kind="ai_action",
            condition={"field": "amount", "op": ">=", "value": 0, "currency": "VND"},
            approver_role_codes=["CEO"],
            second_approver_role_codes=["DIR"] if two_sided else None,
            sla_hours=DEFAULT_SLA_HOURS, is_active=True, priority=100,
        )  # fmt: skip
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def _two_sided(self, req: ApprovalRequest) -> bool:
        rule = (
            await self.db.execute(select(ApprovalRule).where(ApprovalRule.id == req.rule_id))
        ).scalar_one()
        return rule.second_approver_role_codes is not None

    async def _locked(self, request_id: uuid.UUID) -> ApprovalRequest:
        req = await ApprovalRequestRepository(self.db).locked(request_id)
        if req is None:
            raise ApprovalConflictError("approval request not found")
        return req

    async def _audit_decision(
        self, req: ApprovalRequest, approver: Principal, decision: str, *, step: int
    ) -> None:
        await record_audit(
            self.db, action="platform.approval_decided", target_schema="platform",
            target_table="approval_requests", target_id=req.id,
            metadata={"decision": decision, "step": step, "status": req.status},
        )  # fmt: skip

    def _biz(self, msg: str) -> AppError:
        return AppError(msg, code="BUSINESS_RULE_VIOLATION", status_code=422)

    def _to_out(self, req: ApprovalRequest) -> ApprovalRequestOut:
        return ApprovalRequestOut(
            id=req.id, target_kind="ai_action", target_table=req.target_table,
            target_id=req.target_id, ai_action_id=req.ai_action_id, amount=req.amount,
            currency=req.currency, status=req.status, step=req.step,
            requested_by=req.requested_by, due_at=req.due_at, escalated_at=req.escalated_at,
        )  # fmt: skip

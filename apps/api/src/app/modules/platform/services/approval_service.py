"""Approval workflow (T-305 / T-622, EP-WF-01..03, EP-TASK-19, DEC-155, R-DEC-45).

Rules are read from `platform.approval_rules` (R-DEC-45 §1): step 1 approvers =
`approver_role_codes`, step 2 = `second_approver_role_codes` (NULL → single step). The v2.1
AI-action values are kept (single: CEO,DIR · finance ≥ 500M: CEO → DIR). `RULE-task_reassign`
(MGR, SLA 8 h, escalate DIR — escalation itself is M3.2) is created lazily like the AI rules.

The DB enforces `second_decided_by ∉ {first_decided_by, requested_by}` (CK `distinct_approvers`);
this service also checks `platform:approve`, the step role, the data scope (MGR = own department,
R-DEC-45 §3) and that the decider is not the requester. Rejecting at any step rejects the whole
request. The final `APPROVED` runs `on_approved` in the **same transaction** (04 §10.4); every
request / decision is audited and published to the outbox (`platform.approval_*`, 10 §9.2).

Lives in `platform` because `ENT-ApprovalRequest` is a platform table; other modules open requests
through the public `create_for_*` methods, passing their own `AsyncSession`.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol

from sqlalchemy import ColumnElement, and_, false, or_, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.config import get_config
from app.core.deps import Principal
from app.core.errors import AppError, PermissionDeniedError, ScopeDeniedError
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.platform.models import ApprovalRequest, ApprovalRule
from app.modules.platform.repositories import ApprovalRequestRepository, ApprovalRuleRepository
from app.modules.platform.schemas import (
    ApprovalDetailOut,
    ApprovalRequestOut,
    ApprovalTimelineStep,
)

DEFAULT_SLA_HOURS = 8
RULE_SINGLE = "RULE-ai_action_single"
RULE_TWO_SIDED = "RULE-ai_action_two_sided"
RULE_TASK_REASSIGN = "RULE-task_reassign"
# Lazily created rules (05 §2.5): code → (target_kind, condition, step-1 roles, step-2 roles,
# escalate role). The AI-action values reproduce v2.1 SINGLE_STEP_ROLES / FINANCE_STEP_ROLES.
_FINANCE_COND = {"field": "amount", "op": ">=", "value": 0, "currency": "VND"}
RULE_DEFAULTS: dict[str, tuple[str, dict[str, Any], list[str], list[str] | None, str | None]] = {
    RULE_SINGLE: ("ai_action", _FINANCE_COND, ["CEO", "DIR"], None, None),
    RULE_TWO_SIDED: ("ai_action", _FINANCE_COND, ["CEO"], ["DIR"], None),
    RULE_TASK_REASSIGN: ("task_reassign", {}, ["MGR"], None, "DIR"),
}
_DEPT_SCOPED = frozenset({"MGR"})  # `platform:approve` = `d` (02 §5.6, R-DEC-45 §3)

# Pillar of a rule's target (DIR `platform:approve` = `p`, R-DEC-45 §3): the AI-action rules are
# the finance (VND amount) gate → F; `task_reassign` is a people move → O (02 §7).
RULE_PILLAR: dict[str, str] = {"ai_action": "F", "task_reassign": "O"}

OnApproved = Callable[[ApprovalRequest], Awaitable[None]]
Verdict = Literal["ok", "role", "scope"]


class ApproverLike(Protocol):
    """`Principal` (request) or `auth.ApproverRef` (notification routing)."""

    @property
    def role(self) -> str: ...
    @property
    def department_id(self) -> uuid.UUID | None: ...
    @property
    def scope_pillars(self) -> frozenset[str]: ...


def step_roles(rule: ApprovalRule, step: int) -> tuple[str, ...]:
    roles = rule.approver_role_codes if step == 1 else rule.second_approver_role_codes
    return tuple(roles or ())


def _fallback_role(rule: ApprovalRule, step: int) -> str | None:
    """`escalate_to_role_code` stands in for a department-scoped step role (MGR) — R-DEC-45."""
    if rule.escalate_to_role_code and any(r in _DEPT_SCOPED for r in step_roles(rule, step)):
        return rule.escalate_to_role_code
    return None


def eligible_roles(rule: ApprovalRule, step: int) -> tuple[str, ...]:
    fb = _fallback_role(rule, step)
    return step_roles(rule, step) + ((fb,) if fb else ())


def _needs_fallback(req: ApprovalRequest, staffed: frozenset[uuid.UUID]) -> bool:
    """The request's department has no MGR (or the request has no department)."""
    return req.department_id is None or req.department_id not in staffed


def _in_scope(who: ApproverLike, req: ApprovalRequest, rule: ApprovalRule) -> bool:
    """Data scope of `platform:approve` (02 §5.6): CEO all · DIR pillar of the rule
    (`scope_pillars` empty = every pillar) · MGR own department · others none."""
    if who.role == "CEO":
        return True
    if who.role == "DIR":
        pillar = RULE_PILLAR.get(rule.target_kind)
        return not who.scope_pillars or pillar is None or pillar in who.scope_pillars
    if who.role in _DEPT_SCOPED:
        return who.department_id is not None and req.department_id == who.department_id
    return False


def decide_verdict(
    who: ApproverLike, req: ApprovalRequest, rule: ApprovalRule, staffed: frozenset[uuid.UUID]
) -> Verdict:
    """THE approver rule (R-DEC-45 §3) shared by inbox, detail, decide and notifications.

    1. role ∈ roles of the **current** step — CEO is exempt from scope, never from the role;
       then the data scope (`_in_scope`).
    2. else role = `escalate_to_role_code` of a department-scoped step (DIR for MGR): allowed
       while the request's department has no MGR or `department_id` is NULL — "DIR mọi khối
       thấy khi rule fallback" (no pillar filter on the fallback path).
    `staffed` = departments having an active user of the step's department-scoped role.
    """
    if who.role in step_roles(rule, req.step):
        return "ok" if _in_scope(who, req, rule) else "scope"
    if who.role == _fallback_role(rule, req.step) and _needs_fallback(req, staffed):
        return "ok"
    return "role"


def can_decide(
    who: ApproverLike, req: ApprovalRequest, rule: ApprovalRule, staffed: frozenset[uuid.UUID]
) -> bool:
    return decide_verdict(who, req, rule, staffed) == "ok"


def _grant_sql(
    who: ApproverLike, rule: ApprovalRule, step: int, staffed: frozenset[uuid.UUID] | None
) -> ColumnElement[bool] | None:
    """SQL twin of `decide_verdict(...) == "ok"` for requests of (`rule`, `step`)."""
    grants: list[ColumnElement[bool]] = []
    if who.role in step_roles(rule, step):
        if who.role in _DEPT_SCOPED:
            if who.department_id is not None:
                grants.append(ApprovalRequest.department_id == who.department_id)
        elif who.role == "CEO" or (who.role == "DIR" and _dir_pillar_ok(who, rule)):
            grants.append(true())
    elif staffed is not None and who.role == _fallback_role(rule, step):
        dept = ApprovalRequest.department_id
        grants.append(or_(dept.is_(None), dept.not_in(staffed)) if staffed else true())
    return or_(*grants) if grants else None


def _dir_pillar_ok(who: ApproverLike, rule: ApprovalRule) -> bool:
    pillar = RULE_PILLAR.get(rule.target_kind)
    return not who.scope_pillars or pillar is None or pillar in who.scope_pillars


def _uses_fallback(who: ApproverLike, rule: ApprovalRule, step: int) -> bool:
    return who.role not in step_roles(rule, step) and who.role == _fallback_role(rule, step)


class ApprovalConflictError(AppError):
    status_code, code = 409, "CONFLICT_STATE"


class ApprovalService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ApprovalRequestRepository(db)
        self.rules = ApprovalRuleRepository(db)

    # ---------- open a request ----------
    async def create_for_ai_action(
        self, *, ai_action_id: uuid.UUID, requested_by: uuid.UUID, amount: int | None,
        currency: str, payload: dict[str, Any], is_finance: bool,
    ) -> ApprovalRequest:  # fmt: skip
        """Open an approval request for an AI action; 2-step iff finance ≥ threshold (DEC-155)."""
        threshold = get_config().approval_finance_threshold_vnd
        two_sided = is_finance and amount is not None and amount >= threshold
        rule = await self.rule(RULE_TWO_SIDED if two_sided else RULE_SINGLE)
        return await self._open(
            rule, requested_by=requested_by, payload=payload, ai_action_id=ai_action_id,
            amount=amount, currency=currency, source="AI",
            metadata={"two_sided": two_sided, "ai_action_id": str(ai_action_id)},
        )  # fmt: skip

    async def create_for_task_reassign(
        self, *, task_id: uuid.UUID, department_id: uuid.UUID | None, requested_by: uuid.UUID,
        payload: dict[str, Any], emit: bool = True,
    ) -> ApprovalRequestOut:  # fmt: skip
        """EP-TASK-19 (R-DEC-45): one PENDING `task_reassign` request per task (else 409).
        `emit=False` (seed only, R-DEC-47): no outbox event, no notification."""
        if await self.repo.pending_for("task_reassign", task_id) is not None:
            raise ApprovalConflictError(
                "a reassign request is already pending for this task",
                details={"reason": "pending_request_exists"},
            )
        rule = await self.rule(RULE_TASK_REASSIGN)
        req = await self._open(
            rule, requested_by=requested_by, payload=payload, target_schema="execution",
            target_table="tasks", target_id=task_id, department_id=department_id,
            source="MANUAL", metadata={"task_id": str(task_id)}, emit=emit,
        )  # fmt: skip
        return (await self.outs([req]))[0]

    async def _open(
        self, rule: ApprovalRule, *, requested_by: uuid.UUID, payload: dict[str, Any],
        source: str, metadata: dict[str, Any], currency: str = "VND", emit: bool = True,
        **cols: Any,
    ) -> ApprovalRequest:  # fmt: skip
        req = ApprovalRequest(
            rule_id=rule.id, target_kind=rule.target_kind, payload=payload, currency=currency,
            requested_by=requested_by, status="PENDING", step=1, source=source,
            due_at=datetime.now(UTC) + timedelta(hours=rule.sla_hours), **cols,
        )  # fmt: skip
        self.db.add(req)
        await self.db.flush()
        await record_audit(
            self.db, action="platform.approval_requested", target_schema="platform",
            target_table="approval_requests", target_id=req.id, metadata=metadata,
        )  # fmt: skip
        if not emit:
            return req
        await self._publish("platform.approval_requested", req, rule, {
            "target_id": _s(req.target_id or req.ai_action_id),
            "department_id": _s(req.department_id), "due_at": req.due_at.isoformat(),
        })  # fmt: skip
        await self._notify(await self._approvers(req, rule), req, "approval_requested",
                           "Có yêu cầu chờ bạn duyệt")  # fmt: skip
        return req

    async def _approvers(self, req: ApprovalRequest, rule: ApprovalRule) -> list[uuid.UUID]:
        """Users who `can_decide` the current step (R-DEC-45/46) — same rule as inbox/decide."""
        from app.modules.auth.services.auth_service import AuthService

        roles = list(dict.fromkeys(eligible_roles(rule, req.step)))
        candidates = await AuthService(self.db).approver_candidates(roles)
        staffed = await self._staffed(rule, req.step)
        return [c.user_id for c in candidates
                if c.user_id != req.requested_by and can_decide(c, req, rule, staffed)]  # fmt: skip

    async def _staffed(self, rule: ApprovalRule, step: int) -> frozenset[uuid.UUID]:
        """Departments having an active user of each department-scoped step role (MGR)."""
        from app.modules.auth.services.auth_service import AuthService

        if not rule.escalate_to_role_code:
            return frozenset()
        auth = AuthService(self.db)
        out: set[uuid.UUID] = set()
        for role in step_roles(rule, step):
            if role in _DEPT_SCOPED:
                out |= await auth.departments_with_role(role)
        return frozenset(out)

    async def _notify(
        self, users: Sequence[uuid.UUID], req: ApprovalRequest, kind: str, title: str
    ) -> None:
        from app.modules.platform.services.notification_service import NotificationService

        await NotificationService(self.db).notify_users(
            users, kind=kind, title=title, body=f"approval.{req.target_kind}.title",
            link=f"/work/approvals?id={req.id}", ref_schema="platform",
            ref_table="approval_requests", ref_id=req.id,
        )  # fmt: skip

    async def rule(self, code: str) -> ApprovalRule:
        """Rule by code; the known defaults (`RULE_DEFAULTS`) are created lazily (05 §2.5) with
        `INSERT … ON CONFLICT (code) DO NOTHING` then re-read (safe under concurrent requests)."""
        found = await self.rules.by_code(code)
        if found is not None:
            return found
        kind, cond, first, second, escalate = RULE_DEFAULTS[code]
        await self.rules.insert_if_absent(
            code=code, target_kind=kind, condition=cond, approver_role_codes=first,
            second_approver_role_codes=second, escalate_to_role_code=escalate,
            sla_hours=DEFAULT_SLA_HOURS, is_active=True, priority=100,
        )  # fmt: skip
        created = await self.rules.by_code(code)
        if created is None:  # pragma: no cover — inserted above or by a concurrent transaction
            raise AppError(f"approval rule {code} unavailable")
        return created

    async def approver_roles(self, code: str) -> tuple[tuple[str, ...], str | None]:
        """`(step-1 roles, escalate role)` of a rule — notification routing (R-DEC-46)."""
        r = await self.rule(code)
        return step_roles(r, 1), r.escalate_to_role_code

    # ---------- EP-WF-01 / 02 inbox ----------
    async def _assigned(
        self, user: Principal, rules: Sequence[ApprovalRule], *, include_own: bool = False
    ) -> list[ColumnElement[bool]]:
        """SQL form of `can_decide` (R-DEC-45 §3) per (rule, step); not my own request."""
        steps: list[ColumnElement[bool]] = []
        for r in rules:
            for step in (1, 2):
                if not step_roles(r, step):
                    continue
                staffed = await self._staffed(r, step) if _uses_fallback(user, r, step) else None
                cond = _grant_sql(user, r, step, staffed)
                if cond is not None:
                    steps.append(and_(ApprovalRequest.rule_id == r.id,
                                      ApprovalRequest.step == step, cond))  # fmt: skip
        clauses: list[ColumnElement[bool]] = [or_(*steps) if steps else false()]
        if not include_own:
            clauses.append(ApprovalRequest.requested_by != user.user_id)
        return clauses

    async def inbox(
        self, user: Principal, page: PageParams, *, status: str | None, rule_code: str | None,
        target_kind: str | None,
    ) -> tuple[list[ApprovalRequestOut], int, int]:  # fmt: skip
        rules = await self.rules.all_rules()
        mine = await self._assigned(user, rules)
        where = list(mine)
        if rule_code is not None:
            ids = [r.id for r in rules if r.code == rule_code]
            where.append(ApprovalRequest.rule_id.in_(ids) if ids else false())
        filters = {"status": status or "PENDING"}
        if target_kind is not None:
            filters["target_kind"] = target_kind
        items, total = await self.repo.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters, where=where,
        )  # fmt: skip
        pending = await self.repo.count_where(ApprovalRequest.status == "PENDING", *mine)
        return await self.outs(items, rules), total, pending

    async def detail(self, user: Principal, request_id: uuid.UUID) -> ApprovalDetailOut:
        """EP-WF-02 — outside the caller's approver scope → 404 (10 §7.2.2)."""
        rules = await self.rules.all_rules()
        visible = or_(and_(*await self._assigned(user, rules, include_own=True)),
                      ApprovalRequest.requested_by == user.user_id)  # fmt: skip
        found = await self.repo.where_one(ApprovalRequest.id == request_id, visible)
        if found is None:
            raise AppError("approval request not found", code="NOT_FOUND", status_code=404)
        out = (await self.outs([found], rules))[0]
        return ApprovalDetailOut(**out.model_dump(), payload_diff=_diff(found),
                                 timeline=_timeline(found))  # fmt: skip

    async def outs(
        self, reqs: Sequence[ApprovalRequest], rules: Sequence[ApprovalRule] | None = None
    ) -> list[ApprovalRequestOut]:
        from app.modules.auth.services.auth_service import AuthService

        by_id = ({r.id: r for r in rules} if rules is not None
                 else await self.rules.by_ids(list({q.rule_id for q in reqs})))  # fmt: skip
        names = await AuthService(self.db).user_names([q.requested_by for q in reqs])
        return [self._to_out(q, by_id.get(q.rule_id), names.get(q.requested_by)) for q in reqs]

    # ---------- EP-WF-03 decide (v2.1 EP-125 behaviour) ----------
    async def decide(
        self, approver: Principal, request_id: uuid.UUID, *, decision: str,
        reason: str | None, on_approved: OnApproved | None = None,
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
        rule = (await self.rules.by_ids([req.rule_id]))[req.rule_id]  # FK → always present
        await self._check_can_decide(req, approver, rule)
        # Savepoint: a failing hook (e.g. task version moved → 409) undoes the decision too,
        # so the request stays PENDING even if the caller handles the error (TC-M13-08).
        async with self.db.begin_nested():
            if decision == "reject":
                await self._reject(req, approver, reason)
            else:
                await self._approve(req, approver, rule, on_approved)
        await self._publish("platform.approval_decided", req, rule,
                            {"decision": decision, "status": req.status})  # fmt: skip
        if req.status == "PENDING":  # moved to step 2 → the next approvers
            await self._notify(await self._approvers(req, rule), req, "approval_requested",
                               "Có yêu cầu chờ bạn duyệt")  # fmt: skip
        else:
            await self._notify([req.requested_by], req, "approval_decided",
                               "Yêu cầu của bạn đã được xử lý")  # fmt: skip
        return (await self.outs([req], [rule]))[0]

    # ---------- internals ----------
    async def _approve(
        self, req: ApprovalRequest, approver: Principal, rule: ApprovalRule,
        on_approved: OnApproved | None,
    ) -> None:  # fmt: skip
        now = datetime.now(UTC)
        if req.step == 1:
            if req.requested_by == approver.user_id:
                raise self._biz("approver must differ from requester", reason="self_approval")
            req.first_decided_by = approver.user_id
            req.first_decided_at = now
            if step_roles(rule, 2):
                req.step = 2  # await the second approver; stays PENDING
                await self.db.flush()
                await self._audit_decision(req, approver, "approve", step=1)
                return
        else:  # step 2
            if approver.user_id in (req.requested_by, req.first_decided_by):
                raise self._biz("second approver must be distinct (DEC-155)",
                                reason="distinct_approvers")  # fmt: skip
            req.second_decided_by = approver.user_id
            req.second_decided_at = now
        req.status = "APPROVED"
        await self.db.flush()
        if on_approved is not None:
            await on_approved(req)  # target hook, same transaction (04 §10.4)
        await self._audit_decision(req, approver, "approve", step=req.step)

    async def _reject(self, req: ApprovalRequest, approver: Principal, reason: str | None) -> None:
        if not reason:
            raise self._biz("reason required to reject", field="reason")
        if req.requested_by == approver.user_id:
            raise self._biz("approver must differ from requester", reason="self_approval")
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

    async def _check_can_decide(
        self, req: ApprovalRequest, approver: Principal, rule: ApprovalRule
    ) -> None:
        """EP-WF-03: role not in the step (nor fallback) → 403 ROLE; outside scope → 403 SCOPE."""
        staffed = await self._staffed(rule, req.step)
        verdict = decide_verdict(approver, req, rule, staffed)
        if verdict == "role":
            raise PermissionDeniedError(f"role {approver.role} not an approver for step {req.step}")
        if verdict == "scope":
            raise ScopeDeniedError("request outside the approver's scope",
                                   details={"department_id": _s(req.department_id)})  # fmt: skip

    async def _locked(self, request_id: uuid.UUID) -> ApprovalRequest:
        req = await self.repo.locked(request_id)
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

    async def _publish(
        self, event_type: str, req: ApprovalRequest, rule: ApprovalRule, extra: dict[str, Any]
    ) -> None:
        """`platform.approval_*` outbox event, same tx (10 §9.2) — ids/codes only, no PII."""
        payload = {"approval_request_id": str(req.id), "rule_code": rule.code,
                   "target_kind": req.target_kind, "step": req.step, **extra}  # fmt: skip
        await publish_in_tx(
            self.db, event_type=event_type, producer="platform", aggregate_schema="platform",
            aggregate_table="approval_requests", aggregate_id=req.id, payload=payload,
        )  # fmt: skip

    def _biz(self, msg: str, **details: str) -> AppError:
        """422 with `details.reason` (self_approval / distinct_approvers) or `details.field`."""
        return AppError(msg, code="BUSINESS_RULE_VIOLATION", status_code=422, details=details)

    def _to_out(
        self, req: ApprovalRequest, rule: ApprovalRule | None, name: str | None
    ) -> ApprovalRequestOut:
        return ApprovalRequestOut(
            id=req.id, rule_code=rule.code if rule else None, target_kind=req.target_kind,
            target_table=req.target_table, target_id=req.target_id,
            ai_action_id=req.ai_action_id, amount=req.amount, currency=req.currency,
            status=req.status, step=req.step, requested_by=req.requested_by, due_at=req.due_at,
            escalated_at=req.escalated_at, department_id=req.department_id,
            title_key=f"approval.{req.target_kind}.title", params=_params(req),
            requested_by_name=name, created_at=req.created_at,
            overdue=req.status == "PENDING" and req.due_at < datetime.now(UTC),
        )  # fmt: skip


def _s(v: uuid.UUID | None) -> str | None:
    return str(v) if v is not None else None


def _params(req: ApprovalRequest) -> dict[str, object]:
    """i18n params (no fixed sentence, CLAUDE.md §5.2) — ids / amounts only."""
    if req.target_kind == "task_reassign":
        p = req.payload or {}
        return {k: p.get(k) for k in ("task_id", "from_assignee_id", "to_assignee_id")}
    return {"amount": req.amount, "currency": req.currency} if req.amount is not None else {}


def _diff(req: ApprovalRequest) -> list[dict[str, object]]:
    p = req.payload or {}
    if req.target_kind == "task_reassign":
        return [{"field": "assignee_id", "before": p.get("from_assignee_id"),
                 "after": p.get("to_assignee_id")}]  # fmt: skip
    return [{"field": k, "before": None, "after": v} for k, v in sorted(p.items())]


def _timeline(req: ApprovalRequest) -> list[ApprovalTimelineStep]:
    steps = [ApprovalTimelineStep(step=0, actor_ref=req.requested_by, decision="requested",
                                  reason=(req.payload or {}).get("reason"),
                                  at=req.created_at)]  # fmt: skip
    rejected = req.status == "REJECTED"
    for step, who, at in ((1, req.first_decided_by, req.first_decided_at),
                          (2, req.second_decided_by, req.second_decided_at)):  # fmt: skip
        if who is None:
            continue
        last = rejected and step == req.step
        steps.append(
            ApprovalTimelineStep(
                step=step,
                actor_ref=who,
                decision="reject" if last else "approve",
                reason=req.decision_reason if last else None,
                at=at,
            )
        )
    return steps

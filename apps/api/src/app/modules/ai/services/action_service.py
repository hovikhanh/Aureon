"""AI action lifecycle (T-304, EP-115/116, DEC-134) — propose → confirm/execute → undo 24h.

Resolution (04 §9): `resolve_level` gives the effective autonomy after policy + kill switch.
- **L3** (Act & Notify): execute immediately via the Action Registry, set a 24-hour undo window.
- **L2** (Draft & Confirm): persist a `proposed` action card; a human confirms later. A finance
  action ≥ `APPROVAL_FINANCE_THRESHOLD_VND` additionally opens a 2-sided `ENT-ApprovalRequest`
  (DEC-155) and only executes when it is `APPROVED`.
- **L0/L1**: no write is prepared here (insight/suggestion only).

Confirm (EP-115) needs **both** `ai:write` and the target `<domain>:write` (P06, 10 §4.11).
Undo (EP-116) reverses within 24h; `410 UNDO_EXPIRED` past the window, `409 CONFLICT_STATE`
if the target row changed after commit. The kill switch never blocks a human confirm of an L2
card (the person is the actor) — it only stops L3 auto-execute.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.approval_hooks import register_approval_hook
from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import (
    AppError,
    ConflictStateError,
    NotFoundError,
    PermissionDeniedError,
    ScopeDeniedError,
)
from app.modules.ai.models import AIAction
from app.modules.ai.repositories import AIActionRepository
from app.modules.ai.schemas import AIActionOut
from app.modules.ai.services.action_registry import (
    ActionContext,
    ActionOutcome,
    get_action,
    is_finance_action,
)
from app.modules.ai.services.autonomy import resolve_level
from app.modules.ai.services.tool_audit import log_tool_call, request_uuid
from app.modules.platform.services.approval_service import ApprovalService

UNDO_WINDOW = timedelta(hours=24)  # DEC-134 (AI actions; IDP STP = 7 days)
DEFAULT_AGENT = "ceo"  # M1.6 R-DEC-71 (v2.1 `assistant` kept on old rows)
UNDO_KEY = "_undo"  # internal undo state inside `result_refs[0]` (never returned by the API)


def public_refs(refs: Any) -> list[dict[str, Any]]:
    """`result_refs` as exposed by `AIActionOut` / tool logs — without the undo state."""
    return [{k: v for k, v in dict(r).items() if k != UNDO_KEY} for r in (refs or [])]


class UndoExpiredError(AppError):
    status_code, code = 410, "UNDO_EXPIRED"


class ActionRejectedError(AppError):
    status_code, code = 422, "ACTION_REJECTED"


class ActionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        # undo thunks for actions executed in this request; a later-turn undo rebuilds from refs

    # ---------- propose (from a tool call) ----------
    async def propose(
        self, user: Principal, *, action_name: str, tool_name: str | None,
        input_data: dict[str, Any], idempotency_key: str, amount: int | None = None,
        message_id: uuid.UUID | None = None, agent_code: str = DEFAULT_AGENT,
        expected_outcome: dict[str, Any] | None = None, baseline_status: str | None = None,
    ) -> AIActionOut:  # fmt: skip
        act = get_action(action_name)
        if act is None:
            raise NotFoundError(f"unknown action {action_name}")
        level = await resolve_level(
            self.db, action_name=action_name, role=user.role, amount=amount,
            agent_code=agent_code,
        )  # fmt: skip
        # seed the verification baseline (T-307) so the 24h/7d sweep can measure the outcome
        verification: dict[str, Any] | None = None
        if expected_outcome is not None:
            verification = {
                "expected_outcome": expected_outcome,
                "baseline_status": baseline_status,
            }
        action = AIAction(
            action_name=action_name, tool_name=tool_name, agent_profile_code=agent_code,
            autonomy_level=level, status="proposed", on_behalf_of=user.user_id,
            message_id=message_id, input=input_data, idempotency_key=idempotency_key,
            source="AI", verification=verification, request_id=request_uuid(),
        )  # fmt: skip
        self.db.add(action)
        await self.db.flush()
        await self._audit(action, "ai.action_proposed")
        started = time.monotonic()

        if level == "L3":
            await self._execute(user, action)
        elif level == "L2" and is_finance_action(action_name) and amount is not None:
            await self._maybe_open_approval(user, action, amount)
        if tool_name is not None:  # T-647: the WRITE tool call that created the card
            await log_tool_call(
                self.db, tool_name=tool_name, arguments=input_data,
                status="error" if action.status == "failed" else "ok",
                latency_ms=int((time.monotonic() - started) * 1000), agent_code=agent_code,
                user_id=user.user_id, autonomy_level=level, message_id=message_id,
                result_refs=public_refs(action.result_refs), ai_action_id=action.id,
                approval_request_id=action.approval_request_id,
            )  # fmt: skip
        return self._to_out(action)

    # ---------- confirm / reject (EP-115) ----------
    async def confirm(
        self, user: Principal, action_id: uuid.UUID, *, edited_input: dict[str, Any] | None = None
    ) -> AIActionOut:
        action = await self._locked(action_id)
        self._require_write(user, action)
        if action.status != "proposed":
            raise ConflictStateError("action is not awaiting confirmation")
        if action.approval_request_id is not None:
            raise ConflictStateError("action awaits approval; decide the request first")
        if edited_input is not None:
            action.input = edited_input
        await self._execute(user, action)
        await self._audit(action, "ai.action_confirm")  # EP-AI-09 (10 §7.2.5)
        return self._to_out(action)

    async def reject(self, user: Principal, action_id: uuid.UUID, *, reason: str) -> AIActionOut:
        action = await self._locked(action_id)
        self._require_owner(user, action)  # only the asker decides the card (EP-AI-10)
        if action.status != "proposed":
            raise ConflictStateError("only a proposed action can be rejected")
        action.status = "rejected"
        action.why = reason
        await self.db.flush()
        await self._audit(action, "ai.action_reject", metadata={"reason": reason})
        return self._to_out(action)

    # ---------- undo (EP-116) ----------
    async def undo(
        self, user: Principal, action_id: uuid.UUID, *, reason: str | None = None
    ) -> AIActionOut:
        action = await self._locked(action_id)
        self._require_write(user, action)
        if action.status != "executed":
            raise ConflictStateError("only an executed action can be undone")
        if action.undo_deadline is None or action.undo_deadline < datetime.now(UTC):
            raise UndoExpiredError("undo window (24h) has passed")
        act = get_action(action.action_name)
        if act is None or not act.reversible:
            raise ConflictStateError("action is not reversible")
        await self._undo_from_refs(user, action)
        action.status = "undone"
        action.undone_at = datetime.now(UTC)
        action.undone_by = user.user_id
        await self.db.flush()
        await self._audit(action, "ai.action_undone", metadata={"reason": reason})
        return self._to_out(action)

    async def execute_approved(self, approver: Principal, action_id: uuid.UUID) -> None:
        """Execute an action whose 2-sided approval just finalised (called by EP-WF-03).

        Runs in the approval's transaction (04 §10.4). The approver's `Principal` is the actor;
        the write still re-checks `<domain>:write` at commit time inside the executor.
        """
        action = await self._locked(action_id)
        if action.status != "proposed":
            return  # already executed / undone / rejected
        await self._execute(approver, action)

    # ---------- reads ----------
    async def list_for(
        self, user: Principal, *, status: str | None = None, autonomy_level: str | None = None,
        agent_profile_code: str | None = None,
    ) -> list[AIActionOut]:  # fmt: skip
        """EP-AI-07: own cards; `ai:admin` → whole tenant (SCR-64 queue, 10 §7.2.5)."""
        rows = await AIActionRepository(self.db).list_for_user(
            None if user.has("ai:admin") else user.user_id, status=status,
            autonomy_level=autonomy_level, agent_profile_code=agent_profile_code,
        )  # fmt: skip
        return [self._to_out(a) for a in rows]

    async def get(self, user: Principal, action_id: uuid.UUID) -> AIActionOut:
        action = await self._get(action_id)
        if action.on_behalf_of != user.user_id and not user.has("ai:admin"):
            raise NotFoundError("action not found")
        return self._to_out(action)

    # ---------- internals ----------

    async def _execute(self, user: Principal, action: AIAction) -> None:
        act = get_action(action.action_name)
        if act is None:
            raise NotFoundError(f"unknown action {action.action_name}")
        try:
            params, errors = act.parse(dict(action.input))
            if params is None or errors:
                raise ActionRejectedError(
                    "invalid action input", details={"action_name": act.name, "errors": errors}
                )
            ctx = ActionContext(source="AI", ai_action_id=action.id)
            outcome = await act.run(self.db, user, params, ctx)
        except AppError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            action.status = "failed"
            await self.db.flush()
            raise ActionRejectedError(f"execution failed: {exc}") from exc
        now = datetime.now(UTC)
        action.status = "executed"
        action.executed_at = now
        # `ai_actions.result_refs` keeps its v2.1 shape `{type, id, table: "<schema>.<table>"}`;
        # T-645: the first ref also carries the ACT undo state (`snapshot` of the overwritten
        # fields + `target_version` the write left) — `ai_actions` has no snapshot column
        # (05 §2.8 "không đổi cột"); `_to_out` never exposes these keys.
        action.result_refs = [
            {"type": "record", "id": r["id"], "table": f"{r['schema']}.{r['table']}",
             **({"reused": True} if r.get("reused") else {})}
            for r in outcome.result_refs
        ]  # fmt: skip
        if action.result_refs and (outcome.snapshot is not None or outcome.target_version):
            action.result_refs[0] |= {
                UNDO_KEY: {"snapshot": outcome.snapshot, "target_version": outcome.target_version}
            }
        action.undo_deadline = now + UNDO_WINDOW if act.reversible else None
        await self.db.flush()
        await self._audit(action, "ai.action_executed")

    async def _maybe_open_approval(self, user: Principal, action: AIAction, amount: int) -> None:
        req = await ApprovalService(self.db).create_for_ai_action(
            ai_action_id=action.id, requested_by=user.user_id, amount=amount,
            currency="VND", payload=dict(action.input), is_finance=True,
        )  # fmt: skip
        action.approval_request_id = req.id
        await self.db.flush()

    @staticmethod
    def _require_owner(user: Principal, action: AIAction) -> None:
        if action.on_behalf_of != user.user_id:  # only the asker decides the card (TC-M16-18)
            raise ScopeDeniedError("action belongs to another user")

    def _require_write(self, user: Principal, action: AIAction) -> None:
        self._require_owner(user, action)
        if not user.has("ai:write"):
            raise PermissionDeniedError("missing ai:write")
        act = get_action(action.action_name)
        # the ACT's own any-of permission (`execution:write`, `hr:admin` for structure — R-DEC-61)
        if act is not None and not act.permitted(user):
            raise PermissionDeniedError(f"missing {' | '.join(act.required_permission)}")

    async def _undo_from_refs(self, user: Principal, action: AIAction) -> None:
        """Reverse through the Action Registry v2 `undo` of the ACT (R-DEC-60) from the stored
        `result_refs` — no in-process thunk, so undo works from any later request."""
        act = get_action(action.action_name)
        if act is None or not action.result_refs:
            return
        try:
            refs = [{"schema": r["table"].split(".")[0], "table": r["table"].split(".")[-1],
                     "id": r["id"], "reused": bool(r.get("reused"))}
                    for r in action.result_refs]  # fmt: skip
            state = action.result_refs[0].get(UNDO_KEY) or {}
            await act.undo(self.db, user, ActionOutcome(
                refs, state.get("snapshot"), state.get("target_version")))  # fmt: skip
        except NotFoundError:
            return  # already gone

    async def _get(self, action_id: uuid.UUID) -> AIAction:
        action = await AIActionRepository(self.db).by_id(action_id)
        if action is None:
            raise NotFoundError("action not found")
        return action

    async def _locked(self, action_id: uuid.UUID) -> AIAction:
        action = await AIActionRepository(self.db).by_id(action_id, lock=True)
        if action is None:
            raise NotFoundError("action not found")
        return action

    async def _audit(
        self, action: AIAction, verb: str, *, metadata: dict[str, Any] | None = None
    ) -> None:
        meta = {"autonomy_level": action.autonomy_level, "action_name": action.action_name}
        meta.update(metadata or {})
        await record_audit(
            self.db, action=verb, target_schema="ai", target_table="ai_actions",
            target_id=action.id, metadata=meta,
        )  # fmt: skip

    def _to_out(self, a: AIAction) -> AIActionOut:
        now = datetime.now(UTC)
        can_undo = a.status == "executed" and a.undo_deadline is not None and a.undo_deadline > now
        return AIActionOut(
            id=a.id, action_name=a.action_name, tool_name=a.tool_name,
            autonomy_level=a.autonomy_level,
            status=a.status,
            input_preview=dict(a.input) if a.input else {},
            result_refs=public_refs(a.result_refs), on_behalf_of=a.on_behalf_of,
            approval_request_id=a.approval_request_id, executed_at=a.executed_at,
            undo_deadline=a.undo_deadline, can_undo=can_undo,
            agent_profile_code=a.agent_profile_code,
            request_id=str(a.request_id) if a.request_id else None, created_at=a.created_at,
        )  # fmt: skip


async def _execute_approved_ai_action(
    db: Any, approver: Any, action_id: uuid.UUID, _payload: dict[str, Any]
) -> None:
    """Approval hook for `target_kind="ai_action"` — run the action when its approval finalises.

    Registered in `core.approval_hooks` so `platform` can execute an `ai` action on `APPROVED`
    without importing `ai` (DEC-125 — breaks the module cycle).
    """
    await ActionService(db).execute_approved(approver, action_id)


register_approval_hook("ai_action", _execute_approved_ai_action)

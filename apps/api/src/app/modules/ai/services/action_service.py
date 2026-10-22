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

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.approval_hooks import register_approval_hook
from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import (
    AppError,
    ConflictStateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.ai.models import AIAction
from app.modules.ai.schemas import AIActionOut
from app.modules.ai.services.action_registry import UndoThunk, get_action, is_finance_action
from app.modules.ai.services.autonomy import resolve_level
from app.modules.platform.services.approval_service import ApprovalService

UNDO_WINDOW = timedelta(hours=24)  # DEC-134 (AI actions; IDP STP = 7 days)
DEFAULT_AGENT = "assistant"


class UndoExpiredError(AppError):
    status_code, code = 410, "UNDO_EXPIRED"


class ActionRejectedError(AppError):
    status_code, code = 422, "ACTION_REJECTED"


class ActionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        # undo thunks for actions executed in this request; a later-turn undo rebuilds from refs
        self._undo_registry: dict[uuid.UUID, UndoThunk] = {}

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
            verification = {"expected_outcome": expected_outcome, "baseline_status": baseline_status}
        action = AIAction(
            action_name=action_name, tool_name=tool_name, agent_profile_code=agent_code,
            autonomy_level=level, status="proposed", on_behalf_of=user.user_id,
            message_id=message_id, input=input_data, idempotency_key=idempotency_key,
            source="AI", verification=verification,
        )  # fmt: skip
        self.db.add(action)
        await self.db.flush()
        await self._audit(action, "ai.action_proposed")

        if level == "L3":
            await self._execute(user, action)
        elif level == "L2" and is_finance_action(action_name) and amount is not None:
            await self._maybe_open_approval(user, action, amount)
        return self._to_out(action)

    # ---------- confirm / reject (EP-115) ----------
    async def confirm(
        self, user: Principal, action_id: uuid.UUID, *, edited_input: dict[str, Any] | None = None
    ) -> AIActionOut:
        action = await self._locked(action_id)
        if action.status != "proposed":
            raise ConflictStateError("action is not awaiting confirmation")
        self._require_write(user, action)
        if action.approval_request_id is not None:
            raise ConflictStateError("action awaits approval; decide the request first")
        if edited_input is not None:
            action.input = edited_input
        await self._execute(user, action)
        return self._to_out(action)

    async def reject(self, user: Principal, action_id: uuid.UUID, *, reason: str) -> AIActionOut:
        action = await self._locked(action_id)
        if action.status != "proposed":
            raise ConflictStateError("only a proposed action can be rejected")
        action.status = "rejected"
        action.why = reason
        await self.db.flush()
        await self._audit(action, "ai.action_rejected", metadata={"reason": reason})
        return self._to_out(action)

    # ---------- undo (EP-116) ----------
    async def undo(
        self, user: Principal, action_id: uuid.UUID, *, reason: str | None = None
    ) -> AIActionOut:
        action = await self._locked(action_id)
        if action.status != "executed":
            raise ConflictStateError("only an executed action can be undone")
        if action.undo_deadline is None or action.undo_deadline < datetime.now(UTC):
            raise UndoExpiredError("undo window (24h) has passed")
        self._require_write(user, action)
        act = get_action(action.action_name)
        if act is None or not act.reversible:
            raise ConflictStateError("action is not reversible")
        undo_thunk = self._undo_registry.pop(action.id, None)
        if undo_thunk is not None:
            await undo_thunk()
        else:
            await self._undo_from_refs(user, action)
        action.status = "undone"
        action.undone_at = datetime.now(UTC)
        action.undone_by = user.user_id
        await self.db.flush()
        await self._audit(action, "ai.action_undone", metadata={"reason": reason})
        return self._to_out(action)

    async def execute_approved(self, approver: Principal, action_id: uuid.UUID) -> None:
        """Execute an action whose 2-sided approval just finalised (called by EP-125).

        Runs in the approval's transaction (04 §10.4). The approver's `Principal` is the actor;
        the write still re-checks `<domain>:write` at commit time inside the executor.
        """
        action = await self._locked(action_id)
        if action.status != "proposed":
            return  # already executed / undone / rejected
        await self._execute(approver, action)

    # ---------- reads ----------
    async def list_for(
        self, user: Principal, *, status: str | None = None, autonomy_level: str | None = None
    ) -> list[AIActionOut]:
        stmt = select(AIAction).where(AIAction.on_behalf_of == user.user_id)
        if status is not None:
            stmt = stmt.where(AIAction.status == status)
        if autonomy_level is not None:
            stmt = stmt.where(AIAction.autonomy_level == autonomy_level)
        stmt = stmt.order_by(AIAction.created_at.desc())
        rows = (await self.db.execute(stmt)).scalars().all()
        return [self._to_out(a) for a in rows]

    async def get(self, user: Principal, action_id: uuid.UUID) -> AIActionOut:
        action = await self._get(action_id)
        if action.on_behalf_of != user.user_id:
            raise NotFoundError("action not found")
        return self._to_out(action)

    # ---------- internals ----------

    async def _execute(self, user: Principal, action: AIAction) -> None:
        act = get_action(action.action_name)
        if act is None:
            raise NotFoundError(f"unknown action {action.action_name}")
        try:
            outcome = await act.run(self.db, user, dict(action.input))
        except AppError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            action.status = "failed"
            await self.db.flush()
            raise ActionRejectedError(f"execution failed: {exc}") from exc
        now = datetime.now(UTC)
        action.status = "executed"
        action.executed_at = now
        action.result_refs = outcome.result_refs
        action.undo_deadline = now + UNDO_WINDOW if act.reversible else None
        await self.db.flush()
        self._undo_registry[action.id] = outcome.undo
        await self._audit(action, "ai.action_executed")

    async def _maybe_open_approval(self, user: Principal, action: AIAction, amount: int) -> None:
        req = await ApprovalService(self.db).create_for_ai_action(
            ai_action_id=action.id, requested_by=user.user_id, amount=amount,
            currency="VND", payload=dict(action.input), is_finance=True,
        )  # fmt: skip
        action.approval_request_id = req.id
        await self.db.flush()

    def _require_write(self, user: Principal, action: AIAction) -> None:
        if not user.has("ai:write"):
            raise PermissionDeniedError("missing ai:write")
        act = get_action(action.action_name)
        domain = act.module if act else None
        if domain and not user.has(f"{domain}:write"):
            raise PermissionDeniedError(f"missing {domain}:write")

    async def _undo_from_refs(self, user: Principal, action: AIAction) -> None:
        """Reverse from `result_refs` when the in-request undo thunk is gone (e.g. a later turn).

        Only `execution.tasks` is wired as reversible in v2.0; reverse via the execution public
        service (DEC-125 — no cross-module model import).
        """
        from app.modules.execution.services.task_service import TaskService

        for ref in action.result_refs or []:
            if ref.get("table") == "execution.tasks":
                try:
                    await TaskService(self.db).delete(user, uuid.UUID(ref["id"]))
                except NotFoundError:
                    continue

    async def _get(self, action_id: uuid.UUID) -> AIAction:
        action = (
            await self.db.execute(select(AIAction).where(AIAction.id == action_id))
        ).scalar_one_or_none()
        if action is None:
            raise NotFoundError("action not found")
        return action

    async def _locked(self, action_id: uuid.UUID) -> AIAction:
        action = (
            await self.db.execute(
                select(AIAction).where(AIAction.id == action_id).with_for_update()
            )
        ).scalar_one_or_none()
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
            result_refs=list(a.result_refs or []), on_behalf_of=a.on_behalf_of,
            approval_request_id=a.approval_request_id, executed_at=a.executed_at,
            undo_deadline=a.undo_deadline, can_undo=can_undo,
        )  # fmt: skip


async def _execute_approved_ai_action(db: Any, approver: Any, action_id: uuid.UUID) -> None:
    """Approval hook for `target_kind="ai_action"` — run the action when its approval finalises.

    Registered in `core.approval_hooks` so `platform` can execute an `ai` action on `APPROVED`
    without importing `ai` (DEC-125 — breaks the module cycle).
    """
    await ActionService(db).execute_approved(approver, action_id)


register_approval_hook("ai_action", _execute_approved_ai_action)

"""EP-ADM-13/14 onboarding state machine (10 §7.2.5, 05 §2.8, 06 §3.4 SCR-66, R-DEC-75/77).

State = `platform.system_settings` key `onboarding.state` (no new table); `version` is the row's
`system_settings.version` (optimistic lock, 0 = no row). Transitions:

- `start`: not_started → in_progress (`started_at/by`); already in_progress/completed → current
  state returned unchanged (idempotent, no audit). The only action without `version`.
- `complete_step` / `skip_step` / `reopen_step` (needs `step`, status in_progress): step → done /
  skipped / in_progress. Only `goals_import` may be skipped; `finish` is reached via `finish`.
  `refs` (codes only) are merged into the step and the top-level `refs`.
- `finish`: required steps (`company`, `org_import`, `users`) not `done` → 422
  `BUSINESS_RULE_VIOLATION` `details.missing_steps[]`; else completed + `platform.onboarding_
  completed` (counts only, no PII / `reason`).
- `reset` (needs `reason`): allowed when `DEMO_MODE=true` or status ≠ completed → not_started.

Every applied action: audit `platform.onboarding_<action>` in the same transaction.
`progress` is derived through `core/onboarding` sources (hr/auth/execution) — never the client.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.config import get_config
from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ValidationError
from app.core.events.outbox import publish_in_tx
from app.core.onboarding import collect_progress
from app.modules.platform.schemas import (
    OnboardingPatchIn,
    OnboardingProgressOut,
    OnboardingStateOut,
)
from app.modules.platform.services.settings_service import SystemSettingService

KEY = "onboarding.state"
STEPS = ("company", "org_import", "review", "users", "goals_import", "finish")
REQUIRED = ("company", "org_import", "users")
SKIPPABLE = frozenset({"goals_import"})
STEP_ACTIONS = {"complete_step": "done", "skip_step": "skipped", "reopen_step": "in_progress"}
# `refs` carry codes only (05 §2.8): ids + counts, never names / emails.
REF_KEYS = {
    "organization_id": "uuid", "org_import_id": "uuid", "goals_import_id": "uuid",
    "document_ids": "uuids", "import_id": "uuid", "document_id": "uuid", "count": "int",
    "rows": "int", "users_created": "int",
}  # fmt: skip
ONE_DAY = timedelta(hours=24)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _blank() -> dict[str, Any]:
    return {
        "status": "not_started", "started_at": None, "completed_at": None, "started_by": None,
        "steps": {s: {"status": "pending", "updated_at": None, "refs": {}} for s in STEPS},
        "refs": {},
    }  # fmt: skip


def _uuid(v: Any) -> str:
    return str(uuid.UUID(str(v)))


def clean_refs(refs: dict[str, Any] | None) -> dict[str, Any]:
    """Whitelisted keys with uuid / int values only → else 422 (unknown key or PII)."""
    out: dict[str, Any] = {}
    for k, v in (refs or {}).items():
        kind = REF_KEYS.get(k)
        try:
            if kind == "uuid":
                out[k] = _uuid(v)
            elif kind == "uuids" and isinstance(v, list):
                out[k] = [_uuid(x) for x in v]
            elif kind == "int" and isinstance(v, int) and not isinstance(v, bool) and v >= 0:
                out[k] = v
            else:
                raise ValueError(k)
        except (ValueError, TypeError, AttributeError):
            raise ValidationError(
                "refs accept ids and counts only", details={"field": f"refs.{k}"}
            ) from None
    return out


TOP_REFS = ("organization_id", "org_import_id", "goals_import_id", "document_ids")


class OnboardingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = SystemSettingService(db)

    async def get(self) -> OnboardingStateOut:
        row = await self.settings.get(KEY)
        state = _blank() | (row.value if row else {})
        return await self._out(state, row.version if row else 0)

    async def _out(self, state: dict[str, Any], version: int) -> OnboardingStateOut:
        progress = OnboardingProgressOut(**await collect_progress(self.db))
        return OnboardingStateOut(**state, version=version, progress=progress)

    async def apply(self, user: Principal, body: OnboardingPatchIn) -> OnboardingStateOut:
        row = await self.settings.get(KEY)
        version = row.version if row else 0
        state = _blank() | (row.value if row else {})
        refs = clean_refs(body.refs)
        if body.action == "start":
            if state["status"] != "not_started":
                return await self._out(state, version)  # idempotent
            state |= {
                "status": "in_progress",
                "started_at": _now(),
                "started_by": str(user.user_id),
            }
        else:
            if body.version is None:
                raise ValidationError("version is required", details={"field": "version"})
            self._transition(state, body, refs)
        state["refs"] = state["refs"] | {k: v for k, v in refs.items() if k in TOP_REFS}
        reason = (body.reason or "").strip() or f"onboarding {body.action}"
        saved = await self.settings.set(
            KEY, state, reason=reason, updated_by=user.user_id,
            expected_version=version if body.action == "start" else body.version,
        )  # fmt: skip
        sid = await self.settings.id_of(KEY)
        await record_audit(
            self.db, action=f"platform.onboarding_{body.action}", target_schema="platform",
            target_table="system_settings", target_id=sid,
            metadata={"step": body.step, "status": state["status"], "refs": refs},
            why=body.reason,
        )  # fmt: skip
        out = await self._out(state, saved.version)
        if body.action == "finish":
            await self._completed_event(sid, state, out.progress)
        return out

    def _transition(
        self, state: dict[str, Any], body: OnboardingPatchIn, refs: dict[str, Any]
    ) -> None:
        action, status = body.action, state["status"]
        if action == "reset":
            if not (body.reason or "").strip():
                raise ValidationError("reason is required", details={"field": "reason"})
            if status == "completed" and not get_config().demo_mode:
                raise BusinessRuleError("onboarding already completed",
                                        details={"reason": "completed_not_demo"})  # fmt: skip
            state.clear()
            state.update(_blank())
            return
        if status != "in_progress":
            raise BusinessRuleError(
                f"onboarding is {status}", details={"reason": "not_in_progress"}
            )
        if action == "finish":
            missing = [s for s in REQUIRED if state["steps"][s]["status"] != "done"]
            if missing:
                raise BusinessRuleError("required steps are not done",
                                        details={"missing_steps": missing})  # fmt: skip
            now = _now()
            state["steps"]["finish"] = {"status": "done", "updated_at": now, "refs": {}}
            state |= {"status": "completed", "completed_at": now}
            return
        step = body.step
        if step is None or step == "finish":
            raise ValidationError("a wizard step is required", details={"field": "step"})
        if action == "skip_step" and step not in SKIPPABLE:
            raise BusinessRuleError("step cannot be skipped", details={"reason": "not_skippable"})
        cur = state["steps"][step]
        state["steps"][step] = {"status": STEP_ACTIONS[action], "updated_at": _now(),
                                "refs": cur.get("refs", {}) | refs}  # fmt: skip

    async def _completed_event(
        self, sid: uuid.UUID, state: dict[str, Any], p: OnboardingProgressOut
    ) -> None:
        started = datetime.fromisoformat(state["started_at"])
        completed = datetime.fromisoformat(state["completed_at"])
        spent = completed - started
        await publish_in_tx(
            self.db, event_type="platform.onboarding_completed", producer="platform",
            aggregate_schema="platform", aggregate_table="system_settings", aggregate_id=sid,
            payload={
                "started_at": state["started_at"], "completed_at": state["completed_at"],
                "duration_minutes": int(spent.total_seconds() // 60),
                "within_one_day": spent <= ONE_DAY,
                "counts": {"departments": p.departments, "employees": p.employees,
                           "users": sum(p.users_by_role.values()), "kpis": p.kpis,
                           "objectives": p.objectives},
            },
        )  # fmt: skip

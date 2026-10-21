"""`verify_action_outcome` sweep (07 §5.6, 03 §7.3, AI-R10) — hourly beat catch-up job.

For each executed L2/L3 `ENT-AIAction` whose 24h / 7d checkpoint has passed and is not yet in
`verification.checks`, append one check. v2.0 rule (no LLM, no cross-schema read): actions
without an `expected_outcome` → `not_measurable`; undone/failed actions are skipped by the
status filter. Comparing against target modules' services is wired by T-315 (DEC-206).
Idempotent per `(ai_action_id, checkpoint)`. Caller commits.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.ai.models import AIAction

CHECKPOINTS = (("24h", timedelta(hours=24)), ("7d", timedelta(days=7)))
LEVELS = ("L2", "L3")


def due_checkpoints(a: AIAction, now: datetime) -> list[str]:
    if a.executed_at is None:
        return []
    done = {c.get("at") for c in (a.verification or {}).get("checks", [])}
    return [cp for cp, delta in CHECKPOINTS if now >= a.executed_at + delta and cp not in done]


def evaluate(expected: Any) -> tuple[str, Any]:
    """Rule-based comparison placeholder: without a measurable target → `not_measurable`."""
    return "not_measurable", None if expected is None else {"expected": expected}


async def verify_action_outcomes(db: AsyncSession, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    stmt = select(AIAction).where(
        AIAction.status == "executed", AIAction.autonomy_level.in_(LEVELS),
        AIAction.executed_at.is_not(None), AIAction.executed_at <= now - CHECKPOINTS[0][1],
    )  # fmt: skip
    written = 0
    for a in (await db.execute(stmt)).scalars():
        for cp in due_checkpoints(a, now):
            ver = dict(a.verification or {})
            result, actual = evaluate(ver.get("expected_outcome"))
            check = {"at": cp, "result": result, "actual": actual, "checked_at": now.isoformat()}
            ver["checks"] = [*ver.get("checks", []), check]
            a.verification = ver
            await record_audit(
                db, action="ai.action.verify", target_schema="ai", target_table="ai_actions",
                target_id=a.id, before=None, after={"checkpoint": cp, "result": result},
            )  # fmt: skip
            written += 1
    await db.flush()
    return written

"""`verify_action_outcome` sweep (07 §5.6, 03 §7.3, AI-R10) — hourly beat catch-up job.

For each executed L2/L3 `ENT-AIAction` whose 24h / 7d checkpoint has passed and is not yet in
`verification.checks`, append one check (AI-R10 — "yêu cầu evidence + verification 24h/7d").

Comparison (no LLM, system-level read): an action whose `expected_outcome.metric_id` names a
metric is scored against that metric's **current company status** versus the `baseline_status`
captured at execution — `improved` (status rank fell), `worsened` (rose), `unchanged` (equal).
Actions with no measurable `metric_id` / no baseline → `not_measurable`; undone/failed actions are
skipped by the status filter. Metric values are read through the `platform` public
`MetricQueryService` (DEC-125 — no cross-schema query). Idempotent per `(ai_action_id, checkpoint)`.
Caller commits.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.modules.ai.models import AIAction
from app.modules.platform.services.metric_query import MetricQueryService

CHECKPOINTS = (("24h", timedelta(hours=24)), ("7d", timedelta(days=7)))
LEVELS = ("L2", "L3")
# worse ← → better; a lower rank is a healthier metric status
STATUS_RANK = {"ok": 0, "no_data": 1, "warning": 2, "critical": 3}


def due_checkpoints(a: AIAction, now: datetime) -> list[str]:
    if a.executed_at is None:
        return []
    done = {c.get("at") for c in (a.verification or {}).get("checks", [])}
    return [cp for cp, delta in CHECKPOINTS if now >= a.executed_at + delta and cp not in done]


def evaluate(
    expected: Any, baseline_status: str | None, current_status: str | None
) -> tuple[str, Any]:
    """Score the outcome from the metric's status movement.

    Needs a measurable `metric_id`, a captured `baseline_status`, and a resolvable
    `current_status`; otherwise `not_measurable`. A lower `STATUS_RANK` is healthier, so a fall is
    `improved`, a rise is `worsened`, equality is `unchanged`.
    """
    metric_id = expected.get("metric_id") if isinstance(expected, dict) else None
    if metric_id is None or baseline_status is None or current_status is None:
        actual = {"expected": expected} if expected is not None else None
        return "not_measurable", actual
    base = STATUS_RANK.get(baseline_status)
    cur = STATUS_RANK.get(current_status)
    actual = {"metric_id": metric_id, "baseline_status": baseline_status,
              "current_status": current_status}  # fmt: skip
    if base is None or cur is None:
        return "not_measurable", actual
    if cur < base:
        return "improved", actual
    if cur > base:
        return "worsened", actual
    return "unchanged", actual


async def verify_action_outcomes(db: AsyncSession, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    stmt = select(AIAction).where(
        AIAction.status == "executed", AIAction.autonomy_level.in_(LEVELS),
        AIAction.executed_at.is_not(None), AIAction.executed_at <= now - CHECKPOINTS[0][1],
    )  # fmt: skip
    actions = list((await db.execute(stmt)).scalars())
    status_by_code = await _current_statuses(db, actions)
    written = 0
    for a in actions:
        due = due_checkpoints(a, now)
        if not due:
            continue
        ver = dict(a.verification or {})
        expected = ver.get("expected_outcome")
        metric_id = expected.get("metric_id") if isinstance(expected, dict) else None
        current_status = status_by_code.get(metric_id) if metric_id else None
        for cp in due:
            result, actual = evaluate(expected, ver.get("baseline_status"), current_status)
            check = {"at": cp, "result": result, "actual": actual, "checked_at": now.isoformat()}
            ver = dict(a.verification or {})
            ver["checks"] = [*ver.get("checks", []), check]
            a.verification = ver
            await record_audit(
                db, action="ai.action.verify", target_schema="ai", target_table="ai_actions",
                target_id=a.id, before=None, after={"checkpoint": cp, "result": result},
            )  # fmt: skip
            written += 1
    await db.flush()
    return written


async def _current_statuses(db: AsyncSession, actions: list[AIAction]) -> dict[str, str]:
    """Current company status per metric referenced by any pending expected_outcome."""
    codes: set[str] = set()
    for a in actions:
        exp = (a.verification or {}).get("expected_outcome")
        if isinstance(exp, dict) and exp.get("metric_id"):
            codes.add(exp["metric_id"])
    if not codes:
        return {}
    values = await MetricQueryService(db).current_values(codes=codes)
    return {v.metric_code: v.status for v in values}

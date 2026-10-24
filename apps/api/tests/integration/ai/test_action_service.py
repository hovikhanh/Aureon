"""T-304/305/306 — AI action lifecycle, undo 24h, 2-sided approval, kill switch.

TC-AI-012 (actions + undo), TC-AI-013 (approval 2-sided), TC-AI-014 (kill switch).
Runs against the seeded dev DB inside the rolled-back `db_session`.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.deps import Principal
from app.core.errors import ConflictStateError, PermissionDeniedError
from app.modules.ai.schemas import KillSwitchIn
from app.modules.ai.services.action_service import ActionService, UndoExpiredError
from app.modules.ai.services.autonomy import resolve_level
from app.modules.ai.services.kill_switch_service import KillSwitchService
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.platform.services.approval_service import ApprovalService

pytestmark = pytest.mark.integration


def principal(role: str, user_id: uuid.UUID | None = None) -> Principal:
    return Principal(
        user_id=user_id or uuid.uuid4(), role=role,
        permissions=frozenset(ROLE_PERMISSIONS[role]),
    )  # fmt: skip


# ---------- T-304: lifecycle + undo ----------
async def test_ceiling_l2_caps_seed_l3_to_a_proposed_card(db_session) -> None:
    """R-DEC-72: seed default L3 (ACT-create_task) → effective L2 at the M1 ceiling."""
    svc = ActionService(db_session)
    out = await svc.propose(
        principal("CEO"), action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data={"title": "AI task from meeting", "status": "todo"},
        idempotency_key="act-l2-cap-1",
    )  # fmt: skip
    assert out.autonomy_level == "L2"
    assert out.status == "proposed"
    assert out.result_refs in (None, [])


async def test_l3_action_auto_executes_with_24h_undo_window(db_session, ceiling_l3) -> None:
    svc = ActionService(db_session)
    ceo = principal("CEO")
    out = await svc.propose(
        ceo, action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data={"title": "AI task from meeting", "status": "todo"},
        idempotency_key="act-l3-1",
    )  # fmt: skip
    assert out.autonomy_level == "L3"
    assert out.status == "executed"
    assert out.can_undo is True
    assert out.result_refs and out.result_refs[0]["table"] == "execution.tasks"
    assert out.undo_deadline is not None
    assert out.undo_deadline - datetime.now(UTC) > timedelta(hours=23)
    # provenance (05 §2.5): task_source "ai" + source_ref → the ENT-AIAction
    from sqlalchemy import select

    from app.modules.execution.models import Task

    tid = uuid.UUID(out.result_refs[0]["id"])
    t = (await db_session.execute(select(Task).where(Task.id == tid))).scalar_one()
    assert (t.task_source, t.source_ref) == ("ai", {"kind": "ai_action", "id": str(out.id)})


async def test_undo_reverses_within_window(db_session, ceiling_l3) -> None:
    svc = ActionService(db_session)
    ceo = principal("CEO")
    out = await svc.propose(
        ceo, action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data={"title": "undo me", "status": "todo"}, idempotency_key="act-undo-1",
    )  # fmt: skip
    undone = await svc.undo(ceo, out.id, reason="mistake")
    assert undone.status == "undone"
    # the underlying task row is soft-deleted
    from sqlalchemy import select

    from app.modules.execution.models import Task

    task_id = uuid.UUID(out.result_refs[0]["id"])
    task = (await db_session.execute(select(Task).where(Task.id == task_id))).scalar_one()
    assert task.deleted_at is not None


async def test_undo_past_window_is_expired(db_session, ceiling_l3) -> None:
    svc = ActionService(db_session)
    ceo = principal("CEO")
    out = await svc.propose(
        ceo, action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data={"title": "stale", "status": "todo"}, idempotency_key="act-stale-1",
    )  # fmt: skip
    # force the deadline into the past
    action = await svc._locked(out.id)
    action.undo_deadline = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.flush()
    with pytest.raises(UndoExpiredError):
        await svc.undo(ceo, out.id, reason="too late")


async def test_confirm_requires_ai_write_and_domain_write(db_session) -> None:
    svc = ActionService(db_session)
    # EMPLOYEE lacks execution:write for a confirm; build a proposed L2 by kill-switching to L2
    await KillSwitchService(db_session).set(
        principal("ADM"), KillSwitchIn(enabled=True, mode="WRITE_OFF", agents=[], reason="t")
    )
    emp = principal("EMP")
    out = await svc.propose(
        emp, action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data={"title": "needs confirm", "status": "todo"}, idempotency_key="act-l2-1",
    )  # fmt: skip
    assert out.autonomy_level == "L2"
    assert out.status == "proposed"
    # strip execution:write to prove the confirm gate
    no_exec = Principal(
        user_id=emp.user_id,
        role="EMP",
        permissions=frozenset(p for p in ROLE_PERMISSIONS["EMP"] if p != "execution:write"),
    )
    with pytest.raises(PermissionDeniedError):
        await svc.confirm(no_exec, out.id)


async def test_reject_a_proposed_action(db_session) -> None:
    svc = ActionService(db_session)
    await KillSwitchService(db_session).set(
        principal("ADM"), KillSwitchIn(enabled=True, mode="WRITE_OFF", agents=[], reason="t")
    )
    ceo = principal("CEO")
    out = await svc.propose(
        ceo, action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data={"title": "reject me", "status": "todo"}, idempotency_key="act-rej-1",
    )  # fmt: skip
    rejected = await svc.reject(ceo, out.id, reason="not needed")
    assert rejected.status == "rejected"
    with pytest.raises(ConflictStateError):
        await svc.confirm(ceo, out.id)


# ---------- T-305: 2-sided approval (DEC-155) ----------
async def test_finance_over_threshold_needs_two_distinct_approvers(db_session) -> None:
    svc = ApprovalService(db_session)
    requester = uuid.uuid4()
    req = await svc.create_for_ai_action(
        ai_action_id=uuid.uuid4(), requested_by=requester, amount=600_000_000,
        currency="VND", payload={"kind": "expense"}, is_finance=True,
    )  # fmt: skip
    assert req.status == "PENDING" and req.step == 1
    r1 = await svc.decide(principal("CEO"), req.id, decision="approve", reason=None)
    assert r1.step == 2 and r1.status == "PENDING"  # waiting on the second approver
    r2 = await svc.decide(principal("DIR"), req.id, decision="approve", reason=None)
    assert r2.status == "APPROVED"


async def test_finance_under_threshold_is_single_step(db_session) -> None:
    svc = ApprovalService(db_session)
    req = await svc.create_for_ai_action(
        ai_action_id=uuid.uuid4(), requested_by=uuid.uuid4(), amount=100_000_000,
        currency="VND", payload={}, is_finance=True,
    )  # fmt: skip
    r = await svc.decide(principal("CEO"), req.id, decision="approve", reason=None)
    assert r.status == "APPROVED"


async def test_non_approver_role_cannot_decide(db_session) -> None:
    svc = ApprovalService(db_session)
    req = await svc.create_for_ai_action(
        ai_action_id=uuid.uuid4(), requested_by=uuid.uuid4(), amount=100_000_000,
        currency="VND", payload={}, is_finance=True,
    )  # fmt: skip
    with pytest.raises(PermissionDeniedError):
        await svc.decide(principal("EMP"), req.id, decision="approve", reason=None)


# ---------- T-306: kill switch ----------
async def test_kill_switch_write_off_downgrades_l3_to_l2(db_session) -> None:
    await KillSwitchService(db_session).set(
        principal("ADM"), KillSwitchIn(enabled=True, mode="WRITE_OFF", agents=[], reason="risk")
    )
    level = await resolve_level(
        db_session, action_name="ACT-create_task", role="CEO", amount=None,
        agent_code="assistant",
    )  # fmt: skip
    assert level == "L2"


async def test_kill_switch_l0_blocks_preparation(db_session) -> None:
    await KillSwitchService(db_session).set(
        principal("ADM"), KillSwitchIn(enabled=True, mode="L0", agents=[], reason="incident")
    )
    level = await resolve_level(
        db_session, action_name="ACT-create_task", role="CEO", amount=None,
        agent_code="assistant",
    )  # fmt: skip
    assert level == "L0"


async def test_kill_switch_per_agent_scope(db_session, ceiling_l3) -> None:
    # engage only for agent "reporting" — "ceo" stays L3 (ceiling L3 = M3.2 config)
    await KillSwitchService(db_session).set(
        principal("ADM"),
        KillSwitchIn(enabled=True, mode="L0", agents=["reporting"], reason="scoped"),
    )
    ceo = await resolve_level(
        db_session, action_name="ACT-create_task", role="CEO", amount=None, agent_code="ceo",
    )  # fmt: skip
    reporting = await resolve_level(
        db_session, action_name="ACT-create_task", role="CEO", amount=None,
        agent_code="reporting",
    )  # fmt: skip
    assert ceo == "L3"
    assert reporting == "L0"


# ---------- T-307: outcome verification 24h/7d ----------
def test_evaluate_scores_status_movement() -> None:
    from app.modules.ai.services.verification import evaluate

    exp = {"metric_id": "METRIC-F-01", "target": "về ngưỡng"}
    assert evaluate(exp, "critical", "ok")[0] == "improved"
    assert evaluate(exp, "warning", "critical")[0] == "worsened"
    assert evaluate(exp, "warning", "warning")[0] == "unchanged"
    # no metric_id, no baseline, or no current reading → not measurable
    assert evaluate({"target": "x"}, "critical", "ok")[0] == "not_measurable"
    assert evaluate(exp, None, "ok")[0] == "not_measurable"
    assert evaluate(exp, "warning", None)[0] == "not_measurable"


async def test_proposed_action_seeds_verification_baseline(db_session) -> None:
    svc = ActionService(db_session)
    ceo = principal("CEO")
    out = await svc.propose(
        ceo, action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data={"title": "fix the metric", "status": "todo"}, idempotency_key="act-ver-1",
        expected_outcome={"metric_id": "METRIC-F-01", "target": "về ngưỡng"},
        baseline_status="critical",
    )  # fmt: skip
    action = await svc._locked(out.id)
    assert action.verification["expected_outcome"]["metric_id"] == "METRIC-F-01"
    assert action.verification["baseline_status"] == "critical"


async def test_verification_sweep_measures_against_current_metric(db_session, ceiling_l3) -> None:
    from app.modules.ai.services.verification import verify_action_outcomes
    from app.modules.platform.services.metric_query import MetricQueryService

    # anchor the baseline on any current company metric value
    values = await MetricQueryService(db_session).current_values()
    assert values, "seed should have company metric values"
    mv = values[0]
    svc = ActionService(db_session)
    ceo = principal("CEO")
    # baseline deliberately one notch worse than current so the sweep scores "improved"
    worse = {"ok": "warning", "no_data": "warning", "warning": "critical", "critical": "critical"}
    out = await svc.propose(
        ceo, action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data={"title": "verify sweep", "status": "todo"}, idempotency_key="act-ver-2",
        expected_outcome={"metric_id": mv.metric_code, "target": "về ngưỡng"},
        baseline_status=worse[mv.status],
    )  # fmt: skip
    # force the action past the 24h checkpoint
    action = await svc._locked(out.id)
    action.executed_at = datetime.now(UTC) - timedelta(hours=30)
    await db_session.flush()
    written = await verify_action_outcomes(db_session, datetime.now(UTC))
    assert written >= 1
    action = await svc._locked(out.id)
    check = action.verification["checks"][0]
    expected = "unchanged" if worse[mv.status] == mv.status else "improved"
    assert check["result"] == expected


async def test_kill_switch_status_roundtrip(db_session) -> None:
    svc = KillSwitchService(db_session)
    assert (await svc.status()).enabled is False
    await svc.set(
        principal("ADM"), KillSwitchIn(enabled=True, mode="WRITE_OFF", agents=[], reason="x")
    )
    st = await svc.status()
    assert st.enabled is True and st.mode == "WRITE_OFF"


async def test_propose_refuses_card_the_asker_cannot_confirm_m16(db_session) -> None:
    """M1.6 review: no ACT structure card for a role outside `hr:admin` (R-DEC-61) — `propose`
    applies the ACT's own permission + pillar check (`ActionDef.permitted`) up front."""
    with pytest.raises(PermissionDeniedError):
        await ActionService(db_session).propose(
            principal("EMP"), action_name="ACT-create_department",
            tool_name="TOOL-create_department",
            input_data={"code": "X-REV", "name": "Review"}, idempotency_key="act-perm-1",
        )  # fmt: skip

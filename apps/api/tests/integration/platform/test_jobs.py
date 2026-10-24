"""TC-EVT-006 (T-235): beat schedule has the 5 business jobs + relay; each job runs end-to-end.

Celery task bodies run against the rolled-back `db_session` (no real commit).
"""

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from celery.schedules import crontab
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import AIAction
from app.modules.ai.services.verification import due_checkpoints, verify_action_outcomes
from app.worker import celery_app
from app.workers import jobs, notifications

EXPECTED = {
    "daily-burn-check": ("app.jobs.daily_burn_check", "9", "0"),
    "mark-invoices-overdue": ("app.jobs.mark_invoices_overdue", "10", "0"),
    "detect-late-hiring": ("app.jobs.detect_late_hiring", "11", "0"),
    "detect-overdue-tasks": ("app.jobs.detect_overdue_tasks", "8", "30"),
    "verify-action-outcome": ("app.jobs.verify_action_outcome", "*", "5"),
    "recompute-metrics": ("app.jobs.recompute_metrics", "1", "0"),
    "check-review-sla": ("app.jobs.check_review_sla", "*", "15"),  # T-412 IDP SLA escalation
}


def _hours(c: crontab) -> str:
    return "*" if c._orig_hour == "*" else str(c._orig_hour)


def test_beat_schedule_registers_jobs() -> None:
    sched = celery_app.conf.beat_schedule
    assert sched["relay-outbox-events"]["schedule"] == 2.0
    for key, (task, hour, minute) in EXPECTED.items():
        entry = sched[key]
        assert entry["task"] == task and task in celery_app.tasks
        assert _hours(entry["schedule"]) == hour and str(entry["schedule"]._orig_minute) == minute
    assert celery_app.conf.timezone == "Asia/Ho_Chi_Minh"
    # 5 DEC-203 jobs + 01:00 recompute + task_overdue (T-131) + relay + check-review-sla (T-412)
    # + notification e-mail sweep (T-616b) + KR at-risk 07:00 + Friday check-in reminder (T-629)
    assert len(sched) == 11
    assert sched["execution.kr_at_risk"]["task"] in celery_app.tasks
    remind = sched["execution.checkin_reminder"]
    assert remind["task"] in celery_app.tasks and remind["schedule"]._orig_day_of_week == 5
    assert _hours(remind["schedule"]) == "8"
    mail = sched["dispatch-notification-emails"]
    assert mail["task"] == notifications.dispatch_email.name and mail["task"] in celery_app.tasks


@pytest.fixture
def in_session(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> AsyncSession:
    async def run(job: Callable[[AsyncSession], Awaitable[Any]]) -> Any:
        out = await job(db_session)
        await db_session.flush()
        return out

    monkeypatch.setattr(jobs, "_run", run)
    return db_session


async def test_job_bodies_run(in_session: AsyncSession) -> None:
    assert isinstance(await jobs._run(jobs.burn_check), bool)
    assert await jobs._run(jobs.invoices_overdue) >= 0
    assert await jobs._run(jobs.late_hiring) >= 0
    assert await jobs._run(jobs.overdue_tasks) >= 0
    stats = await jobs._run(jobs.recompute)
    assert stats["values"] > 0 and stats["failed_providers"] == 0
    assert await jobs._run(verify_action_outcomes) >= 0


def test_celery_wrappers(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(coro: Any) -> Any:
        coro.close()
        return 3

    monkeypatch.setattr(jobs.asyncio, "run", fake_run)
    assert jobs.daily_burn_check.run() is True
    assert jobs.mark_invoices_overdue.run() == 3
    assert jobs.detect_late_hiring.run() == 3
    assert jobs.verify_action_outcome.run() == 3
    assert jobs.recompute_metrics.run() == 3


def _action(executed: datetime | None, level: str = "L3", **kw: Any) -> AIAction:
    return AIAction(
        action_name="ACT-create_task", agent_profile_code="default", autonomy_level=level,
        status="executed", on_behalf_of=uuid.uuid4(), input={}, source="AI",
        idempotency_key=str(uuid.uuid4()), executed_at=executed, **kw,
    )  # fmt: skip


async def test_verify_action_outcome_checkpoints(db_session: AsyncSession) -> None:
    now = datetime(2037, 6, 10, 12, tzinfo=UTC)
    a24 = _action(now - timedelta(hours=30), verification={"expected_outcome": {"task": "x"}})
    a7d = _action(now - timedelta(days=8))
    low = _action(now - timedelta(days=8), level="L1")
    fresh = _action(now - timedelta(hours=1))
    db_session.add_all([a24, a7d, low, fresh])
    await db_session.flush()
    assert await verify_action_outcomes(db_session, now) >= 3  # a24: 24h · a7d: 24h + 7d
    assert [c["at"] for c in a24.verification["checks"]] == ["24h"]
    assert [c["at"] for c in a7d.verification["checks"]] == ["24h", "7d"]
    assert a24.verification["checks"][0]["result"] == "not_measurable"
    assert low.verification is None and fresh.verification is None
    assert due_checkpoints(a7d, now) == [] and due_checkpoints(_action(None), now) == []
    before = len(a7d.verification["checks"])
    await verify_action_outcomes(db_session, now)  # idempotent per (action, checkpoint)
    assert len(a7d.verification["checks"]) == before

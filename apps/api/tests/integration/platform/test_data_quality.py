"""TC-DQ-001 (T-220, DEC-209): METRIC-DQ-01 — completeness / accuracy / freshness per domain."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today
from app.core.data_quality import DQ_SOURCES, DomainDq, DqSource, domain_stats, dq_score
from app.modules.execution.models import Task
from app.modules.platform.services import metrics as dq
from tests.conftest import ApiClient
from tests.integration.execution.helpers import make_task


def test_dq_score_weights() -> None:
    d = DomainDq("x", 10, completeness=80.0, accuracy=90.0, freshness=50.0)
    assert dq_score(d, 0.3, 0.4, 0.3) == 75.0  # 24 + 36 + 15


async def test_domain_stats_and_provider(
    api: ApiClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    dept, today = uuid.uuid4(), business_today()
    full = {"department_id": str(dept), "assignee_id": str(uuid.uuid4()), "due_date": "2040-01-01"}
    ids = [uuid.UUID((await make_task(api, **full))["id"]) for _ in range(3)]
    ids.append(uuid.UUID((await make_task(api, department_id=str(dept)))["id"]))  # incomplete
    await db_session.execute(update(Task).where(Task.id == ids[0])
                             .values(status="done", done_at=None))  # fmt: skip  # invalid
    mine = DqSource(Task, ("assignee_id", "due_date"),
                    (lambda m: (m.status == "done") & m.done_at.is_(None),),
                    where=(lambda m: m.department_id == dept,))  # fmt: skip
    stats = await domain_stats(db_session, "execution", [mine], today, 24)
    assert stats == DomainDq("execution", 4, completeness=75.0, accuracy=75.0, freshness=100.0)

    stale = datetime.combine(today, datetime.min.time(), tzinfo=UTC) - timedelta(hours=30)
    await db_session.execute(update(Task).where(Task.id.in_(ids)).values(updated_at=stale))
    old = await domain_stats(db_session, "execution", [mine], today, 24)
    assert old is not None and old.freshness == 0.0  # outside SLA_FRESHNESS_EXECUTION 24 h
    assert (
        await domain_stats(
            db_session,
            "execution",
            [DqSource(Task, where=(lambda m: m.department_id == uuid.uuid4(),))],
            today,
            24,
        )
        is None
    )

    monkeypatch.setattr(
        DQ_SOURCES,
        "sources",
        {
            "execution": [mine],
            "risk": [DqSource(Task, where=(lambda m: m.department_id == uuid.uuid4(),))],
        },
    )  # empty → excluded
    [r] = await dq.compute(db_session, today)
    # 75×0.3 + 75×0.4 + 0×0.3 = 52.5 → critical (< 60)
    assert r.code == "METRIC-DQ-01" and r.value == 52.5 and r.data_quality_pct == 75.0
    monkeypatch.setattr(DQ_SOURCES, "sources", {})
    [none] = await dq.compute(db_session, date(2040, 1, 1))
    assert none.value is None and none.status_reason == "no source records"


def test_every_domain_registers_sources() -> None:
    from app.workers.consumers import load_metric_providers

    load_metric_providers()
    assert set(DQ_SOURCES.sources) == set(dq.DOMAINS)

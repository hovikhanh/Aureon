"""TC-DASH-006 (S2 exit): expense over budget → `finance.budget_exceeded` → outbox → relay →
`platform.on_finance_event` → METRIC-FIN-06 recomputed → ALERT-FIN-06 open, all within 60 s.

Committed path (real outbox + relay + consumer transactions) on far-future data (2041-Q3);
everything created is removed in `finally`.
"""

import time
import uuid
from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.events.consumer import consume
from app.core.events.envelope import OUTBOX, PROCESSED
from app.core.events.relay import relay_once
from app.modules.finance.models import Budget, Expense
from app.modules.finance.services.budget_service import BudgetService
from app.modules.platform.events import consumers as platform_consumers
from app.modules.platform.models import Alert, DataLineage, Metric, MetricValue
from app.workers.consumers import load_consumers, load_metric_providers

pytestmark = pytest.mark.integration
AS_OF = date(2041, 10, 5)
SLA_SECONDS = 60


class Collect:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, Any]]] = []

    def send(self, name: str, message: dict[str, Any], countdown: int = 0) -> None:
        self.sent.append((name, message))


async def test_budget_exceeded_alert_within_60s(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    load_consumers()
    load_metric_providers()
    monkeypatch.setattr(platform_consumers, "business_today", lambda: AS_OF)
    dept = uuid.uuid4()
    started = time.monotonic()
    budget_id: uuid.UUID | None = None
    try:
        async with factory() as s:  # 1. business write (API-equivalent service path)
            b = Budget(department_id=dept, fiscal_year=2041, quarter="Q3", source="MANUAL",
                       allocated_amount=1_000_000_000, currency="VND", categories={})  # fmt: skip
            s.add(b)
            s.add(Expense(title="SLA test", category="marketing", amount=1_200_000_000,
                          currency="VND", expense_date=date(2041, 8, 15), period_key="2041-08",
                          origin="manual", department_id=dept, is_recurring=False,
                          source="MANUAL"))  # fmt: skip
            await s.flush()
            budget_id = b.id
            assert await BudgetService(s).check_exceeded(b)
            await s.commit()
        transport = Collect()
        async with factory() as s:  # 2. relay (beat, every 2 s)
            await relay_once(s, transport, honor_pause=False)  # type: ignore[arg-type]
            await s.commit()
        msgs = [(n, m) for n, m in transport.sent if n == "platform.on_finance_event"
                and m["event_type"] == "finance.budget_exceeded"
                and m["payload"].get("budget_id") == str(budget_id)]  # fmt: skip
        assert len(msgs) == 1
        for name, msg in msgs:  # 3. consumer
            assert (await consume(factory, name, msg)).outcome.value == "DONE"
        async with factory() as s:
            alert = (await s.execute(
                select(Alert).join(Metric).where(
                    Metric.code == "METRIC-FIN-06", Alert.period_key == "2041-Q3",
                    Alert.status == "OPEN")
            )).scalar_one()  # fmt: skip
            assert alert.severity in ("WARNING", "CRITICAL")
        elapsed = time.monotonic() - started
        assert elapsed < SLA_SECONDS, f"pipeline took {elapsed:.1f}s"
    finally:
        await _cleanup(factory, dept, budget_id)


async def _cleanup(
    factory: async_sessionmaker[AsyncSession], dept: uuid.UUID, budget_id: uuid.UUID | None
) -> None:
    async with factory() as s:
        mids = select(Metric.id).where(Metric.code.like("METRIC-%"))
        future = MetricValue.period_key.like("2041%")
        await s.execute(
            delete(Alert).where(Alert.period_key.like("2041%"), Alert.metric_id.in_(mids))
        )
        vals = select(MetricValue.id).where(future)
        await s.execute(delete(DataLineage).where(DataLineage.metric_value_id.in_(vals)))
        await s.execute(delete(MetricValue).where(future))
        await s.execute(delete(Expense).where(Expense.department_id == dept))
        await s.execute(delete(Budget).where(Budget.department_id == dept))
        if budget_id is not None:
            ids = select(OUTBOX.c.id).where(OUTBOX.c.aggregate_id == budget_id)
            await s.execute(delete(PROCESSED).where(PROCESSED.c.event_id.in_(ids)))
            await s.execute(delete(OUTBOX).where(OUTBOX.c.aggregate_id == budget_id))
        await s.commit()


def test_sla_constant() -> None:
    assert SLA_SECONDS == 60 and datetime.now(UTC).year >= 2026

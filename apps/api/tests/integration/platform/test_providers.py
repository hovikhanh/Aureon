"""TC-PLT-027..029 (T-220/T-221): domain metric providers + event → alert consumer.

Runs on far-future data created in the rolled-back transaction (2037), independent of seed.
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.envelope import EventEnvelope
from app.core.metrics import METRIC_PROVIDERS
from app.modules.finance.models import Budget, CashPosition, Expense, Revenue
from app.modules.finance.services.metrics import compute as finance_compute
from app.modules.hr.services.metric_provider import compute_hr
from app.modules.platform.events import consumers as platform_consumers
from app.modules.platform.events.consumers import AFFECTS
from app.modules.platform.models import Alert, Metric
from app.modules.sales.services.metric_provider import calc_pct, compute_sales
from app.workers.consumers import load_metric_providers

AS_OF = date(2037, 5, 20)
DEPT = uuid.UUID("00000000-0000-0000-0000-00000000fe01")
CLIENT = uuid.UUID("00000000-0000-0000-0000-00000000c001")


def _rev(period: str, amount: int, client: uuid.UUID | None = None) -> Revenue:
    y, m = int(period[:4]), int(period[5:7])
    return Revenue(
        source_note="t", category="product_sales", amount=amount, currency="VND",
        revenue_date=date(y, m, 5), period_key=period, client_id=client, origin="manual",
        source="MANUAL",
    )  # fmt: skip


def _exp(period: str, amount: int, category: str = "office") -> Expense:
    y, m = int(period[:4]), int(period[5:7])
    return Expense(
        category=category, amount=amount, currency="VND", expense_date=date(y, m, 6),
        period_key=period, department_id=DEPT, origin="manual", source="MANUAL",
        title="t", is_recurring=False,
    )  # fmt: skip


@pytest.fixture
async def fin_data(db_session: AsyncSession) -> None:
    for p in ("2037-01", "2037-02", "2037-03", "2037-04"):
        db_session.add_all([_rev(p, 1_000, CLIENT), _exp(p, 1_500), _exp(p, 400, "cogs")])
    db_session.add_all([
        CashPosition(period_key="2037-03", closing_balance=5_000, currency="VND",
                     cash_source="bank_statement", source="MANUAL", recorded_by=DEPT),
        CashPosition(period_key="2037-04", closing_balance=4_500, currency="VND",
                     cash_source="bank_statement", source="MANUAL", recorded_by=DEPT),
        Budget(department_id=DEPT, fiscal_year=2037, quarter="Q2", allocated_amount=1_000,
               currency="VND", categories={}, source="MANUAL"),
    ])  # fmt: skip
    await db_session.flush()


def test_registry_and_affects() -> None:
    load_metric_providers()
    assert {"finance", "sales", "hr"} <= set(METRIC_PROVIDERS.providers)
    assert AFFECTS["finance.invoice_paid"] == {"finance", "sales"}
    assert calc_pct(1, 0) is None and calc_pct(1, 4) == 25.0


async def test_finance_provider(db_session: AsyncSession, fin_data: None) -> None:
    by = {(r.code, r.scope_type): r for r in await finance_compute(db_session, AS_OF)}
    assert by[("METRIC-FIN-02", "company")].period_key == "2037-Q2"
    # BR-FIN-01 3-month avg burn: (900 + 900 + 500 cash delta) / 3 → 4 500 / 766.7
    assert by[("METRIC-FIN-03", "company")].value == 5.9
    fin6 = by[("METRIC-FIN-06", "company")]
    assert fin6.value == 90.0 and fin6.records  # (1 500 + 400 cogs) / 1 000 → +90 %
    assert by[("METRIC-FIN-06", "department")].scope_id == str(DEPT)
    assert ("METRIC-FIN-01", "company") not in by  # owned by the sales provider


async def test_sales_and_hr_providers(db_session: AsyncSession, fin_data: None) -> None:
    by = {r.code: r for r in await compute_sales(db_session, AS_OF)}
    assert by["METRIC-FIN-01"].value is None and by["METRIC-FIN-01"].status_reason == "NO_TARGET"
    assert by["METRIC-CUS-03"].value == 100.0  # same client kept its revenue
    assert by["METRIC-CUS-04"].value == 100.0  # one client = 100 % concentration
    assert {"METRIC-CUS-01", "METRIC-CUS-02", "METRIC-CUS-06"} <= set(by)
    hr = {r.code: r for r in await compute_hr(db_session, AS_OF)}
    assert set(hr) == {"METRIC-HR-01", "METRIC-HR-02", "METRIC-HR-04"}
    assert hr["METRIC-HR-04"].status in ("ok", "warning", "critical")


async def test_event_consumer_raises_alert(db_session: AsyncSession, fin_data: None,
                                           monkeypatch: pytest.MonkeyPatch) -> None:  # fmt: skip
    """revenue → finance.budget_exceeded → platform consumer → ALERT-FIN-06 (S2 exit)."""
    load_metric_providers()
    monkeypatch.setattr(platform_consumers, "business_today", lambda: AS_OF)
    env = EventEnvelope(
        event_id=uuid.uuid4(), event_type="finance.budget_exceeded",
        occurred_at=datetime.now(UTC), version=1, producer="finance",
        payload={"budget_id": str(uuid.uuid4())},
    )  # fmt: skip
    await platform_consumers.recompute_for(db_session, env)
    stmt = (
        select(func.count(Alert.id))
        .join(Metric)
        .where(
            Metric.code == "METRIC-FIN-06", Alert.period_key == "2037-Q2", Alert.status == "OPEN"
        )
    )
    assert int((await db_session.execute(stmt)).scalar_one()) == 1

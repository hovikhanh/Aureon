"""S1a seed (08 §3, §6, §10.4) — runs inside the rolled-back test transaction."""

import uuid
from datetime import date
from typing import Any

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.core.events.envelope import OUTBOX
from app.modules.finance.models import (
    Budget,
    CashFlowForecast,
    CashPosition,
    Expense,
    Forecast,
    Invoice,
    Revenue,
)
from app.modules.finance.services.analytics_service import FinanceAnalyticsService
from app.seed import finance_data as D
from app.seed.finance_seed import seed_finance

pytestmark = pytest.mark.integration

TY = 1_000_000_000


@pytest.fixture
async def seeded(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> AsyncSession:
    cfg = get_config()
    monkeypatch.setattr(cfg, "demo_mode", True)
    monkeypatch.setattr(cfg, "demo_reference_date", "2026-10-20")
    # isolate from rows other tests / a previous real seed may have left
    for model in (Revenue, Expense, CashPosition, Budget, Invoice, Forecast, CashFlowForecast):
        await db_session.execute(
            update(model).where(model.deleted_at.is_(None)).values(deleted_at=func.now(),
                                                                     source="MANUAL")
        )  # fmt: skip
    await db_session.execute(delete(OUTBOX).where(OUTBOX.c.event_type.like("finance.%")))
    await db_session.execute(update(Forecast).values(is_current=False))
    await db_session.execute(update(CashFlowForecast).values(is_current=False))
    report = await seed_finance(db_session, uuid.uuid4())
    # T-237: 48 HV/HL + 8 historical open invoices = 56; burn now under forecast → no event.
    assert report["revenues"] == 48 and report["budgets"] == 7 and report["invoices"] == 56
    assert report["forecasts"] == 3 and report["cash_flow_forecasts"] == 3
    assert report["burn_over_forecast"] == 0
    return db_session


async def _count(db: AsyncSession, model: Any, *where: Any) -> int:
    stmt = select(func.count()).select_from(model).where(model.source == "SEED", *where)
    return int((await db.execute(stmt)).scalar_one())


async def test_seed_volumes_and_idempotent(seeded: AsyncSession) -> None:
    assert await _count(seeded, Revenue) >= 5 and await _count(seeded, Expense) >= 8
    assert await _count(seeded, Budget) >= 3 and await _count(seeded, Invoice) >= 5
    assert await _count(seeded, CashFlowForecast) == 3
    again = await seed_finance(seeded, uuid.uuid4())
    assert sum(v for k, v in again.items() if k != "burn_over_forecast") == 0
    assert again["burn_over_forecast"] == 0


async def test_seed_matches_08_figures(seeded: AsyncSession) -> None:
    svc = FinanceAnalyticsService(seeded)
    dash = await svc.dashboard("2026-Q3")
    s = dash.summary
    assert s.total_revenue == 73_500_000_000  # DOC-01
    assert s.gross_margin_pct == 18.4
    # T-237 rebalance → METRIC-FIN-03 green: flatter cash drops → burn 1,5 tỷ, runway 13,6 tháng.
    assert s.runway_months == 13.6 and s.net_burn == 1_500_000_000
    assert s.budget_utilization_pct == pytest.approx(97.29)  # every department within budget
    t9 = await svc.dashboard("2026-09")
    assert t9.summary.total_revenue == 25_500_000_000
    variance = await svc.burn_variance(date(2026, 10, 20))
    assert variance is not None and variance < 10  # METRIC-FIN-07 green (≈ −7 %)
    statuses = {m.metric_code: m.status for m in dash.metrics}
    assert statuses["METRIC-FIN-03"] == "ok" and statuses["METRIC-FIN-07"] == "ok"


async def test_seed_alert_events_and_cash_flow(seeded: AsyncSession) -> None:
    rows = (await seeded.execute(select(OUTBOX.c.event_type, OUTBOX.c.payload))).all()
    types = [t for t, _ in rows]
    # T-237 rebalance: every department within budget and burn under forecast → no FIN-06/07 event.
    assert "finance.budget_exceeded" not in types
    assert "finance.burn_over_forecast" not in types
    cf = [p for t, p in rows if t == "finance.cash_flow_forecast_updated"]
    assert {"min_projected_cash": 3_100_000_000, "min_cash_week": 7}.items() <= cf[-1].items()
    lows = (await seeded.execute(
        select(CashFlowForecast.assumptions, CashFlowForecast.min_projected_cash,
               CashFlowForecast.min_cash_week).where(CashFlowForecast.source == "SEED",
                                                     CashFlowForecast.deleted_at.is_(None))
    )).all()  # fmt: skip
    by = {a["scenario"]: (m, w) for a, m, w in lows}
    assert by == {"optimistic": (6_865_000_000, 7), "base": (3_100_000_000, 7),
                  "pessimistic": (-1_984_000_000, 9)}  # fmt: skip
    overdue = await _count(seeded, Invoice, Invoice.status == "overdue")
    assert overdue == 5  # HV-001/008/030/032 (1–30 ngày) + HL-001 (96 ngày)


def test_seed_data_arithmetic() -> None:
    """08 §9 checks on the static data."""
    hv = [r for r in D.INVOICES if r[0].startswith("HV")]
    assert len(hv) == 47 and sum(r[4] for r in hv) == 25_500_000_000
    assert sum(r[4] * r[5] // 100 for r in hv) == 2_436_000_000
    q3 = sum(D.MONTHLY_REVENUE_MIL[m] for m in ("2026-07", "2026-08", "2026-09"))
    assert q3 == 73_500 and sum(D.COGS_MIL.values()) == 60_000
    last12 = [v for k, v in D.MONTHLY_REVENUE_MIL.items() if "2025-10" <= k <= "2026-09"]
    assert sum(last12) == 294_000

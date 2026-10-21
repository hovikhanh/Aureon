"""T-105 — BR-FIN burn/runway, EP-69 what-if, EP-60 dashboard, FR-FIN-08 (TC-FIN-005/006)."""

from datetime import date
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.core.events.envelope import OUTBOX
from app.modules.finance.services.analytics_service import FinanceAnalyticsService
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration

B = 1_000_000  # 1 triệu


async def _month(api: ApiClient, period: str, revenue: int, expense: int, cogs: int = 0) -> None:
    day = f"{period}-10"
    if revenue:
        body = {"amount": revenue, "category": "service", "recognized_on": day}
        assert (await api.call("POST", "/finance/revenues", json=body)).status_code == 201
    for amount, cat in ((expense - cogs, "office"), (cogs, "cogs")):
        if amount:
            body = {"title": "chi", "amount": amount, "category": cat, "spent_on": day}
            assert (await api.call("POST", "/finance/expenses", json=body)).status_code == 201


async def _cash(api: ApiClient, period: str, balance: int) -> None:
    body = {"period": period, "closing_balance": balance, "cash_source": "bank_statement"}
    assert (await api.call("POST", "/finance/cash-positions", json=body)).status_code == 201


async def _seed_q1(api: ApiClient) -> None:
    # (chi − thu) = 400, 500, 600 triệu → burn 500 triệu (03 BR-FIN-01 example)
    await _month(api, "2035-01", 1000 * B, 1400 * B, cogs=600 * B)
    await _month(api, "2035-02", 1000 * B, 1500 * B, cogs=600 * B)
    await _month(api, "2035-03", 1000 * B, 1600 * B, cogs=700 * B)
    await _cash(api, "2035-03", 3000 * B)


async def test_what_if_runway_br_fin_02_and_06(api: ApiClient) -> None:
    await _seed_q1(api)
    r = await api.call("GET", "/finance/what-if/runway", "CEO",
                       params={"as_of": "2035-04-15", "revenue_change_pct": 0})  # fmt: skip
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["net_burn"] == 500 * B and d["runway_months"] == 6.0
    assert d["avg_expense_3m"] == 1500 * B and d["runway_months_no_new_revenue"] == 2.0
    assert d["sources"][0]["type"] == "record" and len(d["sources"]) == 4

    no_rev = await api.call("GET", "/finance/what-if/runway", params={"as_of": "2035-04-15"})
    assert no_rev.json()["data"]["net_burn"] == 1500 * B
    assert no_rev.json()["data"]["runway_months"] == 2.0

    cut = await api.call(
        "GET", "/finance/what-if/runway",
        params={"as_of": "2035-04-15", "expense_change_pct": -50, "extra_monthly_cost": 0,
                "revenue_change_pct": 0},
    )  # fmt: skip
    # chi giảm 50% → 700/750/800 < thu 1000 → có lãi → runway null (BR-FIN-03)
    assert cut.json()["data"]["net_burn"] == 0 and cut.json()["data"]["runway_months"] is None
    bad = await api.call("GET", "/finance/what-if/runway", params={"revenue_change_pct": 150})
    assert bad.status_code == 422


async def test_what_if_without_cash_position(api: ApiClient) -> None:
    r = await api.call("GET", "/finance/what-if/runway", params={"as_of": "1990-05-01"})
    d = r.json()["data"]
    assert d["status_reason"] == "NO_CASH_POSITION" and d["runway_months_no_new_revenue"] is None


async def test_dashboard_contract(api: ApiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = get_config()
    monkeypatch.setattr(cfg, "demo_mode", True)
    monkeypatch.setattr(cfg, "demo_reference_date", "2035-04-15")
    await _seed_q1(api)
    dept_budget = {"department_id": "00000000-0000-4000-8000-000000000035", "fiscal_year": 2035,
                   "quarter": "Q1", "allocated_amount": 100 * B}  # fmt: skip
    assert (await api.call("POST", "/finance/budgets", json=dept_budget)).status_code == 201
    r = await api.call("GET", "/finance/dashboard", "CEO", params={"period": "2035-Q1"})
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "private, max-age=60"
    assert "Authorization" in r.headers["vary"]
    d = r.json()["data"]
    assert d["pillar"] == "F" and d["period"]["key"] == "2035-Q1"
    s = d["summary"]
    assert s["total_revenue"] == 3000 * B and s["total_expense"] == 4500 * B
    assert s["net_profit"] == -1500 * B and s["gross_burn"] == 4500 * B
    assert s["gross_margin_pct"] == pytest.approx(36.7)
    assert s["net_burn"] == 500 * B and s["runway_months"] == 6.0
    assert s["budget_utilization_pct"] == 0.0 and s["currency"] == "VND"
    assert len(d["revenue_trend"]) == 12 and d["revenue_trend"][-1]["period_key"] == "2035-03"
    assert d["revenue_trend"][-1] == {"period_key": "2035-03", "revenue": 1000 * B,
                                      "expense": 1600 * B}  # fmt: skip
    assert d["runway_trend"][-1]["runway_months"] == 6.0
    codes = [m["metric_code"] for m in d["metrics"]]
    assert codes == [f"METRIC-FIN-0{i}" for i in range(1, 8)]
    runway = d["metrics"][2]
    assert runway["status"] == "warning" and runway["lineage_url"].endswith("METRIC-FIN-03")
    assert d["status"] in {"warning", "critical"}


@pytest.mark.parametrize("period", ["current_month", "current_quarter", "ytd", "2035-02"])
async def test_dashboard_periods(api: ApiClient, period: str) -> None:
    r = await api.call("GET", "/finance/dashboard", "VP_SALES", params={"period": period})
    assert r.status_code == 200
    assert r.json()["data"]["status"] in {"ok", "warning", "critical", "no_data"}


async def test_dashboard_bad_period_and_permission(api: ApiClient) -> None:
    assert (
        await api.call("GET", "/finance/dashboard", params={"period": "2035/1"})
    ).status_code == 400
    assert (await api.call("GET", "/finance/dashboard", "EMPLOYEE")).status_code == 403


async def _burn_events(db: AsyncSession) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(OUTBOX.c.payload).where(OUTBOX.c.event_type == "finance.burn_over_forecast")
    )
    return [r[0] for r in rows if r[0]["period_key"] == "2035-06"]


async def test_burn_over_forecast_daily_job(api: ApiClient, db_session: AsyncSession) -> None:
    line = {"period_key": "2035-06", "revenue": 1000 * B, "expense": 1300 * B}
    fc = {"scenario": "base", "horizon": "3m", "confidence_pct": 80, "lines": [line]}
    assert (await api.call("POST", "/finance/forecasts", json=fc)).status_code == 201
    svc = FinanceAnalyticsService(db_session)
    day = date(2035, 6, 15)  # 15/30 ngày
    await _month(api, "2035-06", 400 * B, 550 * B)  # MTD burn 150 → dự kiến 300 = dự báo
    assert await svc.burn_variance(day) == 0.0
    assert await svc.check_burn_over_forecast(day) is False

    body = {"title": "đột biến", "amount": 50 * B, "category": "other", "spent_on": "2035-06-12"}
    await api.call("POST", "/finance/expenses", json=body)  # MTD burn 200 → dự kiến 400 (+33%)
    assert await svc.burn_variance(day) == pytest.approx(33.3)
    assert await svc.check_burn_over_forecast(day) is True
    assert await svc.check_burn_over_forecast(day) is False  # tối đa 1 lần/ngày
    ev = await _burn_events(db_session)
    assert len(ev) == 1
    assert ev[0]["actual_burn"] == 400 * B and ev[0]["forecast_burn"] == 300 * B
    assert ev[0]["severity"] == "critical"
    assert await svc.check_burn_over_forecast(date(2035, 7, 1)) is False  # no forecast line


async def test_burn_uses_cash_deltas_when_available(
    api: ApiClient, db_session: AsyncSession
) -> None:
    """DEC-202 / 08 DOC-01: cash 28,05 → 25,95 → 23,4 → 20,4 tỷ → burn 2,55 tỷ → 8,0 tháng."""
    for period, bal in (("2034-06", 28_050), ("2034-07", 25_950), ("2034-08", 23_400),
                        ("2034-09", 20_400)):  # fmt: skip
        await _cash(api, period, bal * B)
    await _month(api, "2034-09", 25_500 * B, 23_000 * B)  # P&L profitable, cash still burns
    svc = FinanceAnalyticsService(db_session)
    burn, balance, runway = await svc.burn_and_runway("2034-10")
    assert burn == 2_550 * B and balance == 20_400 * B and runway == 8.0

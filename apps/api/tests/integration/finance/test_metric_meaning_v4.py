"""K1, K3, K7, K8 — a METRIC-FIN code reads the same on `/finance/dashboard` and in the store.

FIN-01 = revenue vs target (D-09), FIN-06 = worst department overrun, thresholds from the store's
config (NFR-19); the what-if starts from the store's burn (cash delta, DEC-202).
"""

import uuid
from datetime import date
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.modules.platform.models import SystemSetting
from app.modules.platform.services.metric_store import MetricStore
from app.modules.sales.services.metric_provider import compute_sales
from tests.conftest import ApiClient
from tests.integration.finance.test_analytics import B, _cash, _month

pytestmark = pytest.mark.integration

TODAY = date(2041, 5, 20)
CLOSED = "2041-04"
Metrics = dict[str, dict[str, Any]]


@pytest.fixture(autouse=True)
def _business_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_config(), "business_date_override", TODAY)


async def _target(api: ApiClient, amount: int, period: str = CLOSED) -> None:
    body = {"period_type": "month", "period_key": period, "scope": "team", "target_amount": amount}
    assert (await api.call("POST", "/sales/targets", "CEO", json=body)).status_code == 201


async def _dashboard(api: ApiClient, **params: Any) -> tuple[Metrics, dict[str, Any]]:
    r = await api.call("GET", "/finance/dashboard", "CEO", params=params or None)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    return {m["metric_code"]: m for m in d["metrics"]}, d["summary"]


async def test_fin01_is_revenue_vs_target_with_the_store_status(
    api: ApiClient, db_session: AsyncSession
) -> None:
    await _month(api, "2040-04", 1000 * B, 100 * B)  # YoY +70 % must not leak into FIN-01
    await _month(api, CLOSED, 1700 * B, 100 * B)
    await _target(api, 2000 * B)
    metrics, summary = await _dashboard(api)
    fin01 = metrics["METRIC-FIN-01"]
    assert (fin01["value"], fin01["status"], fin01["period_key"]) == (85.0, "warning", CLOSED)
    assert fin01["unit"] == "PCT" and fin01["lineage_url"].endswith("METRIC-FIN-01")

    store = [r for r in await compute_sales(db_session, TODAY) if r.code == "METRIC-FIN-01"]
    assert [(r.value, r.period_key) for r in store] == [(85.0, CLOSED)]

    _, q2 = await _dashboard(api, period=CLOSED)
    assert q2["revenue_growth_pct"] == 70.0  # YoY keeps its own non-METRIC name
    assert summary["revenue_growth_pct"] is None  # running month has no revenue a year ago


async def test_fin01_without_target_has_no_data(api: ApiClient) -> None:
    await _month(api, CLOSED, 1700 * B, 100 * B)
    fin01 = (await _dashboard(api))[0]["METRIC-FIN-01"]
    assert fin01["value"] is None and fin01["status"] == "no_data"


async def test_fin01_of_a_past_period_reads_that_month(api: ApiClient) -> None:
    await _month(api, "2041-02", 950 * B, 100 * B)
    await _target(api, 1000 * B, "2041-02")
    fin01 = (await _dashboard(api, period="2041-02"))[0]["METRIC-FIN-01"]
    assert (fin01["value"], fin01["status"], fin01["period_key"]) == (95.0, "ok", "2041-02")


async def test_thresholds_come_from_the_store_config(
    api: ApiClient, db_session: AsyncSession
) -> None:
    await _month(api, CLOSED, 1700 * B, 100 * B)
    await _target(api, 2000 * B)
    db_session.add_all([SystemSetting(key="THR_FIN_01_WARN", value=80),
                        SystemSetting(key="THR_FIN_01_CRIT", value=70)])  # fmt: skip
    await db_session.flush()
    assert (await _dashboard(api))[0]["METRIC-FIN-01"]["status"] == "ok"


async def test_runway_status_follows_a_threshold_override(
    api: ApiClient, db_session: AsyncSession
) -> None:
    for m, cash in (("2041-01", 1600), ("2041-02", 1400), ("2041-03", 1200), (CLOSED, 1000)):
        await _cash(api, m, cash * B)
    assert (await _dashboard(api))[0]["METRIC-FIN-03"]["status"] == "critical"  # 5 < 6
    db_session.add(SystemSetting(key="THR_FIN_03_CRIT", value=2))
    await db_session.flush()
    assert (await _dashboard(api))[0]["METRIC-FIN-03"]["status"] == "warning"


async def test_fin06_is_the_worst_department_overrun(api: ApiClient) -> None:
    over, under = uuid.uuid4(), uuid.uuid4()
    for dept, spent in ((over, 130), (under, 50)):
        budget = {"department_id": str(dept), "fiscal_year": 2041, "quarter": "Q2",
                  "allocated_amount": 100 * B}  # fmt: skip
        assert (await api.call("POST", "/finance/budgets", json=budget)).status_code == 201
        expense = {"title": "chi", "amount": spent * B, "category": "office",
                   "spent_on": "2041-04-10", "department_id": str(dept)}  # fmt: skip
        assert (await api.call("POST", "/finance/expenses", json=expense)).status_code == 201
    metrics, summary = await _dashboard(api)
    fin06 = metrics["METRIC-FIN-06"]
    assert (fin06["value"], fin06["status"]) == (30.0, "critical")
    assert summary["budget_utilization_pct"] == 90.0  # the company total stays its own field


async def test_store_and_dashboard_agree_on_every_shared_code(
    api: ApiClient, db_session: AsyncSession
) -> None:
    await _month(api, "2041-02", 1000 * B, 800 * B, cogs=500 * B)
    await _month(api, "2041-03", 1000 * B, 800 * B, cogs=500 * B)
    await _month(api, CLOSED, 1000 * B, 800 * B, cogs=500 * B)
    await _target(api, 1000 * B)
    for m, cash in (("2041-01", 900), ("2041-02", 800), ("2041-03", 700), (CLOSED, 600)):
        await _cash(api, m, cash * B)
    await MetricStore(db_session).recompute(TODAY, {"finance", "sales"})
    await db_session.flush()
    live, _ = await _dashboard(api)
    stored = (await api.call("GET", "/dashboard/metrics", "CEO")).json()["data"]
    by_code = {m["metric_code"]: m for m in stored if m["metric_code"].startswith("METRIC-FIN")}
    for code in ("METRIC-FIN-01", "METRIC-FIN-02", "METRIC-FIN-03", "METRIC-FIN-05"):
        assert live[code]["value"] == by_code[code]["value"], code
        assert live[code]["status"] == by_code[code]["status"], code


# ---------- K3 ----------
async def test_what_if_baseline_is_the_store_burn(api: ApiClient) -> None:
    """Profitable P&L, falling cash: store burn 300 → the what-if may not read burn 0 / null."""
    for m in ("2041-02", "2041-03", CLOSED):
        await _month(api, m, 1000 * B, 800 * B)
    for m, cash in (("2041-01", 2100), ("2041-02", 1800), ("2041-03", 1500), (CLOSED, 1200)):
        await _cash(api, m, cash * B)
    _, summary = await _dashboard(api)
    assert summary["net_burn"] == 300 * B and summary["runway_months"] == 4.0
    params = {"revenue_change_pct": 0, "expense_change_pct": 0}
    base = (await api.call("GET", "/finance/what-if/runway", "CEO", params=params)).json()["data"]
    assert base["net_burn"] == summary["net_burn"]
    assert base["runway_months"] == summary["runway_months"]
    assert base["avg_expense_3m"] == 800 * B and base["avg_revenue_3m"] == 1000 * B

    params = {"revenue_change_pct": 0, "expense_change_pct": 50}
    more = (await api.call("GET", "/finance/what-if/runway", "CEO", params=params)).json()["data"]
    assert more["net_burn"] == 700 * B and more["runway_months"] == 1.7

    params = {"revenue_change_pct": 50, "expense_change_pct": 0}
    gain = (await api.call("GET", "/finance/what-if/runway", "CEO", params=params)).json()["data"]
    assert gain["net_burn"] == 0 and gain["runway_months"] is None  # +500 covers the 300 burn

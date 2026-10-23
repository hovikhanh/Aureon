"""TC-RSK-005 — EP-105 what-if via public services, 5 s per domain → unavailable (T-214)."""

import asyncio
import uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance.services.analytics_service import FinanceAnalyticsService
from app.modules.risk.models import Scenario
from app.modules.risk.schemas import ScenarioAssumptions
from app.modules.risk.services import scenario_service
from app.modules.risk.services.scenario_service import build_shock
from app.modules.sales.services.analytics import SalesAnalytics
from tests.conftest import ApiClient
from tests.integration.risk.helpers import audit_actions, make_risk


async def _run(api: ApiClient, ids: list[str], role: str = "CEO", **kw: Any) -> Any:
    body = {"risk_ids": ids, "horizon_months": 6, **kw}
    return await api.call("POST", "/risk/scenarios", role, json=body)


async def test_scenario_all_domains(api: ApiClient, db_session: AsyncSession) -> None:
    a = await make_risk(api, category="customer", likelihood=5, impact=5)
    b = await make_risk(api, category="people", likelihood=4, impact=3)
    res = await _run(api, [a["id"], b["id"], a["id"]])
    assert res.status_code == 201, res.text
    d = res.json()["data"]
    imp = d["impacts"]
    assert imp["product"] == {"status": "unavailable", "roadmap_items_at_risk": None}
    assert imp["finance"]["status"] == "ok" and imp["finance"]["revenue_delta"] < 0
    assert imp["finance"]["expense_delta"] > 0
    runway = imp["finance"]["runway_delta_months"]
    assert runway is None or runway <= 0  # base without burn = unbounded runway → null
    assert imp["sales"]["status"] == "ok" and imp["sales"]["pipeline_delta"] <= 0
    assert imp["hr"]["status"] == "ok" and imp["hr"]["headcount_delta"] <= 0
    assert d["sources"] and d["sources"][0]["type"] == "record"
    row = await db_session.get(Scenario, uuid.UUID(d["scenario_id"]))
    assert row is not None and row.horizon_months == 6 and len(row.risk_ids) == 2
    assert row.results["impacts"]["product"]["status"] == "unavailable"
    assert await audit_actions(db_session, d["scenario_id"]) == ["risk.scenario_run"]


async def test_domain_timeout_and_error_degrade(
    api: ApiClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = await make_risk(api, category="financial")

    async def slow(*_a: Any, **_k: Any) -> None:
        await asyncio.sleep(1)

    async def boom(*_a: Any, **_k: Any) -> None:
        raise RuntimeError("down")

    monkeypatch.setattr(scenario_service, "DOMAIN_TIMEOUT_S", 0.05)
    monkeypatch.setattr(FinanceAnalyticsService, "what_if_runway", slow)
    monkeypatch.setattr(SalesAnalytics, "pipeline", boom)
    res = await _run(api, [r["id"]], assumptions={"name": "Stress", "extra_monthly_cost": 10})
    assert res.status_code == 201, res.text
    imp = res.json()["data"]["impacts"]
    assert imp["finance"]["status"] == "unavailable" and imp["sales"]["status"] == "unavailable"
    assert imp["hr"]["status"] == "ok"
    stmt = select(Scenario.name).where(Scenario.id == uuid.UUID(res.json()["data"]["scenario_id"]))
    assert (await db_session.execute(stmt)).scalar_one() == "Stress"


async def test_scenario_validation_and_scope(api: ApiClient) -> None:
    r = await make_risk(api, category="product")
    assert (await _run(api, [])).status_code == 422
    assert (await _run(api, [str(uuid.uuid4()) for _ in range(11)])).status_code == 422
    assert (await _run(api, [r["id"]], horizon_months=25)).status_code == 422
    assert (await _run(api, [str(uuid.uuid4())])).status_code == 404
    assert (await _run(api, [r["id"]], role="RISK_MANAGER")).status_code == 201
    # Sales-DIR (khối C) có risk:query nhưng không thấy risk category=product (linked reader
    # chỉ thấy risk khối mình) → risk nằm ngoài scope → 404 (R-DEC-12a; không lộ tồn tại).
    assert (await _run(api, [r["id"]], role="VP_SALES")).status_code == 404
    bad = await _run(api, [r["id"]], assumptions={"foo": 1})
    assert bad.status_code == 422


def test_build_shock_weights_and_overrides() -> None:
    s = build_shock([("customer", 5, 5)], None)
    assert (s.revenue_pct, s.pipeline_pct, s.extra_cost) == (-15.0, -20.0, 0)
    half = build_shock([("people", 5, 1)], None)
    assert half.headcount_pct == -2.0
    o = build_shock(
        [("customer", 5, 5)] * 9, ScenarioAssumptions(revenue_change_pct=-5, extra_monthly_cost=7)
    )
    assert o.revenue_pct == -5 and o.pipeline_pct == -100 and o.extra_cost == 7


async def test_finance_runway_delta_and_no_cash(
    api: ApiClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = await make_risk(api, category="financial", likelihood=5, impact=5)
    original = FinanceAnalyticsService.what_if_runway

    async def fake(self: FinanceAnalyticsService, **kw: Any) -> Any:
        out = await original(self, **kw)
        months = 12.0 if kw["revenue_change_pct"] == 0 else 9.5
        return out.model_copy(update={"runway_months": months})

    monkeypatch.setattr(FinanceAnalyticsService, "what_if_runway", fake)
    imp = (await _run(api, [r["id"]])).json()["data"]["impacts"]
    assert imp["finance"]["runway_delta_months"] == -2.5

    async def no_cash(self: FinanceAnalyticsService, **kw: Any) -> Any:
        out = await original(self, **kw)
        return out.model_copy(update={"avg_revenue_3m": None})

    monkeypatch.setattr(FinanceAnalyticsService, "what_if_runway", no_cash)
    imp = (await _run(api, [r["id"]])).json()["data"]["impacts"]
    assert imp["finance"] == {
        "status": "unavailable",
        "revenue_delta": None,
        "expense_delta": None,
        "runway_delta_months": None,
    }

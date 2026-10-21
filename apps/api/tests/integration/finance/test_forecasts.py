"""T-103 — EP-66 forecasts 3 scenarios + lines → `EVT-finance.forecast_updated` (TC-FIN-003)."""

import uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.envelope import OUTBOX
from app.modules.finance.services.forecast_service import confidence_band
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration

LINES = [
    {"period_key": "2031-02", "revenue": 900, "expense": 1000},
    {"period_key": "2031-01", "revenue": 1000, "expense": 800},
    {"period_key": "2031-03", "revenue": 1000, "expense": 1000},
]


def _body(**kw: Any) -> dict[str, Any]:
    return {"scenario": "base", "horizon": "3m", "lines": LINES, "confidence_pct": 75, **kw}


async def _events(db: AsyncSession, fid: str) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(OUTBOX.c.payload).where(
            OUTBOX.c.event_type == "finance.forecast_updated",
            OUTBOX.c.aggregate_id == uuid.UUID(fid),
        )
    )
    return [r[0] for r in rows]


async def test_create_forecast_lines_and_event(api: ApiClient, db_session: AsyncSession) -> None:
    r = await api.call("POST", "/finance/forecasts", json=_body())
    assert r.status_code == 201, r.text
    f = r.json()["data"]
    assert f["is_current"] and f["horizon_months"] == 3 and f["confidence_pct"] == 75
    assert [ln["period_key"] for ln in f["lines"]] == ["2031-01", "2031-02", "2031-03"]
    nets = [ln["net_profit"] for ln in f["lines"]]
    assert nets == [200, -100, 0]
    cash = [ln["closing_cash"] for ln in f["lines"]]
    assert cash[1] - cash[0] == -100 and cash[2] == cash[1]
    assert {ln["confidence_level"] for ln in f["lines"]} == {"MEDIUM"}
    ev = await _events(db_session, f["id"])
    assert (
        len(ev) == 1 and ev[0]["scenario"] == "base" and ev[0]["projected_net_profit_total"] == 100
    )


async def test_new_forecast_retires_previous_current(api: ApiClient) -> None:
    first = (await api.call("POST", "/finance/forecasts", json=_body())).json()["data"]
    second = (await api.call("POST", "/finance/forecasts", json=_body(horizon="6m"))).json()["data"]
    assert second["is_current"]
    old = (await api.call("GET", f"/finance/forecasts/{first['id']}")).json()["data"]
    assert old["is_current"] is False
    cur = await api.call(
        "GET", "/finance/forecasts", params={"scenario": "base", "is_current": True}
    )
    assert [x["id"] for x in cur.json()["data"]] == [second["id"]]
    six = await api.call("GET", "/finance/forecasts", params={"horizon": "6m", "scenario": "base"})
    assert second["id"] in [x["id"] for x in six.json()["data"]]


async def test_three_scenarios_coexist(api: ApiClient) -> None:
    for sc in ("optimistic", "base", "pessimistic"):
        assert (
            await api.call("POST", "/finance/forecasts", json=_body(scenario=sc))
        ).status_code == 201
    cur = await api.call("GET", "/finance/forecasts", params={"is_current": True, "limit": 10})
    assert {x["scenario"] for x in cur.json()["data"]} >= {"optimistic", "base", "pessimistic"}


async def test_update_lines_and_confidence(api: ApiClient, db_session: AsyncSession) -> None:
    f = (await api.call("POST", "/finance/forecasts", json=_body())).json()["data"]
    p = await api.call(
        "PATCH", f"/finance/forecasts/{f['id']}",
        json={"lines": [{"period_key": "2031-01", "revenue": 5, "expense": 1}], "version": 1,
              "assumptions": {"growth_pct": 5}},
    )  # fmt: skip
    assert p.status_code == 200, p.text
    d = p.json()["data"]
    assert len(d["lines"]) == 1 and d["lines"][0]["net_profit"] == 4
    assert d["assumptions"]["growth_pct"] == 5 and d["confidence_pct"] == 75
    c = await api.call(
        "PATCH", f"/finance/forecasts/{f['id']}", json={"confidence_pct": 95},
        headers={"If-Match": "2"},
    )  # fmt: skip
    assert c.json()["data"]["lines"][0]["confidence_level"] == "HIGH"
    assert len(await _events(db_session, f["id"])) == 3
    stale = await api.call("PATCH", f"/finance/forecasts/{f['id']}", json={"version": 1})
    assert stale.status_code == 409


@pytest.mark.parametrize(
    ("patch", "code"),
    [
        ({"horizon": "1m"}, "BUSINESS_RULE_VIOLATION"),
        ({"lines": [*LINES, {"period_key": "2031-04", "revenue": 1, "expense": 1}]},
         "BUSINESS_RULE_VIOLATION"),
        ({"lines": [LINES[0], LINES[0]]}, "BUSINESS_RULE_VIOLATION"),
        ({"lines": []}, "VALIDATION_ERROR"),
        ({"scenario": "worst"}, "VALIDATION_ERROR"),
    ],
)  # fmt: skip
async def test_forecast_validation(api: ApiClient, patch: dict[str, Any], code: str) -> None:
    r = await api.call("POST", "/finance/forecasts", json=_body(**patch))
    assert r.status_code == 422 and r.json()["error"]["code"] == code


async def test_forecast_not_found_and_permissions(api: ApiClient) -> None:
    assert (await api.call("GET", f"/finance/forecasts/{uuid.uuid4()}")).status_code == 404
    assert (await api.call("POST", "/finance/forecasts", "CEO", json=_body())).status_code == 403
    bad = await api.call("GET", "/finance/forecasts", params={"horizon": "1m"})
    assert bad.status_code == 422


def test_confidence_band() -> None:
    assert [confidence_band(x) for x in (None, 59.9, 60, 89.9, 90)] == [
        "LOW", "LOW", "MEDIUM", "MEDIUM", "HIGH",
    ]  # fmt: skip

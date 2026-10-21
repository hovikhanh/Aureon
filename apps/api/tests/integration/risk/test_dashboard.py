"""TC-RSK-007 — EP-100 `/risk/dashboard`: summary, heatmap 5×5, trend, cache headers (T-216)."""

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.risk.models import Risk
from app.modules.risk.services.dashboard_service import RiskDashboardService
from tests.conftest import ApiClient
from tests.integration.risk.helpers import OWNER, make_risk, set_status


async def _dash(api: ApiClient, role: str = "CEO", **params: Any) -> Any:
    return await api.call("GET", "/risk/dashboard", role, params=params or None)


async def test_dashboard_shape_and_headers(api: ApiClient) -> None:
    res = await _dash(api)
    assert res.status_code == 200, res.text
    assert res.headers["cache-control"] == "private, max-age=60"
    assert "Authorization" in res.headers["vary"]
    d = res.json()["data"]
    assert d["pillar"] == "S" and isinstance(d["open_alerts"], int)  # metric store (T-222)
    assert all(m["metric_code"].startswith("METRIC-RSK-") for m in d["metrics"])
    sei = {m["metric_code"]: m["value"] for m in d["metrics"]}.get("METRIC-RSK-06")
    assert d["summary"]["strategy_execution_index"] == sei
    assert len(d["heatmap"]) == 25 and len(d["risk_score_trend"]) == 6
    keys = [p["period_key"] for p in d["risk_score_trend"]]
    assert keys == sorted(keys) and keys[-1] == d["period"]["key"]
    assert (await _dash(api, period="bogus")).status_code == 400
    assert (await _dash(api, role="RISK_MANAGER")).status_code == 200
    assert (await _dash(api, role="MANAGER")).status_code == 403


async def test_dashboard_counts_delta(api: ApiClient) -> None:
    before = (await _dash(api)).json()["data"]
    crit = await make_risk(api, likelihood=5, impact=4)
    await make_risk(api, likelihood=3, impact=4)
    done = await make_risk(api, likelihood=1, impact=1, owner_id=None)
    assert (await set_status(api, done["id"], "closed", owner_id=OWNER)).status_code == 200
    body = {"risk_id": crit["id"], "title": "m", "owner_id": OWNER, "due_date": "2020-01-01"}
    assert (
        await api.call("POST", "/risk/mitigations", "RISK_MANAGER", json=body)
    ).status_code == 201
    after = (await _dash(api)).json()["data"]
    b, a = before["summary"], after["summary"]
    assert a["open_risks"] - b["open_risks"] == 2
    assert a["critical_count"] - b["critical_count"] == 1
    assert a["high_count"] - b["high_count"] == 1
    assert a["mitigations_active"] - b["mitigations_active"] == 1
    assert a["mitigations_overdue"] - b["mitigations_overdue"] == 1
    cell = next(c for c in after["heatmap"] if (c["likelihood"], c["impact"]) == (5, 4))
    old = next(c for c in before["heatmap"] if (c["likelihood"], c["impact"]) == (5, 4))
    assert cell["count"] - old["count"] == 1
    assert after["status"] == "critical" and a["aggregate_risk_score"] is not None


async def test_dashboard_period_and_trend_far_future(
    api: ApiClient, db_session: AsyncSession
) -> None:
    r = await make_risk(api, likelihood=4, impact=4)
    c = await make_risk(api, likelihood=2, impact=2, owner_id=None)
    await set_status(api, c["id"], "closed", owner_id=OWNER)
    t = datetime(2037, 3, 10, tzinfo=UTC)
    for rid in (r["id"], c["id"]):
        await db_session.execute(
            update(Risk).where(Risk.id == uuid.UUID(rid)).values(identified_at=t, updated_at=t)
        )
    await db_session.flush()
    out = await RiskDashboardService(db_session).dashboard(
        _ceo(), "2037-03", today=date(2037, 3, 20)
    )
    assert out.summary.opened_in_period == 2 and out.summary.closed_in_period == 1
    feb = await RiskDashboardService(db_session).dashboard(
        _ceo(), "2037-02", today=date(2037, 3, 20)
    )
    assert feb.summary.opened_in_period == 0
    assert all(p.open_risks == 0 for p in feb.risk_score_trend)  # nothing identified ≤ Feb 2037
    assert feb.status == "ok"  # RSK-04 no_data alone (1/5) does not make the pillar no_data


def _ceo() -> Any:
    from app.core.deps import Principal

    return Principal(user_id=uuid.uuid4(), role="CEO", permissions=frozenset(), department_id=None)

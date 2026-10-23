"""T-201/T-202 — EP-90 product dashboard (10 §5, FR-PRD-07) — TC-PRD-003.

The DB holds seed data, so company totals are checked as deltas; 2037 trends / quarter only
contain this test's rows.
"""

from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import ApiClient
from tests.integration.product.helpers import make, make_product

pytestmark = pytest.mark.integration


async def dash(api: ApiClient, period: str = "2037-05", role: str = "CPO") -> dict[str, Any]:
    r = await api.call("GET", "/product/dashboard", role, params={"period": period})
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "private, max-age=60"
    assert r.headers["vary"] == "Authorization"
    return dict(r.json()["data"])


async def test_dashboard_summary_and_trends(api: ApiClient, db_session: AsyncSession) -> None:
    before = (await dash(api))["summary"]
    live = await make_product(api, lifecycle_stage="growth")
    await make_product(api, lifecycle_stage="development", status="paused")
    pid = live["id"]
    for period, mau, churn in (("2037-03", 800, 1.0), ("2037-04", 1000, 99.0)):
        r = await api.call(
            "POST",
            f"/product/products/{pid}/metrics",
            "CPO",
            json={
                "period_key": period,
                "mau": mau,
                "churn_rate_pct": churn,
                "nps": 40,
            },
        )
        assert r.status_code == 201
    rel = await make(
        api,
        "releases",
        {
            "product_id": pid,
            "release_version": "1",
            "status": "released",
            "released_at": "2037-05-10T00:00:00Z",
        },
    )
    await make(
        api,
        "features",
        {"product_id": pid, "name": "a", "status": "released", "release_id": rel["id"]},
    )
    await make(api, "features", {"product_id": pid, "name": "b", "status": "released"})
    base = {"product_id": pid, "title": "x", "quarter": "2037-Q2", "target_date": "2037-06-01"}
    await make(api, "roadmap-items", {**base, "status": "in_progress"})
    await make(api, "roadmap-items", {**base, "status": "dropped"})
    late = await make(api, "roadmap-items", base)
    up = await api.call(
        "PATCH",
        f"/product/roadmap-items/{late['id']}",
        "CPO",
        json={"status": "done", "completed_at": "2037-06-10", "version": 1},
    )
    assert up.status_code == 200

    d = await dash(api)
    s = d["summary"]
    assert d["pillar"] == "U" and isinstance(d["open_alerts"], int)
    assert all(m["metric_code"].startswith("METRIC-PRD-") for m in d["metrics"])  # store, T-222
    assert d["period"] == {
        "key": "2037-05",
        "type": "month",
        "start_date": "2037-05-01",
        "end_date": "2037-05-31",
    }
    assert s["products_total"] - before["products_total"] == 2
    assert s["products_active"] - before["products_active"] == 1
    assert s["products_in_dev"] - before["products_in_dev"] == 1
    assert s["mau"] - (before["mau"] or 0) == 1000
    assert s["churn_rate_pct"] == 99.0
    assert s["features_released"] == 1
    assert s["roadmap_on_time_pct"] == 50.0
    assert s["currency"] == "VND"
    assert [p["period_key"] for p in d["mau_trend"]][-1] == "2037-05"
    assert len(d["mau_trend"]) == 12 == len(d["churn_trend"])
    trend = {p["period_key"]: p["mau"] for p in d["mau_trend"]}
    assert (trend["2037-03"], trend["2037-04"], trend["2037-05"]) == (800, 1000, None)
    churn = {p["period_key"]: p["churn_rate_pct"] for p in d["churn_trend"]}
    assert churn["2037-04"] == 99.0 and churn["2037-05"] is None


async def test_dashboard_periods_and_rbac(api: ApiClient) -> None:
    for period in ("2037-Q2", "current_month", "current_quarter", "ytd"):
        assert (await dash(api, period))["period"]["key"]
    assert (await dash(api, "2037-Q2"))["period"]["type"] == "quarter"
    for bad in ("custom", "2037-13", "x"):
        r = await api.call("GET", "/product/dashboard", "CPO", params={"period": bad})
        assert r.status_code == 400 and r.json()["error"]["code"] == "BAD_REQUEST", bad
    # R-DEC-12a: mọi DIR có product:query → đọc dashboard tổng hợp (gồm HR-DIR, ex HR_MANAGER).
    for role in ("CEO", "CFO", "VP_SALES", "RISK_MANAGER", "HR_MANAGER"):
        await dash(api, role=role)
    mgr = await api.call("GET", "/product/dashboard", "MANAGER")
    assert mgr.status_code == 200
    # Vai không phải DIR và không có product:query → 403.
    for role in ("EMPLOYEE", "REVIEWER", "ADMIN"):
        r = await api.call("GET", "/product/dashboard", role)
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_ROLE", role
    default = await api.call("GET", "/product/dashboard", "CPO")
    assert default.json()["data"]["period"]["type"] == "month"

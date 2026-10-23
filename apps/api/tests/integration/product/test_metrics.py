"""T-202 — EP-95 append-only snapshots + BR-PRD-01 `product.metric_anomaly` (TC-PRD-002)."""

import uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.product.models import ProductMetric
from tests.conftest import ApiClient
from tests.integration.product.helpers import audit_actions, make_product, outbox_for

pytestmark = pytest.mark.integration


def snap(period: str, churn: float, **kw: Any) -> dict[str, Any]:
    return {"period_key": period, "mau": 1000, "churn_rate_pct": churn, **kw}


async def post(api: ApiClient, pid: str, body: dict[str, Any], role: str = "CPO") -> Any:
    return await api.call("POST", f"/product/products/{pid}/metrics", role, json=body)


async def anomalies(db: AsyncSession, pid: str) -> list[dict[str, Any]]:
    return [p for e, p in await outbox_for(db, pid) if e == "product.metric_anomaly"]


async def test_snapshot_append_and_supersede(api: ApiClient, db_session: AsyncSession) -> None:
    p = await make_product(api)
    body = snap("2037-01", 1.5, dau=300, adoption_pct=40, retention_30d_pct=55, nps=42, arpu=9)
    first = await post(api, p["id"], body)
    assert first.status_code == 201, first.text
    m1 = first.json()["data"]
    assert m1["adoption_pct"] == 40.0 and m1["nps"] == 42.0 and m1["superseded_by_id"] is None
    second = await post(api, p["id"], {**body, "mau": 1200})
    m2 = second.json()["data"]
    lst = await api.call("GET", f"/product/products/{p['id']}/metrics", "CEO")
    assert [x["id"] for x in lst.json()["data"]] == [m2["id"]]
    old = await db_session.get(ProductMetric, uuid.UUID(m1["id"]))
    assert old is not None
    await db_session.refresh(old)
    assert old.superseded_by_id == uuid.UUID(m2["id"]) and old.mau == 1000
    assert await audit_actions(db_session, m1["id"]) == [
        "product.metric_create",
        "product.metric_supersede",
    ]
    bad = await post(api, p["id"], {**body, "dau": 5000})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    for wrong in (snap("2037-13", 1), snap("2037-01", 101), {**body, "nps": -101}):
        assert (await post(api, p["id"], wrong)).status_code == 422, wrong
    missing = await post(api, str(uuid.uuid4()), body)
    assert missing.status_code == 404
    rows = await db_session.execute(
        select(ProductMetric.id).where(ProductMetric.product_id == uuid.UUID(p["id"]))
    )
    assert len(rows.all()) == 2


async def test_metric_rbac(api: ApiClient) -> None:
    p = await make_product(api)
    for role in ("CEO", "CFO", "VP_SALES", "RISK_MANAGER"):
        r = await post(api, p["id"], snap("2037-02", 1), role=role)
        assert r.status_code == 403, role
    mgr = await api.call(
        "POST",
        f"/product/products/{p['id']}/metrics",
        "MANAGER",
        json=snap("2037-02", 1),
        department_id=uuid.uuid4(),
    )
    assert mgr.status_code == 403 and mgr.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    # R-DEC-12a: mọi DIR có product:query → đọc tổng hợp (gồm HR-DIR, ex HR_MANAGER).
    for role in ("CFO", "VP_SALES", "RISK_MANAGER", "CPO", "HR_MANAGER"):
        r = await api.call("GET", f"/product/products/{p['id']}/metrics", role)
        assert r.status_code == 200, role
    # Vai không phải DIR và không có product:query → 403.
    for role in ("EMPLOYEE", "REVIEWER", "ADMIN"):
        r = await api.call("GET", f"/product/products/{p['id']}/metrics", role)
        assert r.status_code == 403, role


async def test_br_prd_01_anomaly_once(api: ApiClient, db_session: AsyncSession) -> None:
    """03 §5.4 example: avg 1.2% → 2.0% = +66.7% and ≥ 2% → anomaly."""
    p = await make_product(api)
    for period, churn in (("2037-01", 1.0), ("2037-02", 1.2), ("2037-03", 1.4)):
        assert (await post(api, p["id"], snap(period, churn))).status_code == 201
    assert await anomalies(db_session, p["id"]) == []
    hit = (await post(api, p["id"], snap("2037-04", 2.0))).json()["data"]
    assert await anomalies(db_session, p["id"]) == [
        {
            "product_metric_id": hit["id"],
            "product_id": p["id"],
            "metric": "churn_rate_pct",
            "value": 2.0,
            "baseline": 1.2,
        }
    ]
    await post(api, p["id"], snap("2037-04", 2.5))  # correction, same period → no re-publish
    assert len(await anomalies(db_session, p["id"])) == 1


async def test_br_prd_01_no_anomaly_cases(api: ApiClient, db_session: AsyncSession) -> None:
    p = await make_product(api)
    for period in ("2037-01", "2037-02", "2037-03"):
        await post(api, p["id"], snap(period, 1.0))
    await post(api, p["id"], snap("2037-04", 1.8))  # +80% but < 2% floor
    await post(api, p["id"], snap("2037-05", 1.4))  # base (1+1+1.8)/3=1.27 → 1.4 not > 1.9
    q = await make_product(api)
    await post(api, q["id"], snap("2037-02", 1.0))
    await post(api, q["id"], snap("2037-04", 9.0))  # incomplete baseline → no rule
    assert await anomalies(db_session, p["id"]) == []
    assert await anomalies(db_session, q["id"]) == []


async def test_seed_fixture_values(api: ApiClient, db_session: AsyncSession) -> None:
    """14 TC-PRD-002: 2.41% vs 1.5% → anomaly; 1.79% vs 1.5% → none (fixture, not seed)."""
    a, b = await make_product(api), await make_product(api)
    for pid in (a["id"], b["id"]):
        for period in ("2037-06", "2037-07", "2037-08"):
            await post(api, pid, snap(period, 1.5))
    await post(api, a["id"], snap("2037-09", 2.41))
    await post(api, b["id"], snap("2037-09", 1.79))
    assert len(await anomalies(db_session, a["id"])) == 1
    assert await anomalies(db_session, b["id"]) == []


async def test_numbers_are_append_only(api: ApiClient) -> None:
    """No U/D route on EP-95 (05 C5): numbers change only through a superseding snapshot."""
    p = await make_product(api)
    m = (await post(api, p["id"], snap("2037-10", 1.0))).json()["data"]
    url = f"/product/products/{p['id']}/metrics"
    for method in ("PATCH", "PUT", "DELETE"):
        assert (await api.call(method, url, "CPO", json={})).status_code == 405, method
    assert (await api.call(method, f"{url}/{m['id']}", "CPO")).status_code in (404, 405)

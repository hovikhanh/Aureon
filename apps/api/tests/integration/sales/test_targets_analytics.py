"""T-112 — EP-77 targets, EP-75 pipeline, EP-76 performance, EP-70 dashboard (TC-SAL-002)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sales.models import Deal, SalesTarget
from app.modules.sales.services import calculations as calc
from tests.conftest import ApiClient
from tests.integration.sales.helpers import audit_actions, make_client, make_deal, stage

pytestmark = pytest.mark.integration

TODAY = datetime.now(UTC).date()
MONTH = calc.month_period(TODAY.year, TODAY.month)
QUARTER = calc.quarter_of(TODAY)


def target(**kw: Any) -> dict[str, Any]:
    return {"period_type": "quarter", "period_key": "2099-Q1", "scope": "team",
            "target_amount": 10_000_000_000, **kw}  # fmt: skip


# ---------- EP-77 ----------
async def test_target_crud_and_rules(api: ApiClient, db_session: AsyncSession) -> None:
    r = await api.call("POST", "/sales/targets", "CEO", json=target())
    assert r.status_code == 201, r.text
    t = r.json()["data"]
    assert t["period_type"] == "quarter" and t["owner_id"] is None
    dup = await api.call("POST", "/sales/targets", "VP_SALES", json=target())
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    owner = str(uuid.uuid4())
    ind = await api.call(
        "POST", "/sales/targets", "VP_SALES",
        json=target(scope="individual", owner_id=owner, period_type="month", period_key="2099-01"),
    )  # fmt: skip
    assert ind.status_code == 201
    for bad in (target(scope="individual"), target(owner_id=owner),
                target(period_key="2099-01"), target(target_amount=0)):  # fmt: skip
        resp = await api.call("POST", "/sales/targets", "VP_SALES", json=bad)
        assert resp.status_code == 422, bad
    lst = await api.call(
        "GET", "/sales/targets", "VP_SALES",
        params={"period_key": "2099-01", "scope": "individual", "sort_by": "target_amount"},
    )  # fmt: skip
    assert [x["id"] for x in lst.json()["data"]] == [ind.json()["data"]["id"]]
    p = await api.call(
        "PATCH", f"/sales/targets/{t['id']}", "CEO", json={"target_amount": 12, "version": 1}
    )
    assert p.status_code == 200 and p.json()["data"]["target_amount"] == 12
    bad_amt = await api.call(
        "PATCH", f"/sales/targets/{t['id']}", "CEO", json={"target_amount": -1, "version": 2}
    )
    assert bad_amt.status_code == 422
    assert (await api.call("GET", f"/sales/targets/{t['id']}", "CEO")).status_code == 200
    mgr = await api.call("POST", "/sales/targets", "MANAGER", json=target(period_key="2099-Q2"))
    assert mgr.status_code == 403 and mgr.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    assert (await api.call("DELETE", f"/sales/targets/{t['id']}", "MANAGER")).status_code == 403
    assert (await api.call("DELETE", f"/sales/targets/{t['id']}", "CEO")).status_code == 204
    assert (await api.call("GET", f"/sales/targets/{t['id']}", "CEO")).status_code == 404
    assert await audit_actions(db_session, t["id"]) == [
        "sales.target_create", "sales.target_delete", "sales.target_update",
    ]  # fmt: skip


# ---------- analytics fixtures ----------
async def _book(api: ApiClient, db: AsyncSession) -> dict[str, Any]:
    """2 open deals closing this quarter, 1 won + 1 lost this month, 1 won in an old month.

    Seed data (T-236) is soft-deleted inside the rolled-back test transaction so the
    aggregates below see only this book."""
    gone = {"deleted_at": datetime.now(UTC)}
    await db.execute(update(Deal).where(Deal.deleted_at.is_(None)).values(**gone))
    await db.execute(update(SalesTarget).where(SalesTarget.deleted_at.is_(None)).values(**gone))
    c = await make_client(api)
    alice, bob = str(uuid.uuid4()), str(uuid.uuid4())
    o1 = await make_deal(api, c["id"], owner_id=alice, deal_value=2_000_000_000,
                         probability_pct=50, expected_close_date="2099-12-31")  # fmt: skip
    await stage(api, o1["id"], "proposal")
    await make_deal(api, c["id"], owner_id=bob, deal_value=1_000_000_000,
                    probability_pct=10, expected_close_date="2099-12-31")  # fmt: skip
    w = await make_deal(api, c["id"], owner_id=alice, deal_value=600_000_000)
    assert (await stage(api, w["id"], "closed_won")).status_code == 200
    lo = await make_deal(api, c["id"], owner_id=bob, deal_value=400_000_000)
    assert (await stage(api, lo["id"], "closed_lost", lost_reason="giá")).status_code == 200
    old = await make_deal(api, c["id"], owner_id=alice, deal_value=900_000_000)
    await stage(api, old["id"], "closed_won")
    long_ago = datetime.now(UTC) - timedelta(days=400)
    await db.execute(update(Deal).where(Deal.id == uuid.UUID(old["id"])).values(closed_at=long_ago))
    await db.execute(
        update(Deal)
        .where(Deal.id == uuid.UUID(w["id"]))
        .values(created_at=datetime.now(UTC) - timedelta(days=10))
    )
    in_quarter = update(Deal).where(
        Deal.client_id == uuid.UUID(c["id"]), Deal.stage != "closed_won"
    )
    await db.execute(in_quarter.values(expected_close_date=QUARTER.end))  # robust on quarter end
    db.expire_all()  # identity map holds the pre-UPDATE rows
    for body in (
        {"period_type": "quarter", "period_key": QUARTER.key, "scope": "team",
         "target_amount": 1_000_000_000},
        {"period_type": "month", "period_key": MONTH.key, "scope": "team",
         "target_amount": 1_200_000_000},
        {"period_type": "month", "period_key": MONTH.key, "scope": "individual",
         "owner_id": alice, "target_amount": 300_000_000},
    ):  # fmt: skip
        assert (await api.call("POST", "/sales/targets", "CEO", json=body)).status_code == 201
    return {"alice": alice, "bob": bob, "open1": o1["id"]}


async def test_pipeline(api: ApiClient, db_session: AsyncSession) -> None:
    book = await _book(api, db_session)
    r = await api.call("GET", "/sales/pipeline", "VP_SALES")
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    by = {s["stage"]: s for s in data["stages"]}
    assert [s["stage"] for s in data["stages"]] == list(calc.STAGE_ORDER)
    assert by["proposal"]["count"] == 1 and by["proposal"]["weighted_value"] == 1_000_000_000
    assert by["lead"]["value"] == 1_000_000_000 and by["lead"]["avg_days_in_stage"] is not None
    assert by["closed_won"]["count"] == 2 and data["period"] is None
    assert data["coverage_ratio"] == 3.0  # BR-SAL-04: 3 tỷ open in quarter / 1 tỷ
    month = await api.call("GET", "/sales/pipeline", "CFO", params={"period": "current_month"})
    mby = {s["stage"]: s for s in month.json()["data"]["stages"]}
    assert mby["closed_won"]["count"] == 1 and mby["closed_lost"]["value"] == 400_000_000
    own = await api.call("GET", "/sales/pipeline", "VP_SALES", params={"owner_id": book["bob"]})
    oby = {s["stage"]: s for s in own.json()["data"]["stages"]}
    assert oby["proposal"]["count"] == 0 and oby["lead"]["count"] == 1
    assert own.json()["data"]["coverage_ratio"] is None  # bob has no quarter target
    agg_only = await api.call("GET", "/sales/pipeline", "CFO", params={"owner_id": book["bob"]})
    assert agg_only.status_code == 403
    bad = await api.call("GET", "/sales/pipeline", "VP_SALES", params={"period": "custom"})
    assert bad.status_code == 400
    assert (await api.call("GET", "/sales/pipeline", "HR_MANAGER")).status_code == 403


async def test_performance(api: ApiClient, db_session: AsyncSession) -> None:
    book = await _book(api, db_session)
    team = await api.call("GET", "/sales/performance", "CFO")
    assert team.json()["data"] == [{
        "owner_ref": "team", "closed_value": 600_000_000, "quota": 1_200_000_000,
        "attainment_pct": 50.0, "win_rate_pct": 50.0,
    }]  # fmt: skip
    own = await api.call("GET", "/sales/performance", "VP_SALES", params={"group_by": "owner"})
    rows = {r["owner_ref"]: r for r in own.json()["data"]}
    assert rows[book["alice"]]["attainment_pct"] == 200.0
    assert rows[book["bob"]]["win_rate_pct"] == 0.0 and rows[book["bob"]]["quota"] is None
    denied = await api.call("GET", "/sales/performance", "CFO", params={"group_by": "owner"})
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "FORBIDDEN_SCOPE"


async def test_dashboard_contract(api: ApiClient, db_session: AsyncSession) -> None:
    await _book(api, db_session)
    r = await api.call("GET", "/sales/dashboard", "CEO")
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "private, max-age=60"
    assert r.headers["vary"] == "Authorization"
    d = r.json()["data"]
    assert d["pillar"] == "C" and d["status"] == "no_data" and d["metrics"] == []
    assert d["period"]["key"] == MONTH.key and d["period"]["type"] == "month"
    s = d["summary"]
    assert s == {
        "pipeline_value": 3_000_000_000, "weighted_pipeline": 1_100_000_000, "deals_open": 2,
        "deals_won": 1, "deals_lost": 1, "win_rate_pct": 50.0, "avg_deal_value": 600_000_000,
        "closed_revenue": 600_000_000, "quota_attainment_pct": 50.0,
        "avg_sales_cycle_days": s["avg_sales_cycle_days"], "pipeline_coverage": 3.0,
        "currency": "VND",
    }  # fmt: skip
    assert 9.9 <= s["avg_sales_cycle_days"] <= 10.1
    trend = d["win_rate_trend"]
    assert len(trend) == 6 and trend[-1]["period_key"] == MONTH.key
    assert trend[-1]["win_rate_pct"] == 50.0
    assert [p["period_key"] for p in d["pipeline_trend"]] == sorted(
        p["period_key"] for p in d["pipeline_trend"]
    )
    assert d["pipeline_trend"][-1]["pipeline_value"] == 3_000_000_000
    q = await api.call("GET", "/sales/dashboard", "RISK_MANAGER", params={"period": "ytd"})
    assert q.status_code == 200 and q.json()["data"]["period"]["type"] == "ytd"
    assert (await api.call("GET", "/sales/dashboard", "HR_MANAGER")).status_code == 403


async def test_manager_analytics_scoped(api: ApiClient, db_session: AsyncSession) -> None:
    await _book(api, db_session)
    dept = uuid.uuid4()
    c = await make_client(api)
    await make_deal(api, c["id"], "MANAGER", department_id=dept, deal_value=70)
    r = await api.call("GET", "/sales/dashboard", "MANAGER", department_id=dept)
    s = r.json()["data"]["summary"]
    assert s["pipeline_value"] == 70 and s["deals_open"] == 1
    assert s["quota_attainment_pct"] is None and s["pipeline_coverage"] is None
    perf = await api.call(
        "GET", "/sales/performance", "MANAGER", department_id=dept, params={"group_by": "owner"}
    )
    assert perf.status_code == 200 and perf.json()["data"] == []

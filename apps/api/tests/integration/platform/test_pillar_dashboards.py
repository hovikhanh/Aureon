"""TC-DASH-004/005 (T-222): domain pillar dashboards read `metrics[]` + `open_alerts` from the
metric store, isolated from store failures (FR-DSH-07), with private cache + Vary."""

from datetime import date
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import METRIC_PROVIDERS, MetricReading
from app.modules.platform.services import metric_query, pillar_snapshot
from app.modules.platform.services.metric_store import MetricStore
from tests.conftest import ApiClient

AS_OF = date(2036, 2, 10)
P = "2036-01"
ENDPOINTS = (("F", "/finance/dashboard", "CFO"), ("C", "/sales/dashboard", "VP_SALES"),
             ("O", "/hr/dashboard", "HR_MANAGER"), ("U", "/product/dashboard", "CPO"),
             ("S", "/risk/dashboard", "RISK_MANAGER"))  # fmt: skip


async def _store(db: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    async def provider(_db: AsyncSession, _as_of: date) -> list[MetricReading]:
        return [MetricReading("METRIC-CUS-03", 80.0, P), MetricReading("METRIC-HR-02", 30.0, P),
                MetricReading("METRIC-FIN-05", 40.0, P),
                MetricReading("METRIC-PRD-03", 10.0, P),
                MetricReading("METRIC-RSK-04", 20.0, P)]  # fmt: skip

    monkeypatch.setattr(METRIC_PROVIDERS, "providers", {"fake": provider})
    await MetricStore(db).recompute(AS_OF)


@pytest.mark.parametrize(("pillar", "url", "role"), ENDPOINTS)
async def test_pillar_endpoints_read_store(
    api: ApiClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch,
    pillar: str, url: str, role: str,
) -> None:  # fmt: skip
    await _store(db_session, monkeypatch)
    r = await api.call("GET", url, role)
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "private, max-age=60"
    assert r.headers["vary"] == "Authorization"
    d = r.json()["data"]
    assert d["pillar"] == pillar and d["open_alerts"] >= 1
    if pillar != "F":  # finance keeps its live metric list (FIN-01..07)
        codes = {m["metric_code"] for m in d["metrics"]}
        assert {"METRIC-CUS-03", "METRIC-HR-02", "METRIC-PRD-03", "METRIC-RSK-04"} & codes
        assert all(
            m["lineage_url"] == f"/dashboard/metrics/{m['metric_code']}" for m in d["metrics"]
        )


@pytest.mark.parametrize(("pillar", "url", "role"), ENDPOINTS)
async def test_store_failure_is_isolated(
    api: ApiClient, monkeypatch: pytest.MonkeyPatch, pillar: str, url: str, role: str
) -> None:
    async def boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("metric store down")

    monkeypatch.setattr(metric_query.MetricQueryService, "current_values", boom)
    r = await api.call("GET", url, role)
    assert r.status_code == 200, r.text  # domain summary still served
    d = r.json()["data"]
    assert d["pillar"] == pillar and "summary" in d
    assert d["metrics"] == [] or pillar == "F"
    assert d["open_alerts"] == (0 if pillar in ("F", "S") else None)


async def test_snapshot_helpers(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    await _store(db_session, monkeypatch)
    snap = await pillar_snapshot.pillar_snapshot(db_session, "C", codes={"METRIC-CUS-03"})
    assert [m["metric_code"] for m in snap.metrics] == ["METRIC-CUS-03"] and snap.available
    assert pillar_snapshot.pillar_status_of([]) == "no_data"
    assert pillar_snapshot.pillar_status_of(["ok", "no_data"]) == "no_data"
    assert pillar_snapshot.pillar_status_of(["ok", "warning", "critical"]) == "critical"

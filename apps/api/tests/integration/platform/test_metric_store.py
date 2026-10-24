"""TC-PLT-020..026 (T-220/T-221): metric catalog, store, threshold → alert lifecycle, EP-11..17.

Uses fake providers with far-future periods (2036-xx) so seeded data never interferes; all
writes roll back with the test transaction.
"""

from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.envelope import OUTBOX
from app.core.metrics import METRIC_PROVIDERS, MetricReading, RecordRef
from app.modules.platform.models import Alert, DataLineage, Metric, MetricValue, SystemSetting
from app.modules.platform.services.catalog import CATALOG, evaluate
from app.modules.platform.services.metric_store import MetricStore, seed_catalog, setting_key
from tests.conftest import ApiClient

AS_OF = date(2036, 2, 10)
P = "2036-01"


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[MetricReading]]:
    box: dict[str, list[MetricReading]] = {"readings": []}

    async def provider(db: AsyncSession, as_of: date) -> list[MetricReading]:
        return box["readings"]

    async def broken(db: AsyncSession, as_of: date) -> list[MetricReading]:
        raise RuntimeError("domain down")

    monkeypatch.setattr(METRIC_PROVIDERS, "providers", {"fake": provider, "broken": broken})
    return box


async def _alerts(db: AsyncSession, code: str) -> list[Alert]:
    stmt = (
        select(Alert)
        .join(Metric, Alert.metric_id == Metric.id)
        .where(Metric.code == code, Alert.period_key == P)
    )
    return list((await db.execute(stmt)).scalars())


async def _raised_events(db: AsyncSession) -> int:
    stmt = (
        select(func.count())
        .select_from(OUTBOX)
        .where(
            OUTBOX.c.event_type == "platform.alert_raised",
            OUTBOX.c.payload["period_key"].astext == P,
        )
    )
    return int((await db.execute(stmt)).scalar_one())


def test_catalog_has_32_metrics_and_threshold_rules() -> None:
    # 32 base METRIC-* + METRIC-STR-01 (G2, M1.4 R-DEC-54) + METRIC-DQ-02 (G3, M1.5 R-DEC-68)
    assert len(CATALOG) == 34 and len({m.code for m in CATALOG}) == 34
    assert sum(m.pillar is None for m in CATALOG) == 2  # DQ-01, DQ-02
    assert evaluate("LOWER_IS_BAD", 8, 12, 6, False) == "warning"
    assert evaluate("LOWER_IS_BAD", 5, 12, 6, False) == "critical"
    assert evaluate("HIGHER_IS_BAD", 15, 15, 20, True) == "warning"
    assert evaluate("HIGHER_IS_BAD", 15, 15, 20, False) == "ok"
    assert evaluate("HIGHER_IS_BAD", 21, 15, 20, False) == "critical"


async def test_seed_catalog_idempotent_keeps_thresholds(db_session: AsyncSession) -> None:
    await seed_catalog(db_session)
    m = (
        await db_session.execute(select(Metric).where(Metric.code == "METRIC-FIN-03"))
    ).scalar_one()
    m.warning_threshold = 9  # ADMIN-tuned threshold survives a re-seed (NFR-19)
    assert await seed_catalog(db_session) == 0
    assert int((await db_session.execute(select(func.count(Metric.id)))).scalar_one()) == 34
    await db_session.refresh(m)
    assert float(m.warning_threshold) == 9


async def test_store_values_lineage_and_alert_lifecycle(
    db_session: AsyncSession, fake: dict[str, list[MetricReading]]
) -> None:
    store = MetricStore(db_session)
    ref = RecordRef("finance", "budgets", "00000000-0000-0000-0000-00000000000a", 1.0)
    fake["readings"] = [
        MetricReading("METRIC-FIN-03", 8.0, P, records=(ref,)),  # < 12 → warning
        MetricReading("METRIC-FIN-05", 30.0, P),  # > 25 → critical
        MetricReading("METRIC-FIN-01", None, P, status_reason="NO_TARGET"),  # no_data
        MetricReading("METRIC-XXX-99", 1.0, P),  # unknown → ignored
        MetricReading("METRIC-FIN-06", 12.0, P, scope_type="department",
                      scope_id="00000000-0000-0000-0000-0000000000d1"),  # no alert (scope)
    ]  # fmt: skip
    stats = await store.recompute(AS_OF)
    assert stats == {"values": 4, "raised": 2, "resolved": 0, "failed_providers": 1}
    assert [a.severity for a in await _alerts(db_session, "METRIC-FIN-03")] == ["WARNING"]
    assert [a.severity for a in await _alerts(db_session, "METRIC-FIN-05")] == ["CRITICAL"]
    assert await _alerts(db_session, "METRIC-FIN-06") == []
    assert await _raised_events(db_session) == 2
    n_lineage = select(func.count(DataLineage.id)).where(DataLineage.target_table == "budgets")
    assert int((await db_session.execute(n_lineage)).scalar_one()) >= 1

    # same values again → no duplicate alert, old value no longer current
    await store.recompute(AS_OF)
    assert len(await _alerts(db_session, "METRIC-FIN-03")) == 1
    cur = (
        select(func.count(MetricValue.id))
        .join(Metric)
        .where(Metric.code == "METRIC-FIN-03", MetricValue.period_key == P, MetricValue.is_current)
    )
    assert int((await db_session.execute(cur)).scalar_one()) == 1

    # warning → critical escalates in place (+1 event); back to ok resolves
    fake["readings"] = [MetricReading("METRIC-FIN-03", 4.0, P)]
    assert (await store.recompute(AS_OF))["raised"] == 1
    (a,) = await _alerts(db_session, "METRIC-FIN-03")
    assert a.severity == "CRITICAL" and a.status == "OPEN"
    assert await _raised_events(db_session) == 3
    fake["readings"] = [MetricReading("METRIC-FIN-03", 20.0, P)]
    assert (await store.recompute(AS_OF))["resolved"] == 1
    (a,) = await _alerts(db_session, "METRIC-FIN-03")
    assert a.status == "RESOLVED" and a.resolved_at is not None

    # explicit status + threshold_input override the raw value
    fake["readings"] = [
        MetricReading("METRIC-RSK-01", 2.0, P, status="critical"),
        MetricReading("METRIC-FIN-02", 40.0, P, threshold_input=6.0),  # drop 6 pts → critical
    ]
    await store.recompute(AS_OF, modules={"fake"})
    assert [a.severity for a in await _alerts(db_session, "METRIC-RSK-01")] == ["CRITICAL"]
    assert [a.severity for a in await _alerts(db_session, "METRIC-FIN-02")] == ["CRITICAL"]
    assert (await store.recompute(AS_OF, modules={"none"}))["values"] == 0


async def _seed_alerts(db: AsyncSession, fake: dict[str, list[MetricReading]]) -> None:
    fake["readings"] = [
        MetricReading("METRIC-FIN-03", 8.0, P),
        MetricReading("METRIC-FIN-01", 70.0, P),
        MetricReading("METRIC-CUS-01", 2.0, P),
        MetricReading("METRIC-HR-02", 16.0, P),
        MetricReading("METRIC-DQ-01", 50.0, P),
    ]
    await MetricStore(db).recompute(AS_OF)


async def test_ep11_metrics_scoped_by_pillar(
    api: ApiClient, db_session: AsyncSession, fake: dict[str, list[MetricReading]]
) -> None:
    await _seed_alerts(db_session, fake)
    r = await api.call("GET", "/dashboard/metrics", "CEO")
    assert r.status_code == 200 and r.headers["vary"] == "Authorization"
    assert "max-age=60" in r.headers["cache-control"]
    by = {m["metric_code"]: m for m in r.json()["data"]}
    fin3 = by["METRIC-FIN-03"]
    assert fin3["status"] == "warning" and fin3["unit"] == "MONTHS" and fin3["period_key"] == P
    assert fin3["lineage_url"] == "/dashboard/metrics/METRIC-FIN-03"
    assert "METRIC-DQ-01" not in by  # platform metric has no pillar
    vp = await api.call("GET", "/dashboard/metrics", "VP_SALES")
    codes = {m["metric_code"] for m in vp.json()["data"]}
    assert "METRIC-FIN-01" in codes and "METRIC-FIN-03" not in codes and "METRIC-HR-02" not in codes
    f = await api.call(
        "GET", "/dashboard/metrics", "CEO", params={"pillar": "F", "status": "warning"}
    )
    assert {m["metric_code"] for m in f.json()["data"]} >= {"METRIC-FIN-03"}
    assert all(m["pillar"] == "F" and m["status"] == "warning" for m in f.json()["data"])
    assert (await api.call("GET", "/dashboard/metrics", "ADMIN")).status_code == 403
    bad = await api.call("GET", "/dashboard/metrics", "CEO", params={"pillar": "X"})
    assert bad.status_code in (400, 422)


async def test_ep12_metric_detail(
    api: ApiClient, db_session: AsyncSession, fake: dict[str, list[MetricReading]]
) -> None:
    await _seed_alerts(db_session, fake)
    r = await api.call("GET", "/dashboard/metrics/METRIC-FIN-03", "CFO")
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["thresholds"] == {"warning": 12.0, "critical": 6.0} and d["direction"] == "up"
    assert d["trend"][-1] == {"period_key": P, "value": 8.0} and d["name"] == "Cash runway"
    assert d["related_alerts"][0]["alert_code"] == "ALERT-FIN-03"
    assert d["data_source"]["module"] == "finance"
    en = await api.call("GET", "/dashboard/metrics/METRIC-HR-02", "CEO",
                        headers={"Accept-Language": "en"})  # fmt: skip
    assert en.json()["data"]["name"] == "Annualized turnover"
    denied = await api.call("GET", "/dashboard/metrics/METRIC-FIN-03", "VP_SALES")
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    missing = await api.call("GET", "/dashboard/metrics/METRIC-NOPE-01", "CEO")
    assert missing.status_code == 404


async def test_ep15_16_17_alert_lifecycle(
    api: ApiClient, db_session: AsyncSession, fake: dict[str, list[MetricReading]]
) -> None:
    await _seed_alerts(db_session, fake)
    r = await api.call("GET", "/dashboard/alerts", "CEO", params={"status": "open", "limit": 100})
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    mine = [a for a in r.json()["data"] if a["period_key"] == P]
    codes = {a["alert_code"] for a in mine}
    assert {"ALERT-FIN-03", "ALERT-FIN-01", "ALERT-CUS-01", "ALERT-HR-02"} <= codes
    assert r.json()["meta"]["pagination"]["total"] >= 4
    fin3 = next(a for a in mine if a["alert_code"] == "ALERT-FIN-03")
    assert fin3["severity"] == "warning" and fin3["threshold"] == 12.0 and fin3["value"] == 8.0
    assert fin3["message_key"] == "alert.alert_fin_03.warning"

    hr = await api.call("GET", "/dashboard/alerts", "HR_MANAGER", params={"limit": 100})
    hr_codes = {a["alert_code"] for a in hr.json()["data"] if a["period_key"] == P}
    assert "ALERT-HR-02" in hr_codes and "ALERT-FIN-01" in hr_codes
    assert "ALERT-FIN-03" not in hr_codes and "ALERT-CUS-01" not in hr_codes

    url = f"/dashboard/alerts/{fin3['id']}"
    ack = await api.call("POST", f"{url}/acknowledge", "CFO", json={"note": "đang xử lý"})
    assert ack.status_code == 200 and ack.json()["data"]["status"] == "acknowledged"
    again = await api.call("POST", f"{url}/acknowledge", "CFO", json={})
    assert again.status_code == 409 and again.json()["error"]["code"] == "CONFLICT_STATE"
    scope = await api.call("POST", f"{url}/dismiss", "HR_MANAGER", json={"reason": "x"})
    assert scope.status_code == 403
    no_reason = await api.call("POST", f"{url}/dismiss", "CFO", json={"reason": ""})
    assert no_reason.status_code == 422
    dis = await api.call("POST", f"{url}/dismiss", "CFO", json={"reason": "đã có kế hoạch"})
    assert dis.status_code == 200 and dis.json()["data"]["status"] == "dismissed"
    twice = await api.call("POST", f"{url}/dismiss", "CFO", json={"reason": "again"})
    assert twice.status_code == 409
    nf = await api.call("POST", "/dashboard/alerts/00000000-0000-0000-0000-000000000000/dismiss",
                        "CFO", json={"reason": "x"})  # fmt: skip
    assert nf.status_code == 404
    no_idem = await api.http.post(f"/api/v1{url}/acknowledge", json={}, headers=api.headers("CFO"))
    assert no_idem.status_code == 400


async def test_threshold_setting_overrides_catalog(
    db_session: AsyncSession, fake: dict[str, list[MetricReading]]
) -> None:
    """TC-DASH-002: `THR_FIN_03_WARN` in SystemSetting changes the status (03 §1.3, NFR-19)."""
    db_session.add_all([
        SystemSetting(key="THR_FIN_03_WARN", value=6),
        SystemSetting(key="THR_FIN_03_CRIT", value=3),
        SystemSetting(key="THR_FIN_05_WARN", value=True),  # ignored: not numeric
    ])  # fmt: skip
    await db_session.flush()
    fake["readings"] = [MetricReading("METRIC-FIN-03", 8.0, P)]  # default 12/6 → warning
    assert (await MetricStore(db_session).recompute(AS_OF))["raised"] == 0
    assert setting_key("METRIC-FIN-03", "WARN") == "THR_FIN_03_WARN"

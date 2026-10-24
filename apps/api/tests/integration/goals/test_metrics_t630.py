"""T-630 — TC-M14-13: METRIC-STR-01 (G2, R-DEC-54) + SEI refresh / drill-down.

Unit table on the pure `str01` / `due_period`; integration through `compute` on rows created
in the rolled-back test session (provider inputs pinned to those rows).
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.models import KeyResult
from app.modules.execution.services import metrics
from app.modules.execution.services.metrics import due_period, str01
from app.modules.platform.events import consumers as platform_consumers
from app.modules.platform.models import Alert, Metric
from app.modules.platform.services.catalog import BY_CODE, LO
from app.modules.platform.services.metric_store import MetricStore, seed_catalog
from tests.conftest import ApiClient
from tests.integration.execution.helpers import make, patch, uniq

pytestmark = pytest.mark.integration

AS_OF = date(2037, 6, 20)


def _kr(days_ago: int | None) -> KeyResult:
    at = None if days_ago is None else datetime(2037, 6, 20, 5, tzinfo=UTC) - timedelta(
        days=days_ago)  # fmt: skip
    return KeyResult(id=uuid.uuid4(), last_checked_in_at=at)


def test_catalog_entry() -> None:
    d = BY_CODE["METRIC-STR-01"]
    assert (d.direction, d.warning, d.critical, d.source_module, d.unit) == (
        LO, 80, 60, "execution", "PERCENT")  # fmt: skip
    assert set(d.refresh_events) == {"execution.kpi_measured", "execution.okr_checked_in"}
    assert "execution.kpi_measured" in BY_CODE["METRIC-RSK-06"].refresh_events
    assert platform_consumers.AFFECTS["execution.okr_checked_in"] == {"execution"}


@pytest.mark.parametrize(("ptype", "as_of", "grace", "key"), [
    ("MONTH", date(2037, 6, 5), 5, "2037-04"),  # May not yet past grace (≤ 5 Jun)
    ("MONTH", date(2037, 6, 6), 5, "2037-05"),
    ("QUARTER", date(2037, 7, 4), 5, "2037-Q1"),
    ("QUARTER", date(2037, 7, 6), 5, "2037-Q2"),
    ("YEAR", date(2037, 3, 1), 5, "2036"),
])  # fmt: skip
def test_due_period(ptype: str, as_of: date, grace: int, key: str) -> None:
    assert due_period(ptype, as_of, grace) == key


def test_str01_formula_and_records() -> None:
    """KR check-in 6/7 days → on time, 8 / never → late; KPI-period on time vs late."""
    a, b = uuid.uuid4(), uuid.uuid4()
    krs = [_kr(6), _kr(7), _kr(8), _kr(None)]
    r = str01([(a, "2037-05"), (b, "2037-05")], {(a, "2037-05")}, krs, AS_OF, 7, "2037-06")
    assert r.code == "METRIC-STR-01" and r.value == 50.0  # (1 + 2) / (2 + 4)
    assert [(x.table, x.id) for x in r.records] == [
        ("kpis", str(b)),
        ("key_results", str(krs[2].id)),
        ("key_results", str(krs[3].id)),
    ]
    empty = str01([], set(), [], AS_OF, 7, "2037-06")
    assert empty.value is None and empty.status_reason


def _code() -> str:
    return "G-" + uuid.uuid4().hex[:8].translate(str.maketrans("0123456789", "GHIJKLMNOP"))


async def _kpi_measured_at(api: ApiClient, monkeypatch: pytest.MonkeyPatch,
                           at: datetime | None) -> str:  # fmt: skip
    from app.modules.execution.services import kpi_service

    k = await make(api, "/kpis", {"code": _code(), "name": "x", "unit": "x", "target": 10,
                                  "owner_id": str(uuid.uuid4()),
                                  "period_type": "MONTH"})  # fmt: skip
    if at is not None:
        monkeypatch.setattr(kpi_service, "now_utc", lambda: at)
        r = await api.call("POST", f"/kpis/{k['id']}/measurements", "CEO",
                           json={"period_key": "2037-05", "actual_value": 10})  # fmt: skip
        assert r.status_code == 201, r.text
    return str(k["id"])


async def test_load_str01_on_seeded_rows(
    api: ApiClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    on = await _kpi_measured_at(api, monkeypatch, datetime(2037, 6, 3, 3, tzinfo=UTC))
    late = await _kpi_measured_at(api, monkeypatch, datetime(2037, 6, 8, 3, tzinfo=UTC))
    never = await _kpi_measured_at(api, monkeypatch, None)
    o = await make(api, "/objectives", {"title": uniq("O"), "owner_id": str(uuid.uuid4()),
                                        "period_key": "2037-Q2"})  # fmt: skip
    ids = []
    for n in range(2):
        kr = await make(api, f"/objectives/{o['id']}/key-results", {
            "title": f"kr{n}", "baseline": 0, "target": 1, "unit": "x",
            "owner_id": str(uuid.uuid4()), "weight_pct": 50})  # fmt: skip
        ids.append(kr["id"])
    assert (await patch(api, f"/objectives/{o['id']}", 1, status="active")).status_code == 200
    rows = (
        (
            await db_session.execute(
                select(KeyResult)
                .where(KeyResult.id.in_([uuid.UUID(i) for i in ids]))
                .order_by(KeyResult.title)
            )
        )
        .scalars()
        .all()
    )
    rows[0].last_checked_in_at = datetime(2037, 6, 13, 3, tzinfo=UTC)  # 7 days → on time
    rows[1].last_checked_in_at = datetime(2037, 6, 12, 3, tzinfo=UTC)  # 8 days → late
    await db_session.flush()
    mine = {uuid.UUID(x) for x in (on, late, never)}
    real_where = metrics.KpiRepository.where

    async def only_mine(self: Any, *clauses: Any, **kw: Any) -> Any:
        return [k for k in await real_where(self, *clauses, **kw) if k.id in mine]

    async def only_obj(db: AsyncSession, day: date) -> list[Any]:
        from app.modules.execution.repositories import ObjectiveRepository

        return [await ObjectiveRepository(db).get(uuid.UUID(o["id"]))]

    monkeypatch.setattr(metrics.KpiRepository, "where", only_mine)
    monkeypatch.setattr(metrics, "current_objectives", only_obj)
    r = await metrics.load_str01(db_session, AS_OF, "2037-06")
    assert r.value == 40.0  # (1 KPI + 1 KR) / (3 KPI-periods + 2 KRs)
    assert {x.id for x in r.records} == {late, never, str(rows[1].id)}


async def test_str01_alert_below_threshold(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Below 60 → critical alert on METRIC-STR-01 through the platform metric store."""

    async def fake(db: AsyncSession, as_of: date, key: str) -> Any:
        return str01([(uuid.uuid4(), "2037-05")], set(), [_kr(1)], as_of, 7, key)

    monkeypatch.setattr(metrics, "load_str01", fake)
    await seed_catalog(db_session)  # dev DB seeded before T-630 → upsert METRIC-STR-01
    stats = await MetricStore(db_session).recompute(AS_OF, {"execution"})
    assert stats["failed_providers"] == 0
    q = select(Alert).join(Metric, Alert.metric_id == Metric.id).where(
        Metric.code == "METRIC-STR-01", Alert.period_key == "2037-06")  # fmt: skip
    alert = (await db_session.execute(q)).scalars().all()
    assert len(alert) == 1 and alert[0].severity == "CRITICAL"

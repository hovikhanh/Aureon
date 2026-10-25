"""T-627 — KPITarget effective-dated, measurement history, KPIEvaluation, KRMeasurement
(05 §2.6, R-DEC-51..53): TC-M14-02, TC-M14-07, TC-M14-08, TC-M14-09.

Time is pinned through `kpi_service.now_utc` so "measured before / after a target change" is
deterministic; periods live in 2037 to stay clear of the demo seed.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.services import kpi_service
from tests.conftest import ApiClient
from tests.integration.execution.helpers import (
    as_user,
    audit_actions,
    make,
    outbox_for,
    patch,
    uniq,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    def set_(iso: str) -> None:
        at = datetime.fromisoformat(iso).replace(tzinfo=UTC)
        monkeypatch.setattr(kpi_service, "now_utc", lambda: at)

    return set_


async def _kpi(api: ApiClient, **kw: Any) -> dict[str, Any]:
    return await make(api, "/kpis", {
        "code": "KPI-" + uuid.uuid4().hex[:8].translate(str.maketrans("0123456789", "GHIJKLMNOP")),
        "name": "Doanh thu", "unit": "tỷ", "target": 100,
        "owner_id": str(uuid.uuid4()), **kw})  # fmt: skip


async def _measure(api: ApiClient, kid: str, period: str, value: float) -> Any:
    return await api.call("POST", f"/kpis/{kid}/measurements", "CEO",
                          json={"period_key": period, "actual_value": value})  # fmt: skip


async def _evals(api: ApiClient, kid: str, **params: str) -> list[dict[str, Any]]:
    r = await api.call("GET", f"/kpis/{kid}/evaluations", "CEO", params=params)
    assert r.status_code == 200, r.text
    return list(r.json()["data"])


async def test_migration_0017_shape(db_session: AsyncSession) -> None:
    """TC-M14-02: columns + partial UQ (current version) + tenant_id on the logs."""
    cols = await db_session.execute(text(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = 'execution' AND table_name IN "
        "('kpi_targets','kpi_measurements','check_ins','kr_measurements','kpi_evaluations',"
        "'key_results')"))  # fmt: skip
    have = {(t, c) for t, c in cols}
    for need in [("kpi_targets", "valid_from"), ("kpi_targets", "valid_to"),
                 ("kpi_measurements", "tenant_id"), ("kpi_measurements", "check_in_id"),
                 ("check_ins", "tenant_id"), ("kr_measurements", "previous_progress_pct"),
                 ("kpi_evaluations", "previous_band"), ("key_results", "at_risk_reasons"),
                 ("key_results", "last_checked_in_at")]:  # fmt: skip
        assert need in have, need
    idx = await db_session.execute(text(
        "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'execution' AND "
        "tablename IN ('kpi_targets','kpi_measurements')"))  # fmt: skip
    defs = dict(idx.all())
    assert "valid_to IS NULL" in defs["uq_kpi_targets_kpi_id_period_key"]
    assert not any("UNIQUE" in d for n, d in defs.items() if n.startswith("ix_kpi_measurements"))
    # backfill: one evaluation per (KPI, period) that has measurements
    gap = await db_session.execute(text(
        "SELECT count(*) FROM (SELECT DISTINCT kpi_id, period_key FROM execution.kpi_measurements"
        ") m LEFT JOIN execution.kpi_evaluations e USING (kpi_id, period_key) "
        "WHERE e.id IS NULL"))  # fmt: skip
    assert gap.scalar() == 0


async def test_target_effective_dated(
    api: ApiClient, db_session: AsyncSession, clock: Callable[[str], None]
) -> None:
    """TC-M14-07: mid-period change closes + opens, re-scores; 422 / 409 rules; EMP denied."""
    k = await _kpi(api)
    kid, turl = k["id"], f"/kpis/{k['id']}/targets"
    clock("2037-03-05T03:00:00")
    assert (await _measure(api, kid, "2037-03", 80)).status_code == 201  # default target 100
    t0 = (await api.call("GET", turl, "CEO")).json()["data"]
    assert [(t["target"], t["valid_from"], t["valid_to"]) for t in t0] == [
        (100, "2037-03-01", None)]  # fmt: skip
    assert (await _evals(api, kid))[0]["band"] == "BELOW"
    new = await api.call("POST", turl, "CEO", json={
        "period_key": "2037-03", "target": 80, "valid_from": "2037-03-15",
        "reason": "điều chỉnh"})  # fmt: skip
    assert new.status_code == 201, new.text
    assert new.json()["data"]["valid_to"] is None and new.json()["data"]["reason"] == "điều chỉnh"
    hist = (await api.call("GET", turl, "CEO", params={"period_key": "2037-03"})).json()["data"]
    assert [(t["target"], t["valid_to"]) for t in hist] == [(100, "2037-03-15"), (80, None)]
    as_of = await api.call("GET", turl, "CEO", params={"as_of": "2037-03-10"})
    assert [t["target"] for t in as_of.json()["data"]] == [100]
    # the period's latest measurement (5/3) was taken under the old target → still BELOW
    ev = (await _evals(api, kid))[0]
    assert ev["target"] == 100 and ev["band"] == "BELOW"
    clock("2037-03-20T03:00:00")  # after the change → new target 80 → 100 %
    m = (await _measure(api, kid, "2037-03", 80)).json()["data"]
    assert m["kpi_target_id"] == new.json()["data"]["id"] and m["evaluation_band"] == "MEETS"
    ev = (await _evals(api, kid))[0]
    assert (ev["target"], ev["band"], ev["previous_band"]) == (80, "MEETS", "BELOW")
    assert ev["measurement_id"] == m["id"]
    late = await api.call("POST", turl, "CEO", json={
        "period_key": "2037-03", "target": 90, "valid_from": "2037-03-10"})  # fmt: skip
    assert late.status_code == 422  # ≤ current valid_from
    out = await api.call("POST", turl, "CEO", json={
        "period_key": "2037-03", "target": 90, "valid_from": "2037-04-02"})  # fmt: skip
    assert out.status_code == 422 and out.json()["error"]["details"]["field"] == "valid_from"
    bad = await api.call("POST", turl, "CEO", json={"period_key": "2037-Q1", "target": 9})
    assert bad.status_code == 422  # period_key ≠ period_type MONTH
    emp = await as_user(api, "POST", turl, "EMPLOYEE", uuid.UUID(k["owner_id"]), json={
        "period_key": "2037-03", "target": 90, "valid_from": "2037-03-25"})  # fmt: skip
    assert emp.status_code == 403
    assert "execution.kpi_target_set" in await audit_actions(db_session, new.json()["data"]["id"])
    await db_session.execute(
        text("UPDATE execution.kpi_targets SET locked_at = now() WHERE kpi_id = :k"), {"k": kid}
    )
    locked = await api.call("POST", turl, "CEO", json={
        "period_key": "2037-03", "target": 90, "valid_from": "2037-03-25"})  # fmt: skip
    assert locked.status_code == 409
    assert locked.json()["error"]["details"]["reason"] == "period_locked"
    assert (await _measure(api, kid, "2037-03", 1)).status_code == 409
    assert (await patch(api, f"/kpis/{kid}", 1, name="x")).status_code == 200  # KPI not locked


async def test_one_current_target_per_period(api: ApiClient, db_session: AsyncSession) -> None:
    """TC-M14-07 concurrency: the partial UQ lets only one current version exist (the loser of
    two concurrent EP-KPI-09 calls fails), on top of the KPI row lock."""
    from sqlalchemy.exc import IntegrityError

    k = await _kpi(api)
    sql = text(
        "INSERT INTO execution.kpi_targets (id, tenant_id, kpi_id, period_key, target, valid_from,"
        " band_thresholds, score_cap_pct, source) SELECT gen_random_uuid(), tenant_id, id,"
        " '2037-05', 1, '2037-05-01', '{}', 150, 'MANUAL' FROM execution.kpis"
        " WHERE id = :k")  # fmt: skip
    await db_session.execute(sql, {"k": k["id"]})
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await db_session.execute(sql, {"k": k["id"]})


async def test_measurement_history_and_evaluation(
    api: ApiClient, db_session: AsyncSession, clock: Callable[[str], None]
) -> None:
    """TC-M14-08: one row per measurement, evaluation = latest; LIB direction; replay; undo."""
    k = await _kpi(api, direction="LOWER_IS_BETTER", target=10, unit="ngày")
    kid = k["id"]
    clock("2037-01-31T03:00:00")
    assert (await _measure(api, kid, "2037-01", 20)).json()["data"]["evaluation_band"] == "CRITICAL"
    clock("2037-02-20T03:00:00")  # late for 2037-01 (grace 5 days)
    second = (await _measure(api, kid, "2037-01", 10)).json()["data"]
    assert second["achievement_pct"] == 100
    ev = (await _evals(api, kid))[0]
    assert (ev["actual_value"], ev["band"], ev["previous_band"]) == (10, "MEETS", "CRITICAL")
    assert ev["gap_value"] == 0 and ev["measured_on_time"] is True  # first measure on time
    clock("2037-03-10T03:00:00")
    await _measure(api, kid, "2037-02", 5)  # LIB: 10/5 = 200 → cap 150
    evs = await _evals(api, kid)
    assert [e["period_key"] for e in evs] == ["2037-01", "2037-02"]
    assert evs[1]["achievement_pct"] == 150 and evs[1]["gap_value"] == -5
    assert evs[1]["measured_on_time"] is False  # first measured 10/3 > 1/3 + 5
    assert [e["period_key"] for e in await _evals(api, kid, from_period="2037-02")] == ["2037-02"]
    lst = await api.call(
        "GET", f"/kpis/{kid}/measurements", "CEO", params={"period_key": "2037-01"}
    )
    assert lst.json()["meta"]["pagination"]["total"] == 2
    got = (await api.call("GET", f"/kpis/{kid}", "CEO")).json()["data"]["latest_evaluation"]
    assert got["period_key"] == "2037-02" and got["band"] == "EXCEEDS"
    crit = await api.call(
        "GET", "/kpis", "CEO", params={"band": "EXCEEDS", "owner_id": k["owner_id"]}
    )
    assert [x["id"] for x in crit.json()["data"]] == [kid]
    none = await api.call(
        "GET", "/kpis", "CEO", params={"band": "BELOW", "owner_id": k["owner_id"]}
    )
    assert none.json()["data"] == []
    # idempotent replay → same row, no second measurement
    h = api.headers("CEO", idem=True)
    body = {"period_key": "2037-02", "actual_value": 6}
    a = await api.http.post(f"/api/v1/kpis/{kid}/measurements", json=body, headers=h)
    b = await api.http.post(f"/api/v1/kpis/{kid}/measurements", json=body, headers=h)
    assert a.json()["data"]["id"] == b.json()["data"]["id"]
    feb = await api.call(
        "GET", f"/kpis/{kid}/measurements", "CEO", params={"period_key": "2037-02"}
    )
    assert feb.json()["meta"]["pagination"]["total"] == 2
    # undo (Action Registry v2 service): delete latest → evaluation back to the previous row
    async with db_session.begin_nested():
        await kpi_service.KpiService(db_session).delete_measurement(
            uuid.UUID(a.json()["data"]["id"]))  # fmt: skip
    assert (await _evals(api, kid, from_period="2037-02"))[0]["actual_value"] == 5
    first_feb = next(x["id"] for x in feb.json()["data"] if x["id"] != a.json()["data"]["id"])
    await kpi_service.KpiService(db_session).delete_measurement(uuid.UUID(first_feb))
    assert await _evals(api, kid, from_period="2037-02") == []
    events = [e for e, _ in await outbox_for(db_session, kid)]
    assert events.count("execution.kpi_measured") == 4


async def _active_objective(api: ApiClient, owner: uuid.UUID) -> tuple[str, str]:
    o = await make(api, "/objectives", {"title": uniq("O"), "owner_id": str(owner),
                                        "period_key": "2037-Q2"})  # fmt: skip
    kr = await make(api, f"/objectives/{o['id']}/key-results", {
        "title": "Pipeline", "baseline": 0, "target": 100, "unit": "%",
        "owner_id": str(owner)})  # fmt: skip
    await make(api, f"/objectives/{o['id']}/key-results", {
        "title": "Khác", "baseline": 0, "target": 1, "unit": "x", "owner_id": str(owner),
        "weight_pct": 0})  # fmt: skip
    assert (await patch(api, f"/objectives/{o['id']}", 1, status="active")).status_code == 200
    return o["id"], kr["id"]


async def test_kr_check_in_writes_measurement(api: ApiClient, db_session: AsyncSession) -> None:
    """TC-M14-09: CheckIn + KRMeasurement (previous_progress_pct) + KR + objective; undo."""
    owner = uuid.uuid4()
    oid, krid = await _active_objective(api, owner)
    url = f"/key-results/{krid}/check-ins"
    first = await as_user(api, "POST", url, "EMPLOYEE", owner,
                          json={"value": 60, "confidence": "HIGH"})  # fmt: skip
    assert first.status_code == 201, first.text
    fd = first.json()["data"]
    assert fd["kr_measurement"] == {"value": 60, "progress_pct": 60, "previous_progress_pct": None}
    assert fd["target_title"] == "Pipeline" and fd["target_type"] == "key_result"
    second = await api.call("POST", url, "CEO", json={"value": 50, "confidence": "LOW"})
    assert second.status_code == 201, second.text
    sd = second.json()["data"]
    assert sd["kr_measurement"]["previous_progress_pct"] == 60
    kr = (await api.call("GET", f"/key-results/{krid}", "CEO")).json()["data"]
    assert (kr["current_value"], kr["confidence"]) == (50, "LOW")
    assert kr["last_checked_in_at"] is not None
    assert (await api.call("GET", f"/objectives/{oid}", "CEO")).json()["data"]["progress_pct"] == 50
    ms = (await api.call("GET", f"/key-results/{krid}/measurements", "CEO")).json()["data"]
    assert [m["value"] for m in ms] == [50, 60]  # measured_at desc
    assert ms[0]["check_in_id"] == sd["id"] and ms[0]["period_key"] == "2037-Q2"
    lst = (await api.call("GET", url, "CEO")).json()["data"]
    assert lst[0]["kr_measurement"]["value"] == 50
    stranger = await as_user(api, "POST", url, "EMPLOYEE", uuid.uuid4(),
                             json={"value": 1, "confidence": "LOW"})  # fmt: skip
    assert stranger.status_code == 403
    # undo the last check-in (Action Registry v2, M1.5) → back to the first measurement
    await kpi_service.KpiService(db_session).delete_check_in(uuid.UUID(sd["id"]))
    kr = (await api.call("GET", f"/key-results/{krid}", "CEO")).json()["data"]
    assert (kr["current_value"], kr["confidence"]) == (60, "HIGH")
    assert (await api.call("GET", f"/objectives/{oid}", "CEO")).json()["data"]["progress_pct"] == 60
    ms = (await api.call("GET", f"/key-results/{krid}/measurements", "CEO")).json()["data"]
    assert [m["value"] for m in ms] == [60]


async def test_kpi_check_in_links_measurement(api: ApiClient, db_session: AsyncSession) -> None:
    """TC-M14-09: EP-PRF-04 measurement of the current period with `check_in_id`; a failing
    check-in (locked period) leaves no row / event behind; undo removes both rows."""
    k = await _kpi(api)
    ck = await api.call("POST", f"/kpis/{k['id']}/check-ins", "CEO",
                        json={"value": 90, "confidence": "MEDIUM", "note": "ổn"})  # fmt: skip
    assert ck.status_code == 201, ck.text
    cid = ck.json()["data"]["id"]
    assert ck.json()["data"]["target_title"] == "Doanh thu"
    ms = (await api.call("GET", f"/kpis/{k['id']}/measurements", "CEO")).json()["data"]
    assert ms[0]["check_in_id"] == cid and ms[0]["note"] == "ổn"
    await db_session.execute(
        text("UPDATE execution.kpi_targets SET locked_at = now() WHERE kpi_id = :k"), {"k": k["id"]}
    )
    locked = await api.call("POST", f"/kpis/{k['id']}/check-ins", "CEO",
                            json={"value": 1, "confidence": "LOW"})  # fmt: skip
    assert locked.status_code == 409
    n = await db_session.execute(
        text("SELECT count(*) FROM execution.check_ins WHERE kpi_id = :k"), {"k": k["id"]}
    )
    assert n.scalar() == 1
    assert len(await outbox_for(db_session, k["id"])) == 1
    await db_session.execute(
        text("UPDATE execution.kpi_targets SET locked_at = NULL WHERE kpi_id = :k"), {"k": k["id"]}
    )
    await kpi_service.KpiService(db_session).delete_check_in(uuid.UUID(cid))
    left = await db_session.execute(
        text(
            "SELECT (SELECT count(*) FROM execution.check_ins WHERE kpi_id = :k) + "
            "(SELECT count(*) FROM execution.kpi_measurements WHERE kpi_id = :k) + "
            "(SELECT count(*) FROM execution.kpi_evaluations WHERE kpi_id = :k)"
        ),
        {"k": k["id"]},
    )
    assert left.scalar() == 0

"""T-629 — goal events (10 §9.2, R-DEC-55/56/59): TC-M14-10, TC-M14-11, TC-M14-12.

Uses the demo users of the dev DB (`employee@` EMP, `manager@` MGR of the same department);
consumers are invoked in the rolled-back test session with the envelope from the outbox row
(the dedupe on `processed_events` itself is covered through `consume()` with `factory`).
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.events.bus import REGISTRY
from app.core.events.consumer import Outcome, consume
from app.core.events.envelope import OUTBOX, EventEnvelope
from app.core.events.outbox import publish_in_tx
from app.core.pii import scan_payload
from app.modules.auth.models import User
from app.modules.execution.events import consumers as exec_consumers
from app.modules.execution.models import KeyResult
from app.modules.execution.services import at_risk
from app.modules.execution.services.at_risk import AtRiskService, assess, checkin_reminder
from app.modules.platform.events import consumers as platform_consumers
from app.modules.platform.models import Notification
from tests.conftest import ApiClient
from tests.integration.execution.helpers import as_user, make, patch, uniq

pytestmark = pytest.mark.integration

GOAL = ("execution.kpi_below_threshold", "execution.okr_checked_in", "execution.okr_at_risk")


def _code() -> str:
    return "K-" + uuid.uuid4().hex[:8].translate(str.maketrans("0123456789", "GHIJKLMNOP"))


async def _user(db: AsyncSession, email: str) -> User:
    return (await db.execute(select(User).where(User.email == email))).scalar_one()


async def _envelopes(db: AsyncSession, aggregate_id: str, event_type: str) -> list[EventEnvelope]:
    rows = await db.execute(select(OUTBOX).where(
        OUTBOX.c.aggregate_id == uuid.UUID(aggregate_id), OUTBOX.c.event_type == event_type,
    ).order_by(OUTBOX.c.occurred_at))  # fmt: skip
    return [EventEnvelope(event_id=r.id, event_type=r.event_type, occurred_at=r.occurred_at,
                          version=r.version, tenant_id=r.tenant_id, producer="execution",
                          payload=r.payload) for r in rows]  # fmt: skip


async def _alerts(db: AsyncSession, ref_id: str) -> list[tuple[uuid.UUID, str, str | None]]:
    rows = await db.execute(select(Notification.recipient_id, Notification.title,
                                   Notification.link).where(
        Notification.ref_id == uuid.UUID(ref_id), Notification.kind == "alert"))  # fmt: skip
    return [tuple(r) for r in rows.all()]  # type: ignore[misc]


def test_registry_and_routing() -> None:
    from app.core.events.registry import EXTENSION_EVENT_TYPES

    assert set(GOAL) <= EXTENSION_EVENT_TYPES
    for e in ("execution.kpi_measured", "execution.okr_checked_in"):
        assert platform_consumers.AFFECTS[e] == {"execution"}
        assert REGISTRY.consumers_for(e) == ["platform.on_goal_event"]
    for e in ("execution.kpi_below_threshold", "execution.okr_at_risk"):
        assert REGISTRY.consumers_for(e) == ["execution.on_goal_alert"]
    assert "execution.kpi_measured" not in platform_consumers._group("execution.")


async def test_kpi_band_transitions_and_alert(api: ApiClient, db_session: AsyncSession) -> None:
    """TC-M14-11: into BELOW/CRITICAL → event; staying low → none; NEAR+ then down → again;
    consumer: owner + MGR alert, dedupe `(kpi, period, band)`, replay does not duplicate."""
    emp = await _user(db_session, "employee@abc.demo")
    mgr = await _user(db_session, "manager@abc.demo")
    k = await make(api, "/kpis", {"code": _code(), "name": "DT", "unit": "tỷ", "target": 100,
                                  "owner_id": str(emp.employee_id),
                                  "department_id": str(emp.department_id)})  # fmt: skip
    url = f"/kpis/{k['id']}/measurements"
    bands = []
    for v in (60, 50, 75, 95, 80, 40):  # CRIT, CRIT, BELOW(better), NEAR, BELOW, CRIT
        r = await api.call("POST", url, "CEO", json={"period_key": "2037-06", "actual_value": v})
        bands.append(r.json()["data"]["evaluation_band"])
    assert bands == ["CRITICAL", "CRITICAL", "BELOW", "NEAR", "BELOW", "CRITICAL"]
    evs = await _envelopes(db_session, k["id"], "execution.kpi_below_threshold")
    assert [(e.payload["band"], e.payload["previous_band"]) for e in evs] == [
        ("CRITICAL", None), ("BELOW", "NEAR"), ("CRITICAL", "BELOW")]  # fmt: skip
    p = evs[0].payload
    assert set(p) == {
        "kpi_id",
        "kpi_code",
        "period_key",
        "evaluation_id",
        "achievement_pct",
        "band",
        "previous_band",
        "gap_value",
        "owner_id",
        "department_id",
    }
    assert p["gap_value"] == "40.000000" and not scan_payload(p)
    for e in (evs[0], evs[0], evs[1], evs[2]):  # first event twice (re-delivery)
        await exec_consumers.on_goal_alert(db_session, e)
    notes = await _alerts(db_session, k["id"])
    assert {n[0] for n in notes} == {emp.id, mgr.id}
    # 3 events but CRITICAL re-entered in the same period is deduped `(kpi, period, band)`
    assert len(notes) == 4
    assert {n[2] for n in notes} == {f"/goals/kpis/{k['id']}"}
    measured = await _envelopes(db_session, k["id"], "execution.kpi_measured")
    assert len(measured) == 6 and not scan_payload(measured[0].payload)


async def test_target_change_can_raise_alert(
    api: ApiClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """EP-KPI-09 re-scores the period; moving it into a low band publishes too."""
    from app.modules.execution.services import kpi_service

    at = datetime(2037, 1, 5, 3, tzinfo=UTC)
    monkeypatch.setattr(kpi_service, "now_utc", lambda: at)
    k = await make(api, "/kpis", {"code": _code(), "name": "DT", "unit": "tỷ", "target": 10,
                                  "owner_id": str(uuid.uuid4())})  # fmt: skip
    m = await api.call("POST", f"/kpis/{k['id']}/measurements", "CEO",
                       json={"period_key": "2037-01", "actual_value": 10})  # fmt: skip
    assert m.json()["data"]["evaluation_band"] == "MEETS"
    assert await _envelopes(db_session, k["id"], "execution.kpi_below_threshold") == []
    t = await api.call("POST", f"/kpis/{k['id']}/targets", "CEO",
                       json={"period_key": "2037-01", "target": 50,
                             "valid_from": "2037-01-03"})  # fmt: skip
    assert t.status_code == 201, t.text
    [e] = await _envelopes(db_session, k["id"], "execution.kpi_below_threshold")
    assert (e.payload["band"], e.payload["previous_band"]) == ("CRITICAL", "MEETS")


async def _active_kr(api: ApiClient, owner: uuid.UUID, period: str, **kr: Any) -> tuple[str, str]:
    o = await make(api, "/objectives", {"title": uniq("O"), "owner_id": str(owner),
                                        "period_key": period})  # fmt: skip
    k = await make(api, f"/objectives/{o['id']}/key-results", {
        "title": "Pipeline", "baseline": 0, "target": 100, "unit": "%", "owner_id": str(owner),
        **kr})  # fmt: skip
    await make(api, f"/objectives/{o['id']}/key-results", {
        "title": "Khác", "baseline": 0, "target": 1, "unit": "x", "owner_id": str(uuid.uuid4()),
        "weight_pct": 0})  # fmt: skip
    act = await patch(api, f"/objectives/{o['id']}", 1, status="active")
    assert act.status_code == 200, act.text
    return o["id"], k["id"]


async def test_okr_checked_in_payload_and_rollback(
    api: ApiClient, db_session: AsyncSession
) -> None:
    """TC-M14-10: KR + KPI check-in publish `okr_checked_in` in the same tx; a failed request
    leaves no outbox row; payload = 10 §9.2, no PII."""
    from app.modules.execution.services.base import today
    from app.modules.execution.services.kpi_rules import period_key_for

    owner = uuid.uuid4()
    oid, krid = await _active_kr(api, owner, period_key_for("QUARTER", today()))
    url = f"/key-results/{krid}/check-ins"
    for v in (40, 30):
        r = await as_user(api, "POST", url, "EMPLOYEE", owner,
                          json={"value": v, "confidence": "HIGH"})  # fmt: skip
        assert r.status_code == 201, r.text
    cid = r.json()["data"]["id"]
    [e] = await _envelopes(db_session, cid, "execution.okr_checked_in")
    p = e.payload
    assert set(p) == {"check_in_id", "target_type", "target_id", "objective_id", "period_key",
                      "value", "confidence", "progress_pct", "previous_progress_pct",
                      "user_id", "department_id", "on_time"}  # fmt: skip
    assert (p["target_type"], p["target_id"], p["objective_id"]) == ("kr", krid, oid)
    assert (p["progress_pct"], p["previous_progress_pct"], p["on_time"]) == (
        "30.0000", "40.0000", True)  # fmt: skip
    assert not scan_payload(p)
    bad = await as_user(api, "POST", url, "EMPLOYEE", uuid.uuid4(),
                        json={"value": 1, "confidence": "LOW"})  # fmt: skip
    assert bad.status_code == 403
    rows = await db_session.execute(select(OUTBOX.c.id).where(
        OUTBOX.c.event_type == "execution.okr_checked_in",
        OUTBOX.c.payload["target_id"].astext == krid))  # fmt: skip
    assert len(rows.all()) == 2
    k = await make(api, "/kpis", {"code": _code(), "name": "x", "unit": "x", "target": 5,
                                  "owner_id": str(owner)})  # fmt: skip
    ck = await api.call("POST", f"/kpis/{k['id']}/check-ins", "CEO",
                        json={"value": 5, "confidence": "HIGH"})  # fmt: skip
    [kp] = await _envelopes(db_session, ck.json()["data"]["id"], "execution.okr_checked_in")
    assert kp.payload["target_type"] == "kpi" and kp.payload["objective_id"] is None
    assert kp.payload["on_time"] is True and kp.payload["progress_pct"] is None


async def test_on_goal_event_dedupes(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    """TC-M14-10: `platform.on_goal_event` handles one `event_id` once (processed_events)."""
    calls: list[str] = []

    async def fake(_s: AsyncSession, event: Any) -> None:
        calls.append(event.event_type)

    monkeypatch.setattr(platform_consumers, "recompute_for", fake)
    async with factory() as s:
        env = await publish_in_tx(
            s, event_type="execution.okr_checked_in", producer="execution",
            aggregate_schema="execution", aggregate_table="test_events",
            aggregate_id=uuid.uuid4(), payload={"check_in_id": str(uuid.uuid4())},
        )  # fmt: skip
        await s.commit()
    msg = env.model_dump(mode="json")
    first = await consume(factory, "platform.on_goal_event", msg)
    again = await consume(factory, "platform.on_goal_event", msg)
    assert (first.outcome, again.outcome) == (Outcome.DONE, Outcome.DUPLICATE)
    assert calls == ["execution.okr_checked_in"]


def _kr(current: str, confidence: str = "HIGH") -> KeyResult:
    return KeyResult(baseline=Decimal(0), target=Decimal(100), current_value=Decimal(current),
                     confidence=confidence)  # fmt: skip


Q4_END = date(2037, 12, 31)  # last day of 2037-Q4


@pytest.mark.parametrize("days_left", [20, 21, 22])
@pytest.mark.parametrize(("current", "previous", "confidence", "reasons"), [
    ("90", "80", "HIGH", ()),  # ahead, rising, confident
    ("90", "95", "HIGH", ("declining",)),
    ("90", None, "LOW", ("low_confidence",)),
    ("5", "5", "MEDIUM", ("behind_plan",)),
    ("5", "10", "LOW", ("declining", "low_confidence", "behind_plan")),
])  # fmt: skip
def test_assess_decision_table(
    days_left: int, current: str, previous: str | None, confidence: str,
    reasons: tuple[str, ...],
) -> None:  # fmt: skip
    """TC-M14-12: reasons × `days_to_period_end` 20/21/22 (R-DEC-55)."""
    day = Q4_END - timedelta(days=days_left)
    a = assess(_kr(current, confidence), "2037-Q4", day,
               None if previous is None else Decimal(previous), 0.7)  # fmt: skip
    assert a.reasons == reasons and a.days_to_period_end == days_left
    assert a.at_risk is (bool(reasons) and days_left >= 21)


def test_assess_behind_plan_threshold() -> None:
    day = date(2037, 11, 15)  # 45 of 92 days → expected 48.9130 %, 0.7 × = 34.24 %
    assert assess(_kr("34"), "2037-Q4", day, None, 0.7).reasons == ("behind_plan",)
    assert assess(_kr("35"), "2037-Q4", day, None, 0.7).reasons == ()
    assert assess(_kr("35"), "2037-Q4", day, None, 0.7).expected_progress_pct == Decimal(
        "48.9130")  # fmt: skip


async def test_at_risk_transition_job_and_weekly_alert(
    api: ApiClient, db_session: AsyncSession
) -> None:
    """TC-M14-12: event only on false → true; daily job idempotent; `alert` dedupe ISO week."""
    emp = await _user(db_session, "employee@abc.demo")
    mgr = await _user(db_session, "manager@abc.demo")
    oid, krid = await _active_kr(api, emp.employee_id, "2037-Q4")
    kr = (await db_session.execute(select(KeyResult).where(
        KeyResult.id == uuid.UUID(krid)))).scalar_one()  # fmt: skip
    svc = AtRiskService(db_session)
    from app.modules.execution.repositories import ObjectiveRepository

    obj = await ObjectiveRepository(db_session).get(uuid.UUID(oid))
    assert obj is not None
    obj.department_id = emp.department_id
    early = date(2037, 10, 20)  # expected 20.65 % → 0 % progress is behind plan
    assert (await svc.daily(early)) >= 1 and kr.at_risk
    assert kr.at_risk_reasons == ["behind_plan"] and kr.at_risk_since is not None
    assert await svc.daily(early) == 0  # idempotent: still at risk → no new event
    assert await svc.daily(date(2037, 10, 21)) == 0
    [e] = await _envelopes(db_session, krid, "execution.okr_at_risk")
    assert e.payload["reasons"] == ["behind_plan"] and e.payload["days_to_period_end"] == 72
    assert set(e.payload) == {
        "key_result_id",
        "objective_id",
        "period_key",
        "progress_pct",
        "previous_progress_pct",
        "expected_progress_pct",
        "confidence",
        "reasons",
        "days_to_period_end",
        "owner_id",
        "department_id",
    }
    assert not scan_payload(e.payload)
    # recovers → flag cleared, no event; falls again → new event
    kr.current_value = Decimal(60)
    await svc.daily(early)
    assert not kr.at_risk and kr.at_risk_reasons == [] and kr.at_risk_since is None
    kr.current_value = Decimal(0)
    assert await svc.daily(date(2037, 10, 22)) == 1
    evs = await _envelopes(db_session, krid, "execution.okr_at_risk")
    assert len(evs) == 2
    for ev in (evs[0], evs[0], evs[1]):  # same ISO week → one alert per recipient
        await exec_consumers.on_goal_alert(db_session, ev)
    notes = await _alerts(db_session, krid)
    assert {n[0] for n in notes} == {emp.id, mgr.id} and len(notes) == 2
    assert {n[2] for n in notes} == {f"/goals/objectives/{oid}?kr={krid}"}
    next_week = evs[1].model_copy(
        update={"event_id": uuid.uuid4(), "occurred_at": evs[1].occurred_at + timedelta(days=7)}
    )
    await exec_consumers.on_goal_alert(db_session, next_week)
    assert len(await _alerts(db_session, krid)) == 4
    # < 21 days to the end: flag only, never an event
    kr.current_value, kr.at_risk = Decimal(0), False
    await svc.daily(date(2037, 12, 20))
    assert (
        kr.at_risk is False
        and len(await _envelopes(db_session, krid, "execution.okr_at_risk")) == 2
    )


async def test_weekly_checkin_reminder_idempotent(
    api: ApiClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Beat `execution.checkin_reminder`: one `reminder` per user and ISO week, no event."""
    from app.modules.execution.services.base import today
    from app.modules.execution.services.kpi_rules import period_key_for

    emp = await _user(db_session, "employee@abc.demo")
    oid, _ = await _active_kr(api, emp.employee_id, period_key_for("QUARTER", today()))
    friday = today()  # dedupe compares `created_at` (wall clock) with the ISO week start
    monkeypatch.setattr(at_risk, "current_objectives", _only_ids({uuid.UUID(oid)}))
    before = await _outbox_count(db_session)
    assert await checkin_reminder(db_session, friday) >= 1
    assert await checkin_reminder(db_session, friday) == 0
    rows = (await db_session.execute(select(Notification.title).where(
        Notification.recipient_id == emp.id, Notification.kind == "reminder",
        Notification.link == "/goals/check-ins"))).scalars().all()  # fmt: skip
    assert (
        len(rows) == 1 and rows[0].startswith("Check-in tuần: ") and rows[0].endswith(" KR của bạn")
    )
    assert await _outbox_count(db_session) == before


def _only_ids(ids: set[uuid.UUID]) -> Any:
    real = at_risk.current_objectives

    async def run(db: AsyncSession, day: date) -> list[Any]:
        return [o for o in await real(db, day) if o.id in ids]

    return run


async def _outbox_count(db: AsyncSession) -> int:
    from sqlalchemy import func

    return int((await db.execute(select(func.count()).select_from(OUTBOX))).scalar_one())

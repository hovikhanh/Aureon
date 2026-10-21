"""TC-RSK-008 (unit) — METRIC-RSK-01..05 rules on synthetic rows (03 §2.5, DEC-143)."""

import uuid
from datetime import UTC, date, datetime, timedelta

from app.modules.risk.models import Mitigation, Risk
from app.modules.risk.services.analytics import compute_readings, rsk04_status

AS_OF = date(2037, 6, 15)


def risk(li: int, im: int, sev: str, *, status: str = "assessed", owner: bool = True,
         age_days: int = 1) -> Risk:  # fmt: skip
    return Risk(
        id=uuid.uuid4(), likelihood=li, impact=im, severity=sev, status=status,
        owner_id=uuid.uuid4() if owner else None,
        identified_at=datetime(2037, 6, 15, tzinfo=UTC) - timedelta(days=age_days),
    )  # fmt: skip


def mit(r: Risk, status: str, due: date) -> Mitigation:
    return Mitigation(id=uuid.uuid4(), risk_id=r.id, status=status, due_date=due)


def by_code(risks: list[Risk], mits: list[Mitigation]) -> dict[str, tuple[object, object]]:
    out = compute_readings(risks, mits, AS_OF).items
    assert [m.code for m in out] == [f"METRIC-RSK-0{i}" for i in range(1, 6)]
    assert all(m.period_key == "2037-06" and m.scope_type == "company" for m in out)
    return {m.code[-2:]: (m.value, m.status) for m in out}


def test_empty_register() -> None:
    v = by_code([], [])
    assert v == {"01": (0, "ok"), "02": (0, "ok"), "03": (0, "ok"),
                 "04": (None, "no_data"), "05": (0, "ok")}  # fmt: skip


def test_rsk01_levels_and_proposed_ignored() -> None:
    high = risk(3, 4, "high")
    assert by_code([high], [])["01"] == (1, "warning")
    crit = risk(5, 4, "critical")
    prop = risk(5, 5, "critical", status="proposed", owner=False)
    closed = risk(5, 5, "critical", status="closed")
    v = by_code([high, crit, prop, closed], [])
    assert v["01"] == (2, "critical") and v["02"] == (0, "ok")
    assert v["04"] == (16.0, None) and rsk04_status(16.0) == "critical"


def test_rsk02_owner_rules() -> None:
    medium_old = risk(2, 3, "medium", owner=False, age_days=8)
    medium_new = risk(2, 3, "medium", owner=False, age_days=3)
    assert by_code([medium_new], [])["02"] == (0, "ok")
    assert by_code([medium_old], [])["02"] == (0, "warning")
    assert by_code([medium_old, risk(4, 4, "critical", owner=False)], [])["02"] == (1, "critical")


def test_rsk03_stale_high_without_mitigation() -> None:
    old_high, old_crit = risk(3, 4, "high", age_days=31), risk(5, 5, "critical", age_days=40)
    assert by_code([old_high, risk(3, 4, "high", age_days=10)], [])["03"] == (1, "warning")
    assert by_code([old_high, old_crit], [mit(old_high, "in_progress", AS_OF)])["03"] == (
        1, "critical")  # fmt: skip


def test_rsk05_overdue_and_rsk04_bands() -> None:
    low = risk(1, 2, "low")
    late = [mit(low, "planned", AS_OF - timedelta(days=1)), mit(low, "done", date(2037, 1, 1))]
    assert by_code([low], late)["05"] == (1, "warning")
    crit = risk(5, 5, "critical")
    assert by_code([crit], [mit(crit, "in_progress", date(2037, 1, 1))])["05"] == (1, "critical")
    five = [mit(low, "planned", date(2037, 1, d)) for d in range(1, 6)]
    assert by_code([low], five)["05"] == (5, "critical")
    assert by_code([low], [mit(low, "planned", AS_OF)])["05"] == (0, "ok")  # due today
    assert [rsk04_status(x) for x in (9.9, 10.0, 14.9, 15.0)] == [
        "ok", "warning", "warning", "critical"]  # fmt: skip


def test_records_capped_and_sorted() -> None:
    many = [risk(3, 4, "high") for _ in range(60)] + [risk(5, 5, "critical")]
    out = compute_readings(many, [], AS_OF).items[0]
    assert out.value == 61 and len(out.records) == 50
    assert out.records[0].contribution == 25.0 and out.records[0].table == "risks"

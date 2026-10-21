"""TC-SAL-002 — BR-SAL-01..04, METRIC-CUS-01/02/06, stage order, periods (pure functions)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.modules.sales.services import calculations as calc


def test_br_sal_01_closing_probability() -> None:
    assert calc.closing_probability("closed_won") == Decimal(100)
    assert calc.closing_probability("closed_lost") == Decimal(0)
    assert calc.closing_probability("proposal") is None


@pytest.mark.parametrize(
    ("src", "dst", "err"),
    [("lead", "qualified", None), ("lead", "negotiation", None), ("lead", "closed_won", None),
     ("negotiation", "closed_lost", None), ("proposal", "qualified", "not_forward"),
     ("proposal", "proposal", "not_forward"), ("closed_won", "closed_lost", "closed"),
     ("closed_lost", "lead", "closed")],
)  # fmt: skip
def test_stage_transitions(src: str, dst: str, err: str | None) -> None:
    assert calc.transition_error(src, dst) == err


def test_br_sal_02_weighted_value() -> None:
    assert calc.weighted_value(800_000_000, 20) == 160_000_000  # 03 §5.2 example
    assert calc.weighted_value(1_000, Decimal("33.3333")) == 333
    assert calc.weighted_value(5, 50) == 3  # half-up


def test_br_sal_03_win_rate() -> None:
    assert calc.win_rate_pct(6, 14) == 30.0  # 03 §5.2 example
    assert calc.win_rate_pct(1, 2) == 33.3
    assert calc.win_rate_pct(0, 0) is None


def test_br_sal_04_coverage_and_attainment() -> None:
    assert calc.coverage_ratio(30_000_000_000, 10_000_000_000) == 3.0  # 03 §5.2 example
    assert calc.coverage_ratio(5, 0) is None and calc.coverage_ratio(5, None) is None
    assert calc.attainment_pct(9, 10) == 90.0
    assert calc.attainment_pct(9, None) is None


def test_averages() -> None:
    assert calc.avg_days([timedelta(days=10), timedelta(days=21)]) == 15.5
    assert calc.avg_days([]) is None
    assert calc.avg_amount([1, 2]) == 2 and calc.avg_amount([]) is None


def test_stage_durations() -> None:
    t0 = datetime(2026, 9, 1, tzinfo=UTC)
    now = t0 + timedelta(days=10)
    hist = [("lead", t0), ("qualified", t0 + timedelta(days=2))]
    assert calc.stage_durations(hist, now) == [
        ("lead", timedelta(days=2)), ("qualified", timedelta(days=8)),
    ]  # fmt: skip
    closed = [*hist, ("closed_won", t0 + timedelta(days=5))]
    assert [s for s, _ in calc.stage_durations(closed, now)] == ["lead", "qualified"]


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [([], "no_data"), (["ok", "no_data"], "no_data"), (["ok", "ok", "no_data"], "ok"),
     (["ok", "warning", "ok"], "warning"), (["warning", "critical", "ok"], "critical")],
)  # fmt: skip
def test_pillar_status(statuses: list[str], expected: str) -> None:
    assert calc.pillar_status(statuses) == expected


def test_resolve_period() -> None:
    today = date(2026, 10, 20)
    m = calc.resolve_period(None, today)
    assert (m.key, m.type, m.start, m.end) == ("2026-10", "month", date(2026, 10, 1),
                                               date(2026, 10, 31))  # fmt: skip
    q = calc.resolve_period("current_quarter", today)
    assert (q.key, q.start, q.end) == ("2026-Q4", date(2026, 10, 1), date(2026, 12, 31))
    y = calc.resolve_period("ytd", today)
    assert (y.type, y.start, y.end) == ("ytd", date(2026, 1, 1), today)
    assert calc.resolve_period("2026-12", today).end == date(2026, 12, 31)
    assert calc.resolve_period("2026-Q1", today).end == date(2026, 3, 31)
    assert calc.resolve_period("2025", today).type == "year"
    with pytest.raises(ValueError, match="period"):
        calc.resolve_period("custom", today)


def test_target_period_key_and_trend_months() -> None:
    assert calc.target_period_key_ok("month", "2026-10")
    assert calc.target_period_key_ok("quarter", "2026-Q4")
    assert calc.target_period_key_ok("year", "2026")
    assert not calc.target_period_key_ok("quarter", "2026-10")
    keys = [p.key for p in calc.last_months(date(2026, 2, 3), 3)]
    assert keys == ["2025-12", "2026-01", "2026-02"]
    assert calc.quarter_of(date(2026, 5, 1)).key == "2026-Q2"

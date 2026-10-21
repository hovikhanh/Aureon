"""TC-PRD-002 — pure BR-PRD-01 / METRIC-PRD math (03 §2.4, §5.4)."""

import pytest

from app.modules.product.services import calculations as calc

S = calc.Snapshot


def test_previous_periods_cross_year() -> None:
    assert calc.previous_periods("2037-02") == ["2036-11", "2036-12", "2037-01"]


def test_baseline_requires_three() -> None:
    assert calc.baseline([1.0, 1.2, 1.4]) == pytest.approx(1.2)
    assert calc.baseline([1.0, None, 1.4]) is None
    assert calc.baseline([1.0, 1.2]) is None


@pytest.mark.parametrize(
    ("current", "base", "expected"),
    [
        (2.0, 1.2, True),  # 03 example: +66.7% and ≥ 2%
        (1.8, 1.0, False),  # +80% but < 2%
        (2.41, 1.5, True),  # 14 TC-PRD-002 fixture
        (1.79, 1.5, False),  # seed 08 value
        (3.0, 2.0, False),  # exactly +50% is not "> 50%"
        (5.0, None, False),
    ],
)
def test_churn_anomaly(current: float, base: float | None, expected: bool) -> None:
    assert calc.is_churn_anomaly(current, base) is expected


def test_relative_change_and_rounding() -> None:
    assert calc.relative_change_pct(900, 1000) == -10.0
    assert calc.relative_change_pct(None, 1) is None
    assert calc.relative_change_pct(1, 0) is None
    assert calc.round1(None) is None
    assert calc.round1(2.25) == 2.3
    assert calc.pct(1, 3) == 33.3
    assert calc.pct(1, 0) is None


def test_weighted_and_aggregates() -> None:
    rows = [S(1000, 40, 1.0, 50, 40, 9), S(3000, None, 3.0, 30, 20, None), S(0, 90, 9.0, 90, 90, 1)]
    assert calc.weighted(rows, "retention_30d_pct") == 35.0
    assert calc.weighted(rows, "adoption_pct") == 40.0
    assert calc.weighted(rows, "nps") == 25.0
    assert calc.weighted([], "nps") is None
    assert calc.total_mau(rows) == 4000 and calc.total_mau([]) is None
    assert calc.worst_churn(rows) == 9.0 and calc.worst_churn([]) is None


def test_pillar_status() -> None:
    assert calc.pillar_status([]) == "no_data"
    assert calc.pillar_status(["ok", "no_data"]) == "no_data"
    assert calc.pillar_status(["ok", "warning", "critical"]) == "critical"
    assert calc.pillar_status(["ok", "warning", "ok"]) == "warning"
    assert calc.pillar_status(["ok"]) == "ok"

"""TC-FIN-005 — pure BR-FIN rules (03 §6 examples)."""

import pytest

from app.modules.finance import rules


def test_utilization_example_br_fin_05() -> None:
    assert rules.utilization_pct(1_100_000_000, 1_000_000_000) == 110.0
    assert rules.utilization_pct(1, 3) == 33.33


def test_utilization_rejects_zero_allocation() -> None:
    with pytest.raises(ValueError):
        rules.utilization_pct(1, 0)


@pytest.mark.parametrize(
    ("pct", "status"), [(100.0, "ok"), (100.01, "warning"), (110.0, "warning"), (110.5, "critical")]
)
def test_budget_status_thresholds(pct: float, status: str) -> None:
    assert rules.budget_status(pct) == status


def test_quarter_periods() -> None:
    assert rules.quarter_periods(2026, "Q3") == ["2026-07", "2026-08", "2026-09"]
    assert len(rules.quarter_periods(2026, None)) == 12
    assert rules.budget_period_key(2026, "Q1") == "2026-Q1"
    assert rules.budget_period_key(2026, None) == "2026"


def test_net_burn_br_fin_01() -> None:
    m = 1_000_000
    assert rules.net_burn([1400 * m, 1500 * m, 1600 * m], [1000 * m] * 3) == 500 * m
    # profitable months excluded from numerator and denominator
    assert rules.net_burn([900, 1500, 1600], [1000, 1000, 1000]) == 550
    assert rules.net_burn([1, 1], [5, 5]) == 0


def test_runway_br_fin_02_03_06() -> None:
    assert rules.runway_months(3_000_000_000, 500_000_000) == 6.0
    assert rules.runway_months(3_000_000_000, 0) is None
    assert rules.runway_months(None, 5) is None
    assert rules.runway_no_new_revenue(3_000_000_000, [1_500_000_000] * 3) == 2.0
    assert rules.runway_no_new_revenue(None, [1]) is None
    assert rules.runway_no_new_revenue(5, []) is None


def test_ratios() -> None:
    assert rules.gross_margin_pct(1000, 700) == 30.0
    assert rules.gross_margin_pct(0, 5) is None
    assert rules.growth_pct(110, 100) == 10.0
    assert rules.dso_days(500, 3000, 90) == 15.0
    assert rules.dso_days(1, 0, 30) is None
    assert rules.projected_month_burn(200, 0, 30, 15) == 400
    assert rules.projected_month_burn(1, 0, 30, 0) == 0
    assert rules.burn_variance_pct(400, 300) == 33.3
    assert rules.burn_variance_pct(1, 0) is None

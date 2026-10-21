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

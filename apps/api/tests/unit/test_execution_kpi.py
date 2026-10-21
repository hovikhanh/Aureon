"""TC-EXE-004 (T-133) — KPI achievement / 5-level band / KR progress / periods (pure)."""

from datetime import date
from decimal import Decimal as D

import pytest

from app.modules.execution.services.kpi_rules import (
    achievement_pct,
    band,
    kr_progress_pct,
    period_bounds,
    period_key_for,
    weighted_avg,
)


@pytest.mark.parametrize(
    ("ach", "expected"),
    [(69, "CRITICAL"), (70, "BELOW"), (89, "BELOW"), (90, "NEAR"), (99, "NEAR"),
     (100, "MEETS"), (109, "MEETS"), (110, "EXCEEDS"), (0, "CRITICAL")],
)  # fmt: skip
def test_band_boundaries(ach: int, expected: str) -> None:
    assert band(D(ach)) == expected


def test_band_custom_thresholds() -> None:
    assert band(D(50), {"CRITICAL": 0, "BELOW": 40, "NEAR": 80, "MEETS": 95, "EXCEEDS": 120}) \
        == "BELOW"  # fmt: skip


def test_achievement_by_direction() -> None:
    assert achievement_pct("HIGHER_IS_BETTER", D(90), D(100)) == D("90.0000")
    assert achievement_pct("HIGHER_IS_BETTER", D(300), D(100)) == D(150)  # cap
    assert achievement_pct("HIGHER_IS_BETTER", D(-5), D(100)) == D(0)  # floor
    assert achievement_pct("LOWER_IS_BETTER", D(5), D(4)) == D("80.0000")  # target/actual
    assert achievement_pct("LOWER_IS_BETTER", D(0), D(4)) == D(150)
    assert achievement_pct("LOWER_IS_BETTER", D(0), D(0)) == D(100)
    assert achievement_pct("BINARY", D(1), D(1)) == D(100)
    assert achievement_pct("BINARY", D(0), D(1)) == D(0)
    assert achievement_pct("WITHIN_RANGE", D(15), D(20), minimum=D(10)) == D(100)
    assert achievement_pct("WITHIN_RANGE", D(5), D(20), minimum=D(10)) == D(50)
    assert achievement_pct("WITHIN_RANGE", D(40), D(20), minimum=D(10)) == D(50)
    assert achievement_pct("WITHIN_RANGE", D(20), D(20)) == D(100)
    assert achievement_pct("HIGHER_IS_BETTER", D(1), D(3), cap=D(120)) == D("33.3333")


def test_kr_progress_and_weights() -> None:
    assert kr_progress_pct(D(0), D(10), D(5)) == D(50)
    assert kr_progress_pct(D(10), D(0), D(5)) == D(50)  # decreasing target
    assert kr_progress_pct(D(0), D(10), D(20)) == D(100)
    assert kr_progress_pct(D(0), D(10), None) == D(0)
    assert kr_progress_pct(D(5), D(5), D(5)) == D(100)
    assert kr_progress_pct(D(5), D(5), D(4)) == D(0)
    assert weighted_avg([]) == D(0)
    assert weighted_avg([(D(100), D(0)), (D(0), D(0))]) == D(50)
    assert weighted_avg([(D(100), D(3)), (D(0), D(1))]) == D(75)


def test_periods() -> None:
    d = date(2037, 8, 15)
    assert period_key_for("MONTH", d) == "2037-08"
    assert period_key_for("QUARTER", d) == "2037-Q3"
    assert period_key_for("YEAR", d) == "2037"
    assert period_bounds("2037-12") == (date(2037, 12, 1), date(2038, 1, 1))
    assert period_bounds("2037-02") == (date(2037, 2, 1), date(2037, 3, 1))
    assert period_bounds("2037-Q4") == (date(2037, 10, 1), date(2038, 1, 1))
    assert period_bounds("2037-Q1") == (date(2037, 1, 1), date(2037, 4, 1))
    assert period_bounds("2037") == (date(2037, 1, 1), date(2038, 1, 1))
    for bad in ("2037-13", "2037-Q5", "2037-1", "2037-ab"):
        with pytest.raises(ValueError):
            period_bounds(bad)

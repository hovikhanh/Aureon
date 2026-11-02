"""TC-M35-01 — MVP acceptance gate status logic (M3.5, R-DEC-145, 09 §2.2). Pure/stateless.

Covers the G2/G3 percentage band (`pct_status`) and the G1 adoption band (`g1_status`); G4 is a
trivial `0 → pass, else fail` asserted via the thresholds.
"""

from app.modules.ai.services.acceptance_service import (
    G1_MIN_DAYS_PER_WEEK,
    G2_PASS,
    G2_WARN,
    g1_status,
    pct_status,
)


def test_pct_status_bands_at_g2_thresholds() -> None:
    assert pct_status(None, G2_WARN, G2_PASS) == "no_data"
    assert pct_status(85.0, G2_WARN, G2_PASS) == "pass"
    assert pct_status(80.0, G2_WARN, G2_PASS) == "pass"
    assert pct_status(79.9, G2_WARN, G2_PASS) == "warning"
    assert pct_status(60.0, G2_WARN, G2_PASS) == "warning"
    assert pct_status(59.9, G2_WARN, G2_PASS) == "fail"
    assert pct_status(0.0, G2_WARN, G2_PASS) == "fail"


def test_g1_status_pass_requires_four_days_per_week() -> None:
    # 4 weeks window, 16 opened days → 4.0/week → pass
    assert g1_status(16, 4, True) == ("pass", 4.0)
    # 15 opened → 3.75/week → warning
    assert g1_status(15, 4, True) == ("warning", 3.75)
    # threshold is exactly 4.0/week
    assert G1_MIN_DAYS_PER_WEEK == 4.0


def test_g1_status_no_data_when_no_briefings() -> None:
    status, per_week = g1_status(0, 4, False)
    assert status == "no_data"
    assert per_week == 0.0


def test_g1_status_handles_single_week_window() -> None:
    assert g1_status(5, 1, True) == ("pass", 5.0)
    assert g1_status(3, 1, True) == ("warning", 3.0)

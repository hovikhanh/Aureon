"""TC-HR-004 (T-123) — BR-HR-01 annualised turnover + EP-80 period/trend helpers (pure)."""

from datetime import date

import pytest

from app.modules.hr.services.metrics import (
    Tenure,
    annualized_turnover_pct,
    average_tenure_months,
    delay_status,
    hires,
    leavers,
    on_payroll,
    period_turnover_pct,
    resolve_period,
    tenure_months,
    trend_months,
    turnover_status,
    worst,
)


def test_br_hr_01_examples() -> None:
    assert annualized_turnover_pct(3, 150, 150, 1) == 24.0  # 03 BR-HR-01 example
    assert annualized_turnover_pct(20, 150, 150, 12) == 13.3  # 08 seed → METRIC-HR-02
    assert annualized_turnover_pct(3, 148, 152, 3) == 8.0
    assert annualized_turnover_pct(0, 10, 10, 1) == 0.0


def test_turnover_undefined() -> None:
    assert annualized_turnover_pct(1, 0, 0, 1) is None
    assert annualized_turnover_pct(1, 10, 10, 0) is None
    assert annualized_turnover_pct(-1, 10, 10, 1) is None


def test_tenure() -> None:
    assert tenure_months(date(2025, 1, 15), date(2026, 1, 14)) == 11
    assert tenure_months(date(2025, 1, 15), date(2026, 1, 15)) == 12
    assert tenure_months(date(2027, 1, 1), date(2026, 1, 1)) == 0
    assert average_tenure_months([date(2025, 1, 1), date(2026, 1, 1)], date(2026, 7, 1)) == 12.0
    assert average_tenure_months([], date(2026, 1, 1)) is None


def test_roster_maths() -> None:
    rows = [
        Tenure(date(2020, 1, 1), None),
        Tenure(date(2020, 1, 1), date(2026, 9, 15)),
        Tenure(date(2026, 9, 10), None),
        Tenure(date(2026, 11, 1), None),
    ]
    start, end = date(2026, 9, 1), date(2026, 9, 30)
    assert len(on_payroll(rows, end)) == 2
    assert len(on_payroll(rows, date(2026, 8, 31))) == 2
    assert leavers(rows, start, end) == 1 and hires(rows, start, end) == 1
    assert period_turnover_pct(rows, start, end, 1) == 600.0  # 1 / 2 × 12 × 100


@pytest.mark.parametrize(
    ("spec", "key", "start", "end", "months"),
    [
        (None, "2026-10", date(2026, 10, 1), date(2026, 10, 31), 1),
        ("current_quarter", "2026-Q4", date(2026, 10, 1), date(2026, 12, 31), 3),
        ("ytd", "2026-YTD", date(2026, 1, 1), date(2026, 10, 31), 10),
        ("2026-02", "2026-02", date(2026, 2, 1), date(2026, 2, 28), 1),
        ("2025-Q4", "2025-Q4", date(2025, 10, 1), date(2025, 12, 31), 3),
    ],
)
def test_resolve_period(spec: str | None, key: str, start: date, end: date, months: int) -> None:
    p = resolve_period(spec, date(2026, 10, 20))
    assert (p.key, p.start, p.end, p.months) == (key, start, end, months)


@pytest.mark.parametrize("bad", ["custom", "2026-13", "2026-Q5", "x"])
def test_resolve_period_rejects(bad: str) -> None:
    with pytest.raises(ValueError):
        resolve_period(bad, date(2026, 10, 20))


def test_trend_months() -> None:
    t = trend_months(date(2026, 2, 28))
    assert (
        len(t) == 12
        and t[0][0] == "2025-03"
        and t[-1] == ("2026-02", date(2026, 2, 1), date(2026, 2, 28))
    )
    assert [k for k, *_ in t] == sorted(k for k, *_ in t)


def test_statuses() -> None:
    assert turnover_status(None) is None
    assert turnover_status(14.9) == "ok"
    assert turnover_status(15.0) == "warning"
    assert turnover_status(20.0) == "critical"
    assert delay_status([]) == "ok" and delay_status([10]) == "warning"
    assert delay_status([46, 2]) == "critical"
    assert worst(None, None) == "no_data"
    assert worst("ok", None, "warning") == "warning"
    assert worst("critical", "ok") == "critical"

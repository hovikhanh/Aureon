"""Business clock (08 §1 DEMO_REFERENCE_DATE)."""

from datetime import date

import pytest

from app.core import clock
from app.core.config import get_config


def test_month_helpers() -> None:
    assert clock.shift_month("2026-01", -1) == "2025-12"
    assert clock.shift_month("2026-12", 1) == "2027-01"
    assert clock.month_range("2026-12") == (date(2026, 12, 1), date(2027, 1, 1))
    assert clock.month_key(date(2026, 3, 9)) == "2026-03"


def test_business_today_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = get_config()
    monkeypatch.setattr(cfg, "demo_mode", True)
    monkeypatch.setattr(cfg, "demo_reference_date", "2026-10-20")
    assert clock.business_today() == date(2026, 10, 20)
    monkeypatch.setattr(cfg, "demo_mode", False)
    assert clock.business_today() != date(1970, 1, 1)

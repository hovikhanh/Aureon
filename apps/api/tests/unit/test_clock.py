"""Business clock (08 §1 DEMO_REFERENCE_DATE, D-15 BUSINESS_DATE_OVERRIDE)."""

import importlib
import operator
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.core import clock
from app.core.config import ConfigService, get_config


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


def test_override_pins_the_date_without_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-15: the business date no longer depends on DEMO_MODE."""
    cfg = get_config()
    monkeypatch.setattr(cfg, "demo_mode", False)
    monkeypatch.setattr(cfg, "business_date_override", date(2027, 2, 3))
    assert clock.business_today() == date(2027, 2, 3)
    assert clock.business_now().date() == date(2027, 2, 3)


def test_override_wins_over_the_demo_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = get_config()
    monkeypatch.setattr(cfg, "demo_mode", True)
    monkeypatch.setattr(cfg, "demo_reference_date", "2026-10-20")
    monkeypatch.setattr(cfg, "business_date_override", date(2026, 10, 21))
    assert clock.business_today() == date(2026, 10, 21)


def test_no_override_falls_back_to_the_real_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = get_config()
    monkeypatch.setattr(cfg, "demo_mode", False)
    monkeypatch.setattr(cfg, "business_date_override", None)
    assert clock.business_today() == datetime.now(UTC).date()


@pytest.mark.parametrize(
    ("raw", "parsed"), [("", None), ("  ", None), ("2026-10-20", date(2026, 10, 20))]
)
def test_override_env_parsing(
    monkeypatch: pytest.MonkeyPatch, raw: str, parsed: date | None
) -> None:
    monkeypatch.setenv("BUSINESS_DATE_OVERRIDE", raw)
    assert ConfigService().business_date_override == parsed


def test_invalid_override_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUSINESS_DATE_OVERRIDE", "20/10/2026")
    with pytest.raises(ValidationError):
        ConfigService()


# Modules that keep a local `today()` must delegate to the one business clock (D-15).
LOCAL_CLOCKS = [
    "app.modules.hr.services.hr_service:today",
    "app.modules.hr.services.org_service:_today",
    "app.modules.hr.services.structure_service:today",
    "app.modules.sales.services.analytics:SalesAnalytics.today",
    "app.modules.finance.services.invoice_service:today",
    "app.modules.execution.services.base:today",
    "app.modules.product.services.dashboard_service:ProductDashboardService.today",
]


@pytest.mark.parametrize("target", LOCAL_CLOCKS)
def test_every_module_clock_follows_the_override(
    monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    monkeypatch.setattr(get_config(), "business_date_override", date(2031, 7, 9))
    module, attr = target.split(":")
    fn = operator.attrgetter(attr)(importlib.import_module(module))
    assert fn() == date(2031, 7, 9)

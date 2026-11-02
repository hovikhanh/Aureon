"""Business "today" (08 §1: `DEMO_REFERENCE_DATE` is today for every date-dependent metric).

`DEMO_MODE=true` → the configured reference date; otherwise the UTC calendar date.
"""

from datetime import UTC, date, datetime

from app.core.config import get_config


def business_today() -> date:
    cfg = get_config()
    if cfg.demo_mode and cfg.demo_reference_date:
        return date.fromisoformat(cfg.demo_reference_date)
    return datetime.now(UTC).date()


def business_now() -> datetime:
    """Wall-clock instant pinned to the business calendar day (08 §1, DD-05).

    In demo mode a KPI/OKR check-in recorded "now" must land inside the business period
    (`period_key` derives from `business_today()`), so we keep the live time-of-day but move the
    date onto `DEMO_REFERENCE_DATE`. Outside demo mode this is plain `datetime.now(UTC)`.
    """
    now = datetime.now(UTC)
    day = business_today()
    if day == now.date():
        return now
    return now.replace(year=day.year, month=day.month, day=day.day)


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def shift_month(period_key: str, months: int) -> str:
    y, m = int(period_key[:4]), int(period_key[5:7])
    idx = y * 12 + (m - 1) + months
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def month_range(period_key: str) -> tuple[date, date]:
    """[first day, first day of next month)."""
    start = date(int(period_key[:4]), int(period_key[5:7]), 1)
    nxt = shift_month(period_key, 1)
    return start, date(int(nxt[:4]), int(nxt[5:7]), 1)

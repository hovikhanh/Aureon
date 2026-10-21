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

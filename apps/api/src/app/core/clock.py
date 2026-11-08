"""Business "today" — the single calendar every date-dependent rule and metric reads (08 §1).

Resolution order (D-15, separate from `DEMO_MODE`):
1. `BUSINESS_DATE_OVERRIDE` — explicit pin, independent of `DEMO_MODE`;
2. `DEMO_MODE=true` → `DEMO_REFERENCE_DATE` (backward-compatible alias: existing demo stacks and
   seeds keep their timeline without new configuration);
3. otherwise the UTC calendar date.

Timestamps of what happened (`created_at`, `done_at`, `computed_at`…) stay wall-clock.
"""

from datetime import UTC, date, datetime

from app.core.config import get_config


def business_today() -> date:
    cfg = get_config()
    if cfg.business_date_override is not None:
        return cfg.business_date_override
    if cfg.demo_mode and cfg.demo_reference_date:
        return date.fromisoformat(cfg.demo_reference_date)
    return datetime.now(UTC).date()


def business_now() -> datetime:
    """Wall-clock instant pinned to the business calendar day (08 §1, DD-05).

    With a pinned business date a KPI/OKR check-in recorded "now" must land inside the business
    period (`period_key` derives from `business_today()`), so we keep the live time-of-day but
    move the date onto it. Without a pin this is plain `datetime.now(UTC)`.
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

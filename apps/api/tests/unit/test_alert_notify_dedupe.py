"""TC-M21-09 (unit) — cửa sổ dedupe alert theo tuần ISO (R-DEC-88)."""

from datetime import UTC, datetime

from app.modules.platform.services.metric_store import _iso_week_start


def test_week_start_is_monday_midnight_utc() -> None:
    # 2026-10-31 là thứ Bảy → tuần ISO bắt đầu thứ Hai 2026-10-26 00:00 UTC
    start = _iso_week_start(datetime(2026, 10, 31, 14, 30, tzinfo=UTC))
    assert start == datetime(2026, 10, 26, 0, 0, tzinfo=UTC)
    assert start.isoweekday() == 1


def test_monday_maps_to_itself() -> None:
    start = _iso_week_start(datetime(2026, 10, 26, 9, 0, tzinfo=UTC))
    assert start == datetime(2026, 10, 26, 0, 0, tzinfo=UTC)


def test_sunday_same_week_as_prior_monday() -> None:
    # Chủ nhật 2026-11-01 vẫn thuộc tuần bắt đầu 2026-10-26
    start = _iso_week_start(datetime(2026, 11, 1, 23, 59, tzinfo=UTC))
    assert start == datetime(2026, 10, 26, 0, 0, tzinfo=UTC)


def test_two_alerts_same_week_share_window() -> None:
    a = _iso_week_start(datetime(2026, 10, 27, 1, 0, tzinfo=UTC))
    b = _iso_week_start(datetime(2026, 10, 30, 22, 0, tzinfo=UTC))
    assert a == b  # cùng cửa sổ → alert thứ hai bị dedupe

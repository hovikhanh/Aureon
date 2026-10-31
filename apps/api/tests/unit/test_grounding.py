"""TC-M24-01 — hard grounding validator (10 §8, R-DEC-105). Pure/stateless unit tests."""

from app.modules.ai.services.grounding import (
    NO_DATA_WARNING,
    UNGROUNDED_WARNING,
    enforce_grounding,
    grounded_values,
)


def _src(value: float) -> dict[str, object]:
    return {"type": "metric_value", "id": "m", "label": "m", "value": value}


def test_grounded_number_is_kept_no_warning() -> None:
    clean, warns = enforce_grounding("Doanh thu là 300 tỷ.", [_src(300_000_000_000)], [])
    assert "300 tỷ" in clean
    assert warns == []


def test_ungrounded_number_is_removed_with_warning() -> None:
    clean, warns = enforce_grounding("Lợi nhuận là 999 tỷ.", [_src(300_000_000_000)], [])
    assert "999" not in clean
    assert UNGROUNDED_WARNING in warns


def test_unit_scaling_triệu_matches_raw_value() -> None:
    # tool data holds 1_250_000 (đồng); the answer says "1,25 triệu" → grounded.
    clean, warns = enforce_grounding("Chi phí khoảng 1,25 triệu.", [], [{"amount": 1_250_000}])
    assert "1,25 triệu" in clean
    assert UNGROUNDED_WARNING not in warns


def test_percentage_grounded_against_bare_value() -> None:
    clean, warns = enforce_grounding("Tỷ lệ đạt 87%.", [], [{"dq_score": 87}])
    assert "87%" in clean
    assert UNGROUNDED_WARNING not in warns


def test_percentage_ungrounded_is_stripped() -> None:
    clean, warns = enforce_grounding("Win rate 42%.", [], [{"x": 10}])
    assert "42%" not in clean
    assert UNGROUNDED_WARNING in warns


def test_no_number_and_no_source_flags_no_data_when_data_requested() -> None:
    # a READ tool ran (data_requested) but produced nothing → no-data
    clean, warns = enforce_grounding(
        "Hiện chưa có dữ liệu trong phạm vi.", [], [], data_requested=True
    )
    assert NO_DATA_WARNING in warns
    assert clean  # the textual answer is preserved


def test_no_data_not_flagged_for_plain_action_reply() -> None:
    # no tool ran (data_requested=False) → an action/confirmation reply is not a no-data case
    _, warns = enforce_grounding("Đã soạn thẻ giao việc — chờ xác nhận.", [], [])
    assert NO_DATA_WARNING not in warns


def test_no_data_not_flagged_when_grounded_evidence_exists() -> None:
    _, warns = enforce_grounding(
        "Công ty đang bám sát mục tiêu.", [_src(5)], [], data_requested=True
    )
    assert NO_DATA_WARNING not in warns


def test_grounded_values_collects_sources_and_nested_leaves() -> None:
    vals = grounded_values(
        [_src(300.0)], [{"a": 1, "b": {"c": 2}, "list": [3, {"d": 4}], "flag": True}]
    )
    # `flag: True` must NOT contribute a value → exactly the 5 real numbers (True == 1.0 in Python,
    # so test the exact set rather than membership).
    assert vals == {300.0, 1.0, 2.0, 3.0, 4.0}


def test_vi_grouped_thousands_parsed() -> None:
    clean, warns = enforce_grounding("Số dư 1.250.000 đồng.", [], [{"balance": 1_250_000}])
    assert "1.250.000" in clean
    assert UNGROUNDED_WARNING not in warns


def test_period_ordinals_are_not_treated_as_data() -> None:
    # "quý 3", "năm 2026", "Q4" are time labels — never stripped, even with no sources.
    clean, warns = enforce_grounding("Doanh thu quý 3 năm 2026 ổn định.", [], [])
    assert "quý 3" in clean and "2026" in clean
    assert UNGROUNDED_WARNING not in warns


def test_bare_year_is_not_stripped() -> None:
    clean, warns = enforce_grounding("Kế hoạch cho 2027 đang xây dựng.", [], [])
    assert "2027" in clean
    assert UNGROUNDED_WARNING not in warns


def test_entity_codes_and_dates_are_preserved() -> None:
    # NV-0001 (code) and 06/11/2026 (date) carry label digits, not metric values.
    ans = "Đã soạn thẻ giao việc cho NV-0001 (hạn 06/11/2026) — chờ xác nhận."
    clean, warns = enforce_grounding(ans, [], [])
    assert "NV-0001" in clean and "06/11/2026" in clean
    assert warns == []

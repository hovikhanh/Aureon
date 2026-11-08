"""F-H1 — numbers that used to slip past the grounding gate (audit-ai, 10 §8, P05).

Each case below was kept verbatim by the validator before the fix, with `82` as the only source.
"""

import pytest

from app.modules.ai.services.grounding import (
    NO_DATA_WARNING,
    UNGROUNDED_WARNING,
    enforce_grounding,
)

SRC = [{"type": "metric_value", "id": "m", "label": "m", "value": 82}]


@pytest.mark.parametrize(
    ("answer", "forbidden"),
    [
        ("Doanh thu tháng 300 tỷ, đạt 82%.", "300"),
        ("Doanh thu năm 999 tỷ.", "999"),
        ("Lợi nhuận quý 45 tỷ.", "45"),
        ("Chi phí kỳ 77,5%.", "77,5"),
        ("Doanh thu ba trăm tỷ đồng.", "ba trăm"),
        ("Doanh thu hai mươi lăm tỷ.", "hai mươi lăm"),
        ("Biên lãi hai mươi phần trăm.", "hai mươi"),
        ("Tổng USD500000 và VND1000000.", "500000"),
        ("Tổng USD500000 và VND1000000.", "1000000"),
        ("Doanh thu 83,5% kế hoạch.", "83,5"),
        ("Doanh thu đạt 80,5%.", "80,5"),
        ("Doanh thu khoảng 1,250,000 đồng.", "1,250,000"),
        ("Doanh thu vài trăm tỷ.", "vài trăm tỷ"),
        ("Doanh thu 3 trăm tỷ.", "3 trăm"),
        ("Doanh thu 1 nghìn tỷ.", "1 nghìn"),
    ],
)
def test_unsupported_number_does_not_survive(answer: str, forbidden: str) -> None:
    clean, warns = enforce_grounding(answer, SRC, [])
    assert forbidden not in clean
    assert UNGROUNDED_WARNING in warns


def test_grounded_number_beside_a_removed_one_stays() -> None:
    clean, _ = enforce_grounding("Doanh thu tháng 300 tỷ, đạt 82%.", SRC, [])
    assert "82%" in clean
    assert "tháng" in clean


def test_removed_number_leaves_a_visible_placeholder_not_a_broken_sentence() -> None:
    clean, _ = enforce_grounding("Lợi nhuận là 999 tỷ.", SRC, [])
    assert clean == "Lợi nhuận là [chưa có nguồn]."
    clean_en, _ = enforce_grounding("Profit is 999 tỷ.", SRC, [], locale="en")
    assert clean_en == "Profit is [no source]."


@pytest.mark.parametrize(
    "answer",
    [
        "Doanh thu tháng 9 năm 2026 ổn định.",
        "Kết quả quý 3, Q4/2026 và T9/2026.",
        "Top 5 khách hàng, hạng 2, lần 3, tuần 42.",
        "Hạn ngày 20/10 lúc 14:30.",
        "Đối chiếu NV-0001 và METRIC-FIN-01 [1] [2].",
        "1. Tài chính\n2. Nhân sự",
        "Một số khách hàng và hai bên đã ký, tỷ lệ ổn định.",
        "Ba tỷ lệ chính đều ổn định.",
        "Đơn hàng tăng trong tháng năm, hàng trăm khách phản hồi.",
    ],
)
def test_labels_and_prose_are_not_data_numbers(answer: str) -> None:
    clean, warns = enforce_grounding(answer, [], [])
    assert clean == answer
    assert UNGROUNDED_WARNING not in warns


@pytest.mark.parametrize(
    ("answer", "value"),
    [
        ("Doanh thu 300 tỷ.", 299_600_000_000),  # display rounding of the source
        ("Doanh thu 1,2 tỷ.", 1_249_000_000),
        ("Doanh thu 1,25 tỷ.", 1_249_000_000),
        ("Tỷ lệ 82%.", 82.4),
        ("Tỷ lệ 82,4%.", 82.44),
        ("Doanh thu ba trăm tỷ đồng.", 300_000_000_000),
        ("Doanh thu 300.000.000.000 đồng.", 299_900_000_000),
        ("Doanh thu 1 nghìn tỷ.", 1_000_000_000_000),
        ("Tổng USD500000.", 500_000),
        ("Revenue 1,250,000.", 1_250_000),
    ],
)
def test_rounding_of_a_real_source_is_kept(answer: str, value: float) -> None:
    clean, warns = enforce_grounding(answer, [], [{"v": value}])
    assert clean == answer
    assert warns == []


def test_percent_does_not_borrow_unit_scaling() -> None:
    # 0,082 % × 1000 = 82: a percent is compared on its bare value only
    clean, warns = enforce_grounding("Tăng 0,082%.", SRC, [])
    assert "0,082" not in clean
    assert UNGROUNDED_WARNING in warns


def test_explicit_unit_does_not_match_the_bare_value() -> None:
    clean, warns = enforce_grounding("Doanh thu 82 tỷ.", SRC, [])
    assert "82" not in clean
    assert UNGROUNDED_WARNING in warns


def test_row_count_of_a_tool_list_is_evidence() -> None:
    data = [{"tasks": [{"title": "a"}, {"title": "b"}, {"title": "c"}]}]
    clean, warns = enforce_grounding("Có 3 việc quá hạn.", [], data)
    assert "3 việc" in clean
    assert warns == []


def test_trong_is_not_the_unit_tr() -> None:
    clean, _ = enforce_grounding("Đạt 82 trong tháng.", SRC, [])
    assert clean == "Đạt 82 trong tháng."


def test_no_data_semantics_unchanged() -> None:
    _, warns = enforce_grounding("Chưa có dữ liệu.", [], [], data_requested=True)
    assert warns == [NO_DATA_WARNING]

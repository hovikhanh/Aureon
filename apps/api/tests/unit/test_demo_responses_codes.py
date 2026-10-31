"""TC-M21-02 guard — mọi mã METRIC-* trong demo_responses.json phải có trong catalog.

Bắt lỗi đổi tên chỉ số (vd SEI METRIC-RSK-06→METRIC-STR-02, R-DEC-83) bỏ sót fixture AI:
placeholder `{METRIC-X}` và citation `[[METRIC-X]]` được điền từ tool result theo mã, nên mã
không còn trong catalog sẽ làm demo replay rơi về LLM (vỡ grounding P05). DB-independent.
"""

import json
import re
from pathlib import Path

from app.modules.platform.services.catalog import BY_CODE

DATA = Path(__file__).resolve().parents[2] / "src/app/modules/ai/demo_responses.json"
_METRIC = re.compile(r"METRIC-[A-Z]+-\d+")


def _codes() -> set[str]:
    raw = DATA.read_text(encoding="utf-8")
    entries = json.loads(raw)["entries"]
    found: set[str] = set()
    for e in entries:
        for key in ("answer_vi", "answer_en"):
            found.update(_METRIC.findall(e.get(key, "")))
    return found


def test_every_demo_metric_code_in_catalog() -> None:
    codes = _codes()
    assert codes, "demo_responses.json nên có ít nhất một mã METRIC-* để kiểm"
    unknown = sorted(c for c in codes if c not in BY_CODE)
    assert not unknown, f"mã METRIC-* không có trong catalog (đổi tên bỏ sót?): {unknown}"


def test_sei_renamed_to_str_02_everywhere() -> None:
    codes = _codes()
    assert "METRIC-RSK-06" not in codes, "SEI đã đổi sang METRIC-STR-02 (R-DEC-83)"

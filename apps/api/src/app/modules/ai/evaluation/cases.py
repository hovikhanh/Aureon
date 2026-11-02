"""Curated standard-suite corpus for the Evaluation Engine (M3.4, T-827, R-DEC-139).

Each `EvalCase` is self-contained and fixture-only (no DB, no network): it carries the model's
answer, the grounded evidence available that turn (`sources` / `tool_data`), the tools the model
actually called, and the expectations per axis. The corpus is versioned by `SUITE` +
`PROMPT_VERSION`; grow it by appending cases (do not mutate past ids, so historical runs stay
comparable). A deliberately failing case (`ground-fabricated`) keeps the grounding axis honest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.modules.ai.services.tool_executor import SourceRef

SUITE = "core-v1"
PROMPT_VERSION = "v1"


@dataclass(frozen=True)
class EvalCase:
    id: str
    kind: str  # grounding | accuracy | tool_choice
    answer: str
    expected_substrings: list[str] = field(default_factory=list)
    expected_tools: list[str] | None = None
    tools_called: list[str] = field(default_factory=list)
    sources: list[Any] = field(default_factory=list)
    tool_data: list[dict[str, Any]] = field(default_factory=list)


def _src(value: float, label: str) -> SourceRef:
    return SourceRef(type="metric_value", id=label, label=label, value=value)


CASES: list[EvalCase] = [
    # --- grounding: a number backed by a SourceRef must survive the gate ---
    EvalCase(
        id="ground-revenue-ok",
        kind="grounding",
        answer="Doanh thu quý này đạt 1.250.000.000 đ.",
        sources=[_src(1_250_000_000, "METRIC-FIN-01")],
        tool_data=[{"value": 1_250_000_000}],
    ),
    # --- grounding (negative): a fabricated number must be stripped → axis fails ---
    EvalCase(
        id="ground-fabricated",
        kind="grounding",
        answer="Lợi nhuận biên khoảng 37,5% trong tháng.",
        sources=[_src(1_250_000_000, "METRIC-FIN-01")],
        tool_data=[{"value": 1_250_000_000}],
    ),
    # --- grounding: an answer with no numbers and no evidence is trivially grounded ---
    EvalCase(
        id="ground-no-number",
        kind="grounding",
        answer="Đã tạo việc theo dõi và giao cho chủ sở hữu.",
    ),
    # --- accuracy: the answer must contain the expected phrasing ---
    EvalCase(
        id="acc-at-risk",
        kind="accuracy",
        answer="KR 'Tăng tỷ lệ gia hạn' đang ở mức rủi ro do phụ thuộc chưa xong.",
        expected_substrings=["rủi ro", "phụ thuộc"],
    ),
    EvalCase(
        id="acc-no-data",
        kind="accuracy",
        answer="Hiện chưa có dữ liệu cho chỉ số này.",
        expected_substrings=["chưa có dữ liệu"],
    ),
    # --- tool_choice: the model must call exactly the expected tool(s) ---
    EvalCase(
        id="tool-kpi-status",
        kind="tool_choice",
        answer="KPI đang đạt mục tiêu.",
        expected_tools=["get_kpi_status"],
        tools_called=["get_kpi_status"],
    ),
    EvalCase(
        id="tool-search-docs",
        kind="tool_choice",
        answer="Tôi đã tìm trong SOP và thấy quy trình liên quan.",
        expected_tools=["search_documents"],
        tools_called=["search_documents"],
    ),
    EvalCase(
        id="tool-create-task",
        kind="tool_choice",
        answer="Đã tạo việc theo yêu cầu.",
        expected_tools=["create_task"],
        tools_called=["create_task"],
    ),
]

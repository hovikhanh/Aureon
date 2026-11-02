"""M3.4 ai-eval EVAL-* (T-827, R-DEC-139) — the curated Evaluation Engine corpus, fixture mode.

Runs the `core-v1` suite through the pure scorer (no DB, no provider — the corpus carries scripted
answers) and asserts the quality bar the suite exists to guard:

- EVAL-01: the suite stays grounded — exactly the one deliberately-fabricated case fails grounding,
  so a regression that lets hallucinated numbers through would drop `grounding_pct` below its bar.
- EVAL-02: accuracy and tool-choice axes are clean on the curated corpus (100%).
- EVAL-03: every case serialises to the `{id, kind, passed, detail}` shape EP-AI-27/28 expose.
"""

from __future__ import annotations

from app.modules.ai.evaluation import CASES, score_suite


def test_eval01_grounding_catches_exactly_the_fabricated_case() -> None:
    score = score_suite(list(CASES))
    failed = {c["id"] for c in score.cases if not c["passed"]}
    assert failed == {"ground-fabricated"}
    assert score.grounding_pct < 100.0
    assert score.passed == score.total - 1


def test_eval02_accuracy_and_tool_choice_clean() -> None:
    score = score_suite(list(CASES))
    assert score.accuracy_pct == 100.0
    assert score.tool_choice_pct == 100.0
    assert score.score_pct > 90.0


def test_eval03_case_shape_matches_endpoint_contract() -> None:
    score = score_suite(list(CASES))
    for c in score.cases:
        assert set(c) == {"id", "kind", "passed", "detail"}
        assert c["kind"] in {"grounding", "accuracy", "tool_choice"}
        assert isinstance(c["passed"], bool)

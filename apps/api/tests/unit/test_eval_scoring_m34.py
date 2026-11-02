"""TC-M34-01 — Evaluation Engine scoring (M3.4, R-DEC-139). Pure/stateless unit tests.

Covers the three axes (grounding / accuracy / tool_choice), the per-case pass rule (every
applicable axis passes), the suite aggregate (`_pct` denominators exclude non-applicable axes),
and the curated corpus invariant: exactly one deliberately-fabricated case fails grounding so a
regression that stops catching hallucinations drops `grounding_pct` below 100.
"""

from app.modules.ai.evaluation import CASES, SUITE, score_suite
from app.modules.ai.evaluation.cases import PROMPT_VERSION, EvalCase, _src
from app.modules.ai.evaluation.scoring import score_case


def _case(**kw: object) -> EvalCase:
    base = dict(
        id="t",
        kind="grounding",
        answer="",
        expected_substrings=(),
        expected_tools=None,
        tools_called=(),
        sources=(),
        tool_data=(),
    )
    base.update(kw)
    return EvalCase(**base)  # type: ignore[arg-type]


def test_grounding_axis_passes_when_number_is_sourced() -> None:
    c = _case(kind="grounding", answer="Doanh thu 1200.", sources=(_src(1200.0, "rev"),))
    r = score_case(c)
    assert r.grounding.applicable and r.grounding.passed
    assert r.passed


def test_grounding_axis_fails_on_fabricated_number() -> None:
    c = _case(kind="grounding", answer="Doanh thu 9999.", sources=(_src(1200.0, "rev"),))
    r = score_case(c)
    assert r.grounding.applicable and not r.grounding.passed
    assert not r.passed


def test_accuracy_axis_checks_all_expected_substrings_casefold() -> None:
    c = _case(kind="accuracy", answer="KR đang ở mức RỦI RO", expected_substrings=("rủi ro",))
    assert score_case(c).accuracy.passed
    miss = _case(kind="accuracy", answer="ổn định", expected_substrings=("rủi ro",))
    assert not score_case(miss).accuracy.passed


def test_tool_choice_axis_is_set_equality() -> None:
    ok = _case(
        kind="tool_choice",
        expected_tools=("TOOL-get_kpi_status",),
        tools_called=("TOOL-get_kpi_status",),
    )
    assert score_case(ok).tool_choice.passed
    wrong = _case(
        kind="tool_choice",
        expected_tools=("TOOL-get_kpi_status",),
        tools_called=("TOOL-create_task",),
    )
    assert not score_case(wrong).tool_choice.passed


def test_non_applicable_axes_excluded_from_denominator() -> None:
    # expected_tools=None → the tool_choice axis is not applicable and never fails the case
    r = score_case(_case(kind="accuracy", answer="x", expected_substrings=("x",)))
    assert not r.tool_choice.applicable
    assert r.passed


def test_suite_aggregate_and_fabricated_invariant() -> None:
    score = score_suite(list(CASES))
    assert score.total == len(CASES)
    # exactly one curated case (the fabricated one) must fail → not a clean sweep
    assert score.passed == score.total - 1
    assert 0.0 < score.grounding_pct < 100.0
    assert score.accuracy_pct == 100.0
    assert score.tool_choice_pct == 100.0
    ids = {c["id"] for c in score.cases if not c["passed"]}
    assert ids == {"ground-fabricated"}


def test_suite_identifiers_stable() -> None:
    assert SUITE == "core-v1"
    assert PROMPT_VERSION == "v1"

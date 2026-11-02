"""Pure scoring for the Evaluation Engine (M3.4, T-827, R-DEC-139) — no DB, no network.

A case is scored on three independent axes:

- **grounding** — every number in the answer is backed by a `SourceRef` / tool result. Reuses the
  runtime gate `enforce_grounding`: the case passes when it strips nothing (clean == answer) and
  raises no warning, i.e. the model did not fabricate a number (FR-AIQ-01, BRD-P05).
- **accuracy**  — the (case-folded) answer contains every expected substring.
- **tool_choice** — the set of tools the model actually called equals the expected set.

`score_suite` aggregates per-case axis passes into `_pct` (0–100) and a combined `score_pct`
(mean of the three axes). An axis a case does not exercise (e.g. a case with no expected tool)
is excluded from that axis' denominator so it never dilutes the score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.modules.ai.services.grounding import enforce_grounding


@dataclass(frozen=True)
class AxisResult:
    applicable: bool
    passed: bool


@dataclass(frozen=True)
class CaseResult:
    id: str
    kind: str
    grounding: AxisResult
    accuracy: AxisResult
    tool_choice: AxisResult

    @property
    def passed(self) -> bool:
        """A case passes when every axis it exercises passes."""
        return all(
            a.passed for a in (self.grounding, self.accuracy, self.tool_choice) if a.applicable
        )

    def as_dict(self) -> dict[str, Any]:
        detail = ",".join(
            name
            for name, a in (
                ("grounding", self.grounding),
                ("accuracy", self.accuracy),
                ("tool_choice", self.tool_choice),
            )
            if a.applicable and not a.passed
        )
        return {
            "id": self.id,
            "kind": self.kind,
            "passed": self.passed,
            "detail": f"failed:{detail}" if detail else "ok",
        }


@dataclass
class SuiteScore:
    total: int = 0
    passed: int = 0
    grounding_pct: float = 0.0
    accuracy_pct: float = 0.0
    tool_choice_pct: float = 0.0
    score_pct: float = 0.0
    cases: list[dict[str, Any]] = field(default_factory=list)


def _pct(passed: int, total: int) -> float:
    return round(100.0 * passed / total, 2) if total else 0.0


def _grounding(answer: str, sources: list[Any], tool_data: list[dict[str, Any]]) -> AxisResult:
    clean, warnings = enforce_grounding(
        answer, sources, tool_data, data_requested=bool(sources or tool_data)
    )
    return AxisResult(applicable=True, passed=clean == answer and not warnings)


def _accuracy(answer: str, expected: list[str]) -> AxisResult:
    if not expected:
        return AxisResult(applicable=False, passed=True)
    low = answer.casefold()
    return AxisResult(applicable=True, passed=all(e.casefold() in low for e in expected))


def _tool_choice(called: list[str], expected: list[str] | None) -> AxisResult:
    if expected is None:
        return AxisResult(applicable=False, passed=True)
    return AxisResult(applicable=True, passed=set(called) == set(expected))


def score_case(case: Any) -> CaseResult:
    """Score one `EvalCase` (duck-typed to avoid an import cycle with `cases`)."""
    return CaseResult(
        id=case.id,
        kind=case.kind,
        grounding=_grounding(case.answer, case.sources, case.tool_data),
        accuracy=_accuracy(case.answer, case.expected_substrings),
        tool_choice=_tool_choice(case.tools_called, case.expected_tools),
    )


def score_suite(cases: list[Any]) -> SuiteScore:
    results = [score_case(c) for c in cases]
    out = SuiteScore(total=len(results), passed=sum(1 for r in results if r.passed))
    for axis in ("grounding", "accuracy", "tool_choice"):
        applicable = [getattr(r, axis) for r in results if getattr(r, axis).applicable]
        setattr(out, f"{axis}_pct", _pct(sum(1 for a in applicable if a.passed), len(applicable)))
    out.score_pct = round((out.grounding_pct + out.accuracy_pct + out.tool_choice_pct) / 3, 2)
    out.cases = [r.as_dict() for r in results]
    return out

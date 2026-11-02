"""D26 Evaluation Engine (M3.4, T-827, R-DEC-138/139).

A small standard-suite runner that scores an agent prompt/model version on three axes —
**grounding** (FR-AIQ-01, no fabricated numbers), **accuracy** (answer matches the expected
substring), **tool-choice** (the model called the expected tool) — over a curated fixture corpus.
The scoring in `scoring.py` is pure (no DB, no network) so Vitest-style unit tests cover it
directly; `EvaluationService` persists one `ENT-AIEvaluation` per run. CI always runs
`MODEL_GATEWAY_MODE=fixture` — never a live provider.
"""

from app.modules.ai.evaluation.cases import CASES, SUITE, EvalCase
from app.modules.ai.evaluation.scoring import AxisResult, CaseResult, SuiteScore, score_suite

__all__ = [
    "CASES",
    "SUITE",
    "AxisResult",
    "CaseResult",
    "EvalCase",
    "SuiteScore",
    "score_suite",
]

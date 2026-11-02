"""D26 Evaluation Engine service (M3.4, T-827, R-DEC-139/140).

`run()` scores the curated fixture corpus (pure, via `score_suite`) and persists one
`ENT-AIEvaluation` row tagged with the active prompt/model/provider/gateway-mode. CI always runs
`MODEL_GATEWAY_MODE=fixture` (no live provider). `list_runs()` / `get()` are the read side behind
EP-AI-27/28. The run never calls an LLM itself — the corpus already carries the model's scripted
answers — so a regression in scoring, not provider cost, is what the suite guards.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.core.deps import Principal
from app.core.envelope import Page
from app.core.errors import NotFoundError
from app.modules.ai.evaluation import CASES, SUITE, score_suite
from app.modules.ai.evaluation.cases import PROMPT_VERSION
from app.modules.ai.models import AIEvaluation
from app.modules.ai.repositories import AIEvaluationRepository
from app.modules.ai.schemas import AIEvaluationOut


class EvaluationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AIEvaluationRepository(db)

    async def run(
        self, *, suite: str = SUITE, prompt_version: str = PROMPT_VERSION,
        triggered_by: uuid.UUID | None = None,
    ) -> AIEvaluationOut:  # fmt: skip
        """Score the corpus and persist one run; the caller commits."""
        cfg = get_config()
        started = datetime.now(UTC)
        score = score_suite(list(CASES))
        finished = datetime.now(UTC)
        row = AIEvaluation(
            suite=suite,
            prompt_version=prompt_version,
            model=cfg.model_chat,
            provider=cfg.model_provider_primary,
            gateway_mode=cfg.model_gateway_mode,
            total=score.total,
            passed=score.passed,
            grounding_pct=score.grounding_pct,
            accuracy_pct=score.accuracy_pct,
            tool_choice_pct=score.tool_choice_pct,
            score_pct=score.score_pct,
            cases=score.cases,
            started_at=started,
            finished_at=finished,
            triggered_by=triggered_by,
        )
        self.db.add(row)
        await self.db.flush()
        return self._out(row)

    async def list_runs(
        self, user: Principal, *, suite: str | None, model: str | None, provider: str | None,
        limit: int, offset: int,
    ) -> Page[AIEvaluationOut]:  # fmt: skip
        rows, total = await self.repo.page(
            suite=suite, model=model, provider=provider, limit=limit, offset=offset
        )
        return Page(items=[self._out(r) for r in rows], total=total, limit=limit, offset=offset)

    async def get(self, user: Principal, evaluation_id: uuid.UUID) -> AIEvaluationOut:
        row = await self.repo.by_id(evaluation_id)
        if row is None:
            raise NotFoundError("Evaluation not found")
        return self._out(row)

    @staticmethod
    def _out(row: AIEvaluation) -> AIEvaluationOut:
        return AIEvaluationOut(
            id=row.id,
            suite=row.suite,
            prompt_version=row.prompt_version,
            model=row.model,
            provider=row.provider,
            gateway_mode=row.gateway_mode,
            total=row.total,
            passed=row.passed,
            grounding_pct=float(row.grounding_pct),
            accuracy_pct=float(row.accuracy_pct),
            tool_choice_pct=float(row.tool_choice_pct),
            score_pct=float(row.score_pct),
            cases=row.cases,
            started_at=row.started_at,
            finished_at=row.finished_at,
            triggered_by=row.triggered_by,
        )

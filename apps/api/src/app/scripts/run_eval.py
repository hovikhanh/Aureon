"""Evaluation Engine runner CLI (M3.4, T-827, R-DEC-139).

    uv run python -m app.scripts.run_eval [--suite core-v1] [--prompt-version v1] [--no-persist]

Scores the curated fixture corpus and prints a summary. By default it also persists one
`ENT-AIEvaluation` per active tenant (R-DEC-21); `--no-persist` scores only (useful in CI /
dry runs with no DB). Always `MODEL_GATEWAY_MODE=fixture` — the corpus carries scripted answers,
so this never calls a live provider.
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import active_tenant_ids, tenant_scope
from app.modules.ai.evaluation import CASES, SUITE, score_suite
from app.modules.ai.evaluation.cases import PROMPT_VERSION
from app.modules.ai.services.evaluation_service import EvaluationService


def _print_summary(suite: str, prompt_version: str) -> None:
    score = score_suite(list(CASES))
    print(f"suite={suite} prompt_version={prompt_version}")
    print(f"  passed       {score.passed}/{score.total}")
    print(f"  grounding    {score.grounding_pct:.2f}%")
    print(f"  accuracy     {score.accuracy_pct:.2f}%")
    print(f"  tool_choice  {score.tool_choice_pct:.2f}%")
    print(f"  score        {score.score_pct:.2f}%")
    for c in score.cases:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"    [{mark}] {c['id']:<22} {c['kind']:<12} {c['detail']}")


async def _persist(suite: str, prompt_version: str) -> None:
    from app.workers.events import _engine

    async with _engine() as engine:
        for tenant in active_tenant_ids():
            with tenant_scope(tenant):
                async with AsyncSession(engine, expire_on_commit=False) as session:
                    out = await EvaluationService(session).run(
                        suite=suite, prompt_version=prompt_version
                    )
                    await session.commit()
                    print(f"  persisted run {out.id} (tenant {tenant})")


def main() -> int:
    parser = argparse.ArgumentParser(prog="run_eval")
    parser.add_argument("--suite", default=SUITE)
    parser.add_argument("--prompt-version", default=PROMPT_VERSION)
    parser.add_argument("--no-persist", action="store_true", help="score only, do not write DB")
    args = parser.parse_args()

    _print_summary(args.suite, args.prompt_version)
    if not args.no_persist:
        asyncio.run(_persist(args.suite, args.prompt_version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

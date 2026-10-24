"""AI cost & usage report (T-308, EP-119 `/ai/usage`, DEC-131) — `ai:admin`.

Aggregates `ENT-ModelCallLog` over a window into `{ budget_usd, used_usd, used_pct, rows }`.
Cost is stored as `estimated_cost_micro_usd` (integer micro-USD, no float drift); the summary
converts to USD only at the edge. `group_by` supports the keys backed by columns in v2.0
(`provider | model | task_kind | user`); department / agent / classification budgets are deferred
to v2.1 (DEC-150). An 80% spend trips `warn_80pct`; ≥100% trips `over_budget` (the chat path
returns `429 AI_QUOTA_EXCEEDED` — ModelGateway budget guard). Caller supplies the window; the
default is the current calendar month.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import Float, Integer, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.modules.ai.models import ModelCallLog
from app.modules.ai.schemas import CostRowOut, CostSummaryOut

GroupBy = Literal["provider", "model", "task_kind", "user"]
_GROUP_COLUMN = {
    "provider": ModelCallLog.provider,
    "model": ModelCallLog.model,
    "task_kind": ModelCallLog.task_kind,
    "user": ModelCallLog.user_id,
}
_MICRO = 1_000_000


def month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class CostService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def usage(
        self, *, group_by: GroupBy = "provider",
        start: datetime | None = None, end: datetime | None = None,
    ) -> CostSummaryOut:  # fmt: skip
        now = datetime.now(UTC)
        start = start or month_start(now)
        end = end or now
        key_col = _GROUP_COLUMN[group_by]
        is_error = case((ModelCallLog.status != "ok", 1), else_=0)
        stmt = (
            select(
                key_col.label("key"),
                func.count().label("calls"),
                func.coalesce(func.sum(ModelCallLog.tokens_in), 0).label("tokens_in"),
                func.coalesce(func.sum(ModelCallLog.tokens_out), 0).label("tokens_out"),
                func.coalesce(func.sum(ModelCallLog.estimated_cost_micro_usd), 0).label("micro"),
                func.coalesce(cast(func.avg(cast(is_error, Float)), Float), 0.0).label(
                    "error_rate"
                ),
                func.coalesce(
                    cast(func.percentile_cont(0.95).within_group(ModelCallLog.latency_ms), Integer),
                    0,
                ).label("p95_ms"),
            )
            .where(ModelCallLog.created_at >= start, ModelCallLog.created_at <= end)
            .group_by(key_col)
            .order_by(func.sum(ModelCallLog.estimated_cost_micro_usd).desc())
        )
        rows: list[CostRowOut] = []
        used_micro = 0
        for r in (await self.db.execute(stmt)).all():
            used_micro += int(r.micro)
            rows.append(
                CostRowOut(
                    key=str(r.key) if r.key is not None else "(unknown)",
                    calls=int(r.calls),
                    tokens_in=int(r.tokens_in),
                    tokens_out=int(r.tokens_out),
                    cost_usd=int(r.micro) / _MICRO,
                    error_rate=round(float(r.error_rate), 4),
                    p95_ms=int(r.p95_ms),
                )
            )
        budget = float(get_config().ai_monthly_budget_usd)
        used = used_micro / _MICRO
        used_pct = round(used / budget * 100, 2) if budget > 0 else 0.0
        return CostSummaryOut(
            budget_usd=budget,
            used_usd=round(used, 6),
            used_pct=used_pct,
            period=start.date().isoformat(),
            over_budget=used >= budget > 0,
            warn_80pct=used >= budget * 0.8 > 0,
            rows=rows,
        )

    async def spend_by_agent(self, *, start: datetime | None = None) -> dict[str, float]:
        """Month-to-date USD per `agent_profile_code` (EP-AI-16 `month_spend_usd`, FR-AIQ-05)."""
        start = start or month_start(datetime.now(UTC))
        stmt = (
            select(ModelCallLog.agent_profile_code,
                   func.coalesce(func.sum(ModelCallLog.estimated_cost_micro_usd), 0))
            .where(ModelCallLog.created_at >= start,
                   ModelCallLog.agent_profile_code.is_not(None))
            .group_by(ModelCallLog.agent_profile_code)
        )  # fmt: skip
        return {str(k): int(v) / _MICRO for k, v in (await self.db.execute(stmt)).all()}

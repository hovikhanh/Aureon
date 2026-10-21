"""EP-66 forecasts (FR-FIN-05, T-103) → `EVT-finance.forecast_updated`.

A new forecast for a scenario becomes `is_current` and retires the previous one (history kept,
partial UQ `(scenario) WHERE is_current`). `horizon` 1m has no DB value (CK 3/6/12) → 422
(DEC-188). `confidence_pct` is stored in `assumptions.confidence_pct` (no column in 05) and
mapped to the per-line `confidence_level` band (DEC-133 thresholds: ≥ 90 HIGH, ≥ 60 MEDIUM).
`closing_cash` = latest CashPosition + cumulative (revenue − expense).
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import current_actor, record_audit
from app.core.deps import Principal
from app.core.errors import BusinessRuleError, NotFoundError
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.finance.models import Forecast, ForecastLine
from app.modules.finance.repositories import ForecastRepository
from app.modules.finance.schemas import (
    HORIZON_MONTHS,
    ForecastCreate,
    ForecastLineIn,
    ForecastLineOut,
    ForecastOut,
    ForecastUpdate,
)

EVT_FORECAST_UPDATED = "finance.forecast_updated"
MONTHS_HORIZON = {v: k for k, v in HORIZON_MONTHS.items()}


def confidence_band(pct: float | None) -> str:
    if pct is None or pct < 60:
        return "LOW"
    return "HIGH" if pct >= 90 else "MEDIUM"


def _months(horizon: str) -> int:
    if horizon not in HORIZON_MONTHS:
        raise BusinessRuleError(
            "horizon must be 3m, 6m or 1y",
            details={"field": "horizon", "allowed": ["3m", "6m", "1y"]},
        )
    return HORIZON_MONTHS[horizon]


def _check_lines(lines: list[ForecastLineIn], months: int) -> None:
    keys = [ln.period_key for ln in lines]
    if len(set(keys)) != len(keys):
        raise BusinessRuleError("duplicate period_key in lines", details={"field": "lines"})
    if len(keys) > months:
        raise BusinessRuleError(
            "more lines than the horizon", details={"field": "lines", "max": months}
        )


class ForecastService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ForecastRepository(db)

    async def out(self, f: Forecast) -> ForecastOut:
        lines = await self.repo.lines(f.id)
        assumptions = dict(f.assumptions or {})
        return ForecastOut(
            id=f.id, version=f.version, created_at=f.created_at, updated_at=f.updated_at,
            scenario=f.scenario, horizon=MONTHS_HORIZON[f.horizon_months],
            horizon_months=f.horizon_months, is_current=f.is_current,
            generated_at=f.generated_at, generated_by=f.generated_by,
            confidence_pct=assumptions.get("confidence_pct"), assumptions=assumptions,
            lines=[
                ForecastLineOut(
                    period_key=ln.period_key, revenue=ln.projected_revenue,
                    expense=ln.projected_expenses, net_profit=ln.projected_net_profit,
                    closing_cash=ln.projected_closing_cash, currency=ln.currency,
                    confidence_level=ln.confidence_level,
                )
                for ln in lines
            ],
        )  # fmt: skip

    async def _build_lines(
        self, forecast_id: uuid.UUID, lines: list[ForecastLineIn], confidence: float | None
    ) -> list[ForecastLine]:
        cash = await self.repo.latest_closing()
        band = confidence_band(confidence)
        rows = []
        for ln in sorted(lines, key=lambda x: x.period_key):
            net = ln.revenue - ln.expense
            cash += net
            rows.append(
                ForecastLine(
                    forecast_id=forecast_id,
                    period_key=ln.period_key,
                    projected_revenue=ln.revenue,
                    projected_expenses=ln.expense,
                    projected_net_profit=net,
                    projected_closing_cash=cash,
                    confidence_level=band,
                    source="MANUAL",
                )
            )
        return rows

    async def _publish(self, f: Forecast, out: ForecastOut) -> None:
        await publish_in_tx(
            self.db, event_type=EVT_FORECAST_UPDATED, producer="finance",
            aggregate_schema="finance", aggregate_table="forecasts", aggregate_id=f.id,
            payload={
                "forecast_id": str(f.id), "scenario": f.scenario, "horizon": out.horizon,
                "periods": [ln.period_key for ln in out.lines],
                "projected_net_profit_total": sum(ln.net_profit for ln in out.lines),
                "min_projected_closing_cash": min(ln.closing_cash for ln in out.lines),
                "currency": "VND", "version": f.version,
            },
        )  # fmt: skip

    async def _audit(self, action: str, f: Forecast, before: Any, after: ForecastOut) -> None:
        await record_audit(
            self.db, action=action, target_schema="finance", target_table="forecasts",
            target_id=f.id, before=before.model_dump(mode="json") if before else None,
            after=after.model_dump(mode="json"),
        )  # fmt: skip

    async def list_forecasts(
        self, page: PageParams, *, scenario: str | None, horizon: str | None,
        current_only: bool,
    ) -> tuple[list[ForecastOut], int]:  # fmt: skip
        filters: dict[str, Any] = {}
        if scenario:
            filters["scenario"] = scenario
        if horizon:
            filters["horizon_months"] = _months(horizon)
        if current_only:
            filters["is_current"] = True
        items, total = await self.repo.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters,
        )  # fmt: skip
        return [await self.out(f) for f in items], total

    async def get(self, id_: uuid.UUID) -> Forecast:
        f = await self.repo.get(id_)
        if f is None:
            raise NotFoundError("forecast not found")
        return f

    async def create(self, user: Principal, body: ForecastCreate) -> ForecastOut:
        months = _months(body.horizon)
        _check_lines(body.lines, months)
        previous = await self.repo.current(body.scenario)
        if previous is not None:
            await self.repo.update(previous, is_current=False, updated_by=user.user_id)
        f = await self.repo.create(
            scenario=body.scenario, horizon_months=months, generated_at=datetime.now(UTC),
            generated_by=current_actor().type, is_current=True,
            assumptions={**body.assumptions, "confidence_pct": body.confidence_pct},
            source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        self.db.add_all(await self._build_lines(f.id, body.lines, body.confidence_pct))
        await self.db.flush()
        await self.db.refresh(f)
        out = await self.out(f)
        await self._audit("finance.forecast_create", f, None, out)
        await self._publish(f, out)
        return out

    async def update(
        self, user: Principal, id_: uuid.UUID, body: ForecastUpdate, expected: int
    ) -> ForecastOut:
        f = await self.get(id_)
        before = await self.out(f)
        assumptions = dict(f.assumptions or {})
        if body.assumptions is not None:
            assumptions = {**body.assumptions, "confidence_pct": assumptions.get("confidence_pct")}
        if body.confidence_pct is not None:
            assumptions["confidence_pct"] = body.confidence_pct
        await self.repo.update(
            f, expected_version=expected, assumptions=assumptions, updated_by=user.user_id
        )
        if body.lines is not None:
            _check_lines(body.lines, f.horizon_months)
            for old in await self.repo.lines(f.id):
                await self.db.delete(old)
            await self.db.flush()
            self.db.add_all(
                await self._build_lines(f.id, body.lines, assumptions.get("confidence_pct"))
            )
            await self.db.flush()
        elif body.confidence_pct is not None:
            for ln in await self.repo.lines(f.id):
                ln.confidence_level = confidence_band(body.confidence_pct)
            await self.db.flush()
        await self.db.refresh(f)
        out = await self.out(f)
        await self._audit("finance.forecast_update", f, before, out)
        await self._publish(f, out)
        return out

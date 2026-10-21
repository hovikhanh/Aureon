"""EP-100 `/risk/dashboard` (FR-RSK-07, 10 §5): summary + heatmap 5×5 + `risk_score_trend`.

`metrics: []`, `open_alerts`/`unacknowledged_alerts` = 0 and `strategy_execution_index` = null
until the platform metric store / alert engine and execution are wired (DEC-219). Pillar
status is derived from METRIC-RSK-01..05 computed on the fly (same code as the provider).
"""

from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today, month_range, shift_month
from app.core.deps import Principal
from app.core.errors import BadRequestError
from app.modules.hr.services.metrics import resolve_period
from app.modules.risk.repositories import MitigationRepository, RiskRepository
from app.modules.risk.schemas import (
    HeatCell,
    PeriodOut,
    RiskDashboardOut,
    RiskScorePoint,
    RiskSummary,
)
from app.modules.risk.services import analytics, rules, scope

TREND_MONTHS = 6


def _between(ts: Any, start: date, end: date) -> bool:
    return ts is not None and start <= ts.date() <= end


class RiskDashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def dashboard(
        self, user: Principal, period: str | None, today: date | None = None
    ) -> RiskDashboardOut:
        today = today or business_today()
        try:
            p = resolve_period(period, today)
        except ValueError as exc:
            raise BadRequestError(str(exc), details={"field": "period"}) from exc
        as_of = min(p.end, today)
        risks = list(await RiskRepository(self.db).scoped(*scope.read_filter(user)))
        ids = {r.id for r in risks}
        mits = [m for m in await MitigationRepository(self.db).live_all() if m.risk_id in ids]
        current = as_of >= today
        live = analytics.open_on(risks, as_of, current=current)
        readings = analytics.compute_readings(risks, mits, as_of, current=current)
        closed = [
            r for r in risks if r.status == "closed" and _between(r.updated_at, p.start, p.end)
        ]
        opened = [
            r for r in risks if r.status != "proposed" and _between(r.identified_at, p.start, p.end)
        ]
        summary = RiskSummary(
            open_risks=len(live),
            critical_count=sum(r.severity == "critical" for r in live),
            high_count=sum(r.severity == "high" for r in live),
            aggregate_risk_score=rules.aggregate_score([analytics.score(r) for r in live]),
            opened_in_period=len(opened),
            closed_in_period=len(closed),
            mitigations_active=sum(m.status in rules.ACTIVE_MITIGATION for m in mits),
            mitigations_overdue=len(analytics.overdue(mits, as_of)),
            unacknowledged_alerts=0,
            strategy_execution_index=None,
        )
        heat = rules.heatmap([(r.likelihood, r.impact) for r in live])
        trend: list[RiskScorePoint] = []
        for i in range(TREND_MONTHS - 1, -1, -1):
            key = shift_month(f"{as_of.year:04d}-{as_of.month:02d}", -i)
            day = min(month_range(key)[1] - timedelta(days=1), as_of)
            snap = analytics.open_on(risks, day, current=day >= today)
            trend.append(RiskScorePoint(
                period_key=key, open_risks=len(snap),
                aggregate_risk_score=rules.aggregate_score([analytics.score(r) for r in snap]),
            ))  # fmt: skip
        return RiskDashboardOut(
            status=rules.pillar_status(readings.statuses()),
            period=PeriodOut(key=p.key, type=p.type, start_date=p.start, end_date=p.end),
            summary=summary, heatmap=[HeatCell(**c) for c in heat], metrics=[],
            risk_score_trend=trend, open_alerts=0,
        )  # fmt: skip

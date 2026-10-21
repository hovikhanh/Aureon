"""Sales read models — EP-70 dashboard, EP-75 pipeline, EP-76 performance (FR-SAL-04/05/07).

Aggregates are computed from the scoped deal set with the pure BR-SAL functions in
`calculations.py`. Scope (02 §6.2, DEC-193): MANAGER sees only deals of their department;
`sales:query` without `sales:read` gets aggregates only (no per-owner rows / filter).

`metrics[]` of the dashboard is `[]` until the metric store (`ENT-MetricValue`, METRIC-CUS-*)
is computed by `recompute_metrics` in S2; therefore the pillar `status` is derived from an
empty metric list → `no_data` (03 §4) until then. Summary numbers are live.
"""

import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.modules.sales.models import Deal, SalesTarget
from app.modules.sales.repositories import (
    DealRepository,
    StageHistoryRepository,
    TargetRepository,
)
from app.modules.sales.schemas import (
    PerformanceRow,
    PeriodOut,
    PipelineOut,
    PipelineStage,
    PipelineTrendPoint,
    SalesDashboardOut,
    SalesSummary,
    WinRateTrendPoint,
)
from app.modules.sales.services import calculations as calc
from app.modules.sales.services import scope

TREND_MONTHS = 6


def period_out(p: calc.Period) -> PeriodOut:
    return PeriodOut(key=p.key, type=p.type, start_date=p.start, end_date=p.end)


def _end_of(d: date) -> datetime:
    return datetime.combine(d + timedelta(days=1), time.min, tzinfo=UTC)


def _closed_in(deals: Iterable[Deal], p: calc.Period, stage: str) -> list[Deal]:
    lo, hi = datetime.combine(p.start, time.min, tzinfo=UTC), _end_of(p.end)
    return [d for d in deals if d.stage == stage and d.closed_at and lo <= d.closed_at < hi]


def _open(deals: Iterable[Deal]) -> list[Deal]:
    return [d for d in deals if d.stage in calc.OPEN_STAGES]


def _open_closing_in(deals: Iterable[Deal], p: calc.Period) -> list[Deal]:
    return [
        d for d in _open(deals)
        if d.expected_close_date and p.start <= d.expected_close_date <= p.end
    ]  # fmt: skip


def _team_target(targets: Sequence[SalesTarget]) -> int | None:
    return next((t.target_amount for t in targets if t.scope == "team"), None)


class SalesAnalytics:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.deals = DealRepository(db)
        self.history = StageHistoryRepository(db)
        self.targets = TargetRepository(db)

    @staticmethod
    def today() -> date:
        return datetime.now(UTC).date()

    async def _scoped_deals(self, user: Principal, owner_id: uuid.UUID | None = None) -> list[Deal]:
        where: list[Any] = []
        if scope.is_department_scoped(user):
            where.append(Deal.department_id == user.department_id)
        if owner_id is not None:
            scope.require_detail_reader(user)
            where.append(Deal.assigned_to == owner_id)
        return list(await self.deals.scoped(*where))

    async def _quota(self, user: Principal, key: str, owner_id: uuid.UUID | None) -> int | None:
        """Quota for a period key: individual target of `owner_id`, else the team target.

        Department-scoped users get `None` for the team quota: it is company-wide (DEC-193).
        """
        rows = await self.targets.by_period(key)
        if owner_id is not None:
            return next((t.target_amount for t in rows if t.owner_id == owner_id), None)
        return None if scope.is_department_scoped(user) else _team_target(rows)

    # ---------- EP-75 ----------
    async def pipeline(
        self, user: Principal, period: str | None, owner_id: uuid.UUID | None
    ) -> PipelineOut:
        today = self.today()
        p = calc.resolve_period(period, today) if period else None
        deals = await self._scoped_deals(user, owner_id)
        hist = await self.history.for_deals([d.id for d in deals])
        per_deal: dict[uuid.UUID, list[tuple[str, datetime]]] = defaultdict(list)
        for h in hist:
            per_deal[h.deal_id].append((h.stage, h.entered_at))
        now = datetime.now(UTC)
        spent: dict[str, list[timedelta]] = defaultdict(list)
        for rows in per_deal.values():
            for stage, dur in calc.stage_durations(rows, now):
                spent[stage].append(dur)
        stages = []
        for stage in calc.STAGE_ORDER:
            if stage in calc.CLOSED_STAGES:
                bucket = (
                    _closed_in(deals, p, stage) if p else [d for d in deals if d.stage == stage]
                )
            else:
                pool = _open_closing_in(deals, p) if p else _open(deals)
                bucket = [d for d in pool if d.stage == stage]
            stages.append(
                PipelineStage(
                    stage=stage,
                    count=len(bucket),
                    value=sum(d.deal_value for d in bucket),
                    weighted_value=sum(d.weighted_value for d in bucket),
                    avg_days_in_stage=calc.avg_days(spent.get(stage, [])),
                )
            )
        quarter = calc.quarter_of(p.end if p else today)
        open_value = sum(d.deal_value for d in _open_closing_in(deals, quarter))
        coverage = calc.coverage_ratio(open_value, await self._quota(user, quarter.key, owner_id))
        return PipelineOut(
            period=period_out(p) if p else None, stages=stages, coverage_ratio=coverage
        )

    # ---------- EP-76 ----------
    async def performance(
        self, user: Principal, period: str | None, group_by: str
    ) -> list[PerformanceRow]:
        p = calc.resolve_period(period, self.today())
        if group_by == "owner":
            scope.require_detail_reader(user)
        deals = await self._scoped_deals(user)
        won, lost = _closed_in(deals, p, "closed_won"), _closed_in(deals, p, "closed_lost")
        if group_by == "team":
            return [await self._perf_row(user, "team", p.key, None, won, lost)]
        owners = sorted({d.assigned_to for d in won + lost}, key=str)
        return [
            await self._perf_row(
                user,
                str(o),
                p.key,
                o,
                [d for d in won if d.assigned_to == o],
                [d for d in lost if d.assigned_to == o],
            )
            for o in owners
        ]

    async def _perf_row(
        self, user: Principal, ref: str, key: str, owner: uuid.UUID | None,
        won: list[Deal], lost: list[Deal],
    ) -> PerformanceRow:  # fmt: skip
        closed = sum(d.deal_value for d in won)
        quota = await self._quota(user, key, owner)
        return PerformanceRow(
            owner_ref=ref, closed_value=closed, quota=quota,
            attainment_pct=calc.attainment_pct(closed, quota),
            win_rate_pct=calc.win_rate_pct(len(won), len(lost)),
        )  # fmt: skip

    # ---------- EP-70 ----------
    async def dashboard(self, user: Principal, period: str | None) -> SalesDashboardOut:
        today = self.today()
        p = calc.resolve_period(period, today)
        deals = await self._scoped_deals(user)
        open_ = _open(deals)
        won, lost = _closed_in(deals, p, "closed_won"), _closed_in(deals, p, "closed_lost")
        closed_revenue = sum(d.deal_value for d in won)
        quarter = calc.quarter_of(p.end)
        q_open = sum(d.deal_value for d in _open_closing_in(deals, quarter))
        summary = SalesSummary(
            pipeline_value=sum(d.deal_value for d in open_),
            weighted_pipeline=sum(d.weighted_value for d in open_),
            deals_open=len(open_), deals_won=len(won), deals_lost=len(lost),
            win_rate_pct=calc.win_rate_pct(len(won), len(lost)),
            avg_deal_value=calc.avg_amount(d.deal_value for d in won),
            closed_revenue=closed_revenue,
            quota_attainment_pct=calc.attainment_pct(
                closed_revenue, await self._quota(user, p.key, None)
            ),
            avg_sales_cycle_days=calc.avg_days(
                d.closed_at - d.created_at for d in won if d.closed_at
            ),
            pipeline_coverage=calc.coverage_ratio(
                q_open, await self._quota(user, quarter.key, None)
            ),
        )  # fmt: skip
        metrics: list[dict[str, Any]] = []  # METRIC-CUS-* from the metric store — S2
        return SalesDashboardOut(
            status=calc.pillar_status(m["status"] for m in metrics),
            period=period_out(p), summary=summary, metrics=metrics,
            pipeline_trend=self._pipeline_trend(deals, p.end),
            win_rate_trend=self._win_rate_trend(deals, p.end),
        )  # fmt: skip

    @staticmethod
    def _pipeline_trend(deals: Sequence[Deal], end: date) -> list[PipelineTrendPoint]:
        """Deals open at each month end (created before, not closed yet then).

        Values are the deals' current `deal_value` / `weighted_value` — no value snapshots exist
        before the metric store (S2).
        """
        out = []
        for m in calc.last_months(end, TREND_MONTHS):
            cut = _end_of(m.end)
            open_at = [
                d for d in deals
                if d.created_at < cut and (d.closed_at is None or d.closed_at >= cut)
            ]  # fmt: skip
            out.append(
                PipelineTrendPoint(
                    period_key=m.key,
                    pipeline_value=sum(d.deal_value for d in open_at),
                    weighted_pipeline=sum(d.weighted_value for d in open_at),
                )
            )
        return out

    @staticmethod
    def _win_rate_trend(deals: Sequence[Deal], end: date) -> list[WinRateTrendPoint]:
        out = []
        for m in calc.last_months(end, TREND_MONTHS):
            w, lo = (
                len(_closed_in(deals, m, "closed_won")),
                len(_closed_in(deals, m, "closed_lost")),
            )
            out.append(
                WinRateTrendPoint(
                    period_key=m.key, won=w, lost=lo, win_rate_pct=calc.win_rate_pct(w, lo)
                )
            )
        return out

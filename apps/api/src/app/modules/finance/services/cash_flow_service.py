"""EP-128 13-week cash flow (DEC-148, FR-FIN-05, T-106) → `cash_flow_forecast_updated`.

Model (DEC-201):
- week 1 starts on the Monday of business today; opening cash = latest CashPosition.
- receivables: open OUT invoices by `due_date` (past due → week 1); `collection_on_time_pct`
  arrives on time, the rest 4 weeks later (dropped if beyond week 13).
- payables: open IN invoices by `due_date` (past due → week 1).
- payroll: `payroll_monthly_override` or the 3-month average of `salary` expenses — company
  total only, never per person — paid in the week that contains each month end.
- opex: `fixed_opex_weekly` or the 3-month average of other expenses × 12 / 52.
- confidence per line: weeks 1–4 HIGH, 5–8 MEDIUM, 9–13 LOW.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import current_actor, record_audit
from app.core.clock import business_today, month_key, month_range, shift_month
from app.core.errors import NotFoundError
from app.core.events.outbox import publish_in_tx
from app.modules.finance.models import CashFlowForecast, CashFlowForecastLine
from app.modules.finance.repositories import AnalyticsRepository, CashFlowRepository
from app.modules.finance.schemas import CashFlowAssumptions, CashFlowForecastOut, CashFlowLineOut

WEEKS = 13
LATE_WEEKS = 4
EVT_UPDATED = "finance.cash_flow_forecast_updated"
INPUTS_KEY = "_inputs"


def _int(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_index(start: date, d: date | None) -> int:
    """0-based week of `d` (past or missing → 0); may be ≥ WEEKS."""
    if d is None or d < start:
        return 0
    return (d - start).days // 7


def band(week_no: int) -> str:
    return "HIGH" if week_no <= 4 else "MEDIUM" if week_no <= 8 else "LOW"


def no_cash_position() -> NotFoundError:
    return NotFoundError("no cash position recorded", details={"status_reason": "NO_CASH_POSITION"})


class CashFlowService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CashFlowRepository(db)
        self.analytics = AnalyticsRepository(db)

    async def out(self, f: CashFlowForecast) -> CashFlowForecastOut:
        lines = await self.repo.lines(f.id)
        low = next((ln for ln in lines if ln.week_no == f.min_cash_week), None)
        return CashFlowForecastOut(
            id=f.id, start_week=f.start_week, weeks=f.weeks, opening_cash=f.opening_cash,
            currency=f.currency, min_projected_cash=f.min_projected_cash,
            min_cash_week=f.min_cash_week,
            confidence_level=low.confidence_level if low else band(f.min_cash_week),
            generated_at=f.generated_at, generated_by=f.generated_by,
            assumptions={k: v for k, v in (f.assumptions or {}).items() if k != INPUTS_KEY},
            lines=[CashFlowLineOut.model_validate(ln, from_attributes=True) for ln in lines],
            stale=(f.assumptions or {}).get(INPUTS_KEY) != await self.repo.inputs_fingerprint(),
        )  # fmt: skip

    async def current(self, as_of: date | None = None) -> CashFlowForecastOut:
        f = await self.repo.current()
        if f is None or (as_of is not None and f.start_week > as_of):
            if await self.analytics.cash_on_or_before(month_key(as_of or business_today())):
                raise NotFoundError(
                    "no cash flow forecast yet", details={"status_reason": "NOT_COMPUTED"}
                )
            raise no_cash_position()
        return await self.out(f)

    async def _monthly_averages(self, today: date) -> tuple[int, int]:
        """(avg monthly payroll, avg monthly opex) over the 3 closed months."""
        months = [shift_month(month_key(today), -i) for i in (3, 2, 1)]
        payroll = sum((await self.analytics.monthly_expense(months, "salary")).values())
        total = sum((await self.analytics.monthly_expense(months)).values())
        cogs = sum((await self.analytics.monthly_expense(months, "cogs")).values())
        return _int(Decimal(payroll) / 3), _int(Decimal(total - payroll - cogs) / 3)

    async def recompute(
        self, assumptions: CashFlowAssumptions | None = None, *, reason: str = "manual"
    ) -> CashFlowForecastOut:
        today = business_today()
        cash = await self.analytics.cash_on_or_before(month_key(today))
        if cash is None:
            raise no_cash_position()
        prev = await self.repo.current()
        if assumptions is None:
            stored = dict(prev.assumptions or {}) if prev else {}
            keys = CashFlowAssumptions.model_fields
            assumptions = CashFlowAssumptions.model_validate(
                {k: v for k, v in stored.items() if k in keys}
            )
        start = monday(today)
        inflow = [0] * WEEKS
        outflow_pay = [0] * WEEKS
        on_time = Decimal(str(assumptions.collection_on_time_pct)) / 100
        for due, amount in await self.repo.open_invoices("OUT"):
            w = week_index(start, due)
            timely = _int(amount * on_time)
            if w < WEEKS:
                inflow[w] += timely
            if w + LATE_WEEKS < WEEKS:
                inflow[w + LATE_WEEKS] += amount - timely
        for due, amount in await self.repo.open_invoices("IN"):
            w = week_index(start, due)
            if w < WEEKS:
                outflow_pay[w] += amount

        avg_payroll, avg_opex = await self._monthly_averages(today)
        payroll_month = assumptions.payroll_monthly_override
        if payroll_month is None:
            payroll_month = avg_payroll
        opex_week = assumptions.fixed_opex_weekly
        if opex_week is None:
            opex_week = _int(Decimal(avg_opex) * 12 / 52)
        payroll = [0] * WEEKS
        key = month_key(start)
        while True:
            month_end = month_range(key)[1] - timedelta(days=1)
            w = week_index(start, month_end)
            if w >= WEEKS:
                break
            if month_end >= start:
                payroll[w] += payroll_month
            key = shift_month(key, 1)

        if prev is not None:
            await self.repo.update(prev, is_current=False)
        f = await self.repo.create(
            start_week=start, weeks=WEEKS, opening_cash=cash.closing_balance,
            currency=cash.currency, min_projected_cash=cash.closing_balance, min_cash_week=1,
            generated_at=datetime.now(UTC), generated_by=current_actor().type,
            is_current=True,
            assumptions={**assumptions.model_dump(), "reason": reason,
                         "payroll_monthly": payroll_month, "opex_weekly": opex_week},
            source="MANUAL" if reason == "manual" else "EVENT",
        )  # fmt: skip
        closing = cash.closing_balance
        lowest: tuple[int, int] = (cash.closing_balance + 1, 1)  # replaced by week 1
        rows = []
        for i in range(WEEKS):
            net = inflow[i] - outflow_pay[i] - payroll[i] - opex_week
            closing += net
            if i == 0 or closing < lowest[0]:
                lowest = (closing, i + 1)
            rows.append(
                CashFlowForecastLine(
                    forecast_id=f.id, week_no=i + 1, week_start=start + timedelta(weeks=i),
                    inflow_receivables=inflow[i], inflow_other=0,
                    outflow_payables=outflow_pay[i], outflow_payroll=payroll[i],
                    outflow_opex=opex_week, outflow_other=0, net_flow=net,
                    closing_cash=closing, currency=cash.currency,
                    confidence_level=band(i + 1), source=f.source,
                )
            )  # fmt: skip
        f.min_projected_cash, f.min_cash_week = lowest
        self.db.add_all(rows)
        await self.db.flush()
        f.assumptions = {**f.assumptions, INPUTS_KEY: await self.repo.inputs_fingerprint()}
        await self.db.flush()
        await self.db.refresh(f)
        out = await self.out(f)
        await record_audit(
            self.db, action="finance.cash_flow_recompute", target_schema="finance",
            target_table="cash_flow_forecasts", target_id=f.id,
            after={"min_projected_cash": f.min_projected_cash, "min_cash_week": f.min_cash_week,
                   "reason": reason},
        )  # fmt: skip
        await publish_in_tx(
            self.db, event_type=EVT_UPDATED, producer="finance", aggregate_schema="finance",
            aggregate_table="cash_flow_forecasts", aggregate_id=f.id,
            payload={"forecast_id": str(f.id), "min_projected_cash": f.min_projected_cash,
                     "min_cash_week": f.min_cash_week, "currency": f.currency},
        )  # fmt: skip
        return out


async def recompute_on_event(session: AsyncSession, reason: str) -> uuid.UUID | None:
    """Consumer helper: recompute only when a cash position exists (else nothing to do)."""
    svc = CashFlowService(session)
    if await svc.analytics.cash_on_or_before(month_key(business_today())) is None:
        return None
    return (await svc.recompute(reason=reason)).id


def assumptions_of(payload: dict[str, Any] | None) -> CashFlowAssumptions | None:
    return CashFlowAssumptions.model_validate(payload) if payload else None

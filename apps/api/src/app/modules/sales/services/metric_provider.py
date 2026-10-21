"""Sales metric provider — METRIC-CUS-01..04, CUS-06 + METRIC-FIN-01 (revenue vs team target;
revenue via finance public service) — CUS-05 NPS comes from product — DEC-205.

Company scope, period = last closed month before `as_of` (CUS-01: the quarter of `as_of`).
"Change vs 3 periods" (CUS-02 points, CUS-06 %) are sent as `threshold_input`; CUS-02 needs
≥ 10 closed deals in the 3 base periods (03 ALERT-CUS-02), else no comparison (input 0).
CUS-03 / CUS-04 use revenue by client from finance's public `revenue_by_client`.
"""

from collections.abc import Sequence
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import month_key, shift_month
from app.core.metrics import MetricReading, RecordRef, metric_provider
from app.modules.finance.services.revenue_query import revenue_by_client, revenue_total
from app.modules.sales import models as m
from app.modules.sales.repositories import DealRepository, TargetRepository
from app.modules.sales.services import calculations as calc
from app.modules.sales.services.analytics import _closed_in, _open_closing_in, _team_target

MIN_CLOSED_FOR_TREND = 10


def _period(key: str) -> calc.Period:
    return calc.month_period(int(key[:4]), int(key[5:7]))


def _win(deals: Sequence[m.Deal], p: calc.Period) -> tuple[int, int]:
    return len(_closed_in(deals, p, "closed_won")), len(_closed_in(deals, p, "closed_lost"))


def _cycle(deals: Sequence[m.Deal], p: calc.Period) -> float | None:
    won = _closed_in(deals, p, "closed_won")
    return calc.avg_days(d.closed_at - d.created_at for d in won if d.closed_at)


def _months(last: str, n: int) -> list[str]:
    return [shift_month(last, -i) for i in range(n - 1, -1, -1)]


async def compute_sales(db: AsyncSession, as_of: date) -> list[MetricReading]:
    deals = list(await DealRepository(db).scoped())
    last = shift_month(month_key(as_of), -1)
    p = _period(last)
    base = [_period(k) for k in _months(shift_month(last, -1), 3)]
    out: list[MetricReading] = []

    month_target = _team_target(await TargetRepository(db).by_period(last))
    revenue = await revenue_total(db, [last])
    out.append(MetricReading(
        "METRIC-FIN-01", calc_pct(revenue, month_target or 0), last,
        status_reason=None if month_target else "NO_TARGET",
    ))  # fmt: skip

    quarter = calc.quarter_of(as_of)
    q_deals = _open_closing_in(deals, quarter)
    target = _team_target(await TargetRepository(db).by_period(quarter.key))
    out.append(MetricReading(
        "METRIC-CUS-01", calc.coverage_ratio(sum(d.deal_value for d in q_deals), target),
        quarter.key, period_type="QUARTER", status_reason=None if target else "NO_TARGET",
        records=tuple(RecordRef("sales", "deals", str(d.id)) for d in q_deals[:50]),
    ))  # fmt: skip

    won, lost = _win(deals, p)
    rate = calc.win_rate_pct(won, lost)
    base_wl = [_win(deals, b) for b in base]
    base_closed = sum(w + lo for w, lo in base_wl)
    base_rate = calc.win_rate_pct(sum(w for w, _ in base_wl), sum(lo for _, lo in base_wl))
    drop = 0.0
    if rate is not None and base_rate is not None and base_closed >= MIN_CLOSED_FOR_TREND:
        drop = round(base_rate - rate, 1)
    out.append(MetricReading("METRIC-CUS-02", rate, last, threshold_input=drop))

    cur = await revenue_by_client(db, [last])
    prev = await revenue_by_client(db, [shift_month(last, -1)])
    prev_total = sum(prev.values())
    kept = sum(cur.get(c, 0) for c in prev)
    out.append(MetricReading("METRIC-CUS-03", calc_pct(kept, prev_total), last))

    rolling = await revenue_by_client(db, _months(last, 12))
    top5 = sum(sorted(rolling.values(), reverse=True)[:5])
    out.append(MetricReading("METRIC-CUS-04", calc_pct(top5, sum(rolling.values())), last,
                             period_type="ROLLING_12M"))  # fmt: skip

    cycle = _cycle(deals, p)
    base_cycles = [c for c in (_cycle(deals, b) for b in base) if c is not None]
    change = 0.0
    if cycle is not None and base_cycles:
        avg = sum(base_cycles) / len(base_cycles)
        change = round((cycle - avg) / avg * 100, 1) if avg else 0.0
    out.append(MetricReading("METRIC-CUS-06", cycle, last, threshold_input=change))
    return out


def calc_pct(num: int, den: int) -> float | None:
    return round(num / den * 100, 1) if den else None


@metric_provider("sales")
async def compute(db: AsyncSession, as_of: date) -> list[MetricReading]:
    return await compute_sales(db, as_of)

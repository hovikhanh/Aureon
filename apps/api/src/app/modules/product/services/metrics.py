"""Product metric provider — METRIC-PRD-01..05 + METRIC-CUS-05 NPS (03 §2.3–2.4, DEC-205).

Company scope, `period_key` = last closed month before `as_of` (`YYYY-MM`). Mapping (DEC-214):
- PRD-01 value = Σ MAU of launched products' snapshots of the period; `threshold_input` = MAU
  drop % vs the 3-period average (0 when no full baseline).
- PRD-02 value = worst product churn of the period; `threshold_input` = largest relative churn
  increase % vs that product's 3-period average among products at ≥ the 2% floor, else 0.
- PRD-03 = MAU-weighted retention 30d of the period.
- PRD-04 = roadmap on-time % for the quarter containing the period (late = 03 rule, as of
  `as_of`; `dropped` excluded).
- PRD-05 = release attainment %: features released in the period ÷ features planned in it
  (roadmap item `planned_date` in the period, or released in it).
- CUS-05 = MAU-weighted NPS of each live product's latest snapshot (`≤` period).
`value=None` → `no_data` with `status_reason`.
"""

import uuid
from collections.abc import Sequence
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import month_key, month_range, shift_month
from app.core.metrics import MetricReading, RecordRef, metric_provider
from app.modules.product.models import Feature, ProductMetric, RoadmapItem
from app.modules.product.repositories import (
    FeatureRepository,
    MetricRepository,
    ProductRepository,
    ReleaseRepository,
    RoadmapRepository,
)
from app.modules.product.services import calculations as calc
from app.modules.product.services.dashboard_service import (
    is_launched,
    latest_per_product,
    released_in,
    to_snapshot,
)

MAX_RECORDS = 50


def _refs(
    rows: Sequence[ProductMetric | Feature | RoadmapItem], table: str
) -> tuple[RecordRef, ...]:
    return tuple(RecordRef("product", table, str(r.id)) for r in rows[:MAX_RECORDS])


def _reading(
    code: str, value: float | None, key: str, records: tuple[RecordRef, ...],
    threshold_input: float | None = None,
) -> MetricReading:  # fmt: skip
    return MetricReading(
        code, value, key, threshold_input=threshold_input, records=records,
        status_reason=None if value is not None else "NO_DATA",
    )  # fmt: skip


def churn_increase(rows: Sequence[ProductMetric], last: str) -> float:
    """Largest BR-PRD-01-style relative increase among products at/above the floor."""
    prev = calc.previous_periods(last)
    by: dict[tuple[uuid.UUID, str], float] = {
        (r.product_id, r.period_key): float(r.churn_rate_pct) for r in rows
    }
    worst = 0.0
    for r in rows:
        if r.period_key != last or float(r.churn_rate_pct) < calc.CHURN_ANOMALY_FLOOR_PCT:
            continue
        base = calc.baseline([by.get((r.product_id, k)) for k in prev])
        change = calc.relative_change_pct(float(r.churn_rate_pct), base)
        worst = max(worst, change or 0.0)
    return worst


def _mau_of(rows: Sequence[ProductMetric], key: str, ids: set[uuid.UUID]) -> int | None:
    return calc.total_mau(
        [to_snapshot(r) for r in rows if r.period_key == key and r.product_id in ids]
    )


def _snapshot_readings(
    rows: Sequence[ProductMetric], launched: set[uuid.UUID], live: set[uuid.UUID], last: str
) -> list[MetricReading]:
    period_rows = [r for r in rows if r.period_key == last and r.product_id in launched]
    snaps = [to_snapshot(r) for r in period_rows]
    refs = _refs(period_rows, "product_metrics")
    mau = calc.total_mau(snaps)
    base = calc.baseline([_mau_of(rows, k, launched) for k in calc.previous_periods(last)])
    change = calc.relative_change_pct(mau, base)
    churn_up = churn_increase([r for r in rows if r.product_id in launched], last)
    latest = latest_per_product(rows, live, last)
    nps = calc.weighted([to_snapshot(r) for r in latest], "nps")
    return [
        _reading("METRIC-PRD-01", mau, last, refs, -change if change is not None else 0.0),
        _reading("METRIC-PRD-02", calc.worst_churn(snaps), last, refs, churn_up),
        _reading("METRIC-PRD-03", calc.weighted(snaps, "retention_30d_pct"), last, refs),
        _reading("METRIC-CUS-05", nps, last, _refs(latest, "product_metrics")),
    ]


@metric_provider("product")
async def compute(db: AsyncSession, as_of: date) -> list[MetricReading]:
    last = shift_month(month_key(as_of), -1)
    start, nxt = month_range(last)
    end = nxt - timedelta(days=1)
    products = list(await ProductRepository(db).all_live())
    launched = {p.id for p in products if is_launched(p)}
    live = {p.id for p in products}
    rows = [r for r in await MetricRepository(db).current_rows(max_period=last)
            if r.product_id in live]  # fmt: skip
    out = _snapshot_readings(rows, launched, live, last)

    all_items = [i for i in await RoadmapRepository(db).all_live() if i.product_id in live]
    quarter = [i for i in all_items if i.quarter == calc.quarter_key(end)]
    on_time = calc.roadmap_on_time_pct(
        [(i.status, i.planned_date, i.completed_at) for i in quarter], as_of
    )
    out.append(_reading("METRIC-PRD-04", on_time, last, _refs(quarter, "roadmap_items")))

    features = [f for f in await FeatureRepository(db).all_live() if f.product_id in live]
    released = released_in(features, await ReleaseRepository(db).all_live(), start, end)
    planned_items = {i.id for i in all_items
                     if i.planned_date is not None and start <= i.planned_date <= end}  # fmt: skip
    rel_ids = {f.id for f in released}
    planned = [f for f in features if f.id in rel_ids
               or (f.roadmap_item_id in planned_items and f.status != "deprecated")]  # fmt: skip
    attainment = calc.pct(len(released), len(planned))
    out.append(_reading("METRIC-PRD-05", attainment, last, _refs(planned, "features")))
    return out

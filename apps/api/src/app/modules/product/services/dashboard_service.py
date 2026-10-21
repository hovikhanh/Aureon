"""EP-90 product dashboard (FR-PRD-07, 10 §5) — computed on read until the metric store wires
`metrics[]` (DEC-200 pattern; `metrics: []` → pillar `no_data` for now).

Mapping (DEC-214): snapshot figures use each launched product's latest current snapshot with
`period_key ≤` the period's last month; `features_released` counts released features whose
release (else the feature's own `updated_at`) falls in the period; roadmap on-time uses the
quarter containing the period end, `dropped` excluded.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today
from app.core.deps import Principal
from app.modules.product.models import Feature, Product, ProductMetric, Release
from app.modules.product.repositories import (
    FeatureRepository,
    MetricRepository,
    ProductRepository,
    ReleaseRepository,
    RoadmapRepository,
)
from app.modules.product.schemas.metrics import (
    ChurnPoint,
    MauPoint,
    PeriodOut,
    ProductDashboardOut,
    ProductSummary,
)
from app.modules.product.services import calculations as calc

LAUNCHED_STAGES = frozenset({"launched", "growth", "mature"})
DEV_STAGES = frozenset({"idea", "development"})


def is_launched(p: Product) -> bool:
    return p.launched_at is not None or p.lifecycle_stage in LAUNCHED_STAGES


def to_snapshot(m: ProductMetric) -> calc.Snapshot:
    def f(v: object) -> float | None:
        return None if v is None else float(str(v))

    return calc.Snapshot(
        mau=m.mau, adoption_pct=f(m.adoption_rate_pct), churn_rate_pct=float(m.churn_rate_pct),
        retention_30d_pct=f(m.retention_30d_pct), nps=f(m.nps),
        arpu=m.arpu,
    )  # fmt: skip


def latest_per_product(
    rows: Sequence[ProductMetric], product_ids: set[uuid.UUID], last: str
) -> list[ProductMetric]:
    """Latest current snapshot (`period_key ≤ last`) of every product in `product_ids`."""
    latest: dict[uuid.UUID, ProductMetric] = {}
    for r in rows:  # rows ascending by period_key
        if r.product_id in product_ids and r.period_key <= last:
            latest[r.product_id] = r
    return list(latest.values())


def released_in(
    features: Sequence[Feature], releases: Sequence[Release], start: date, end: date
) -> list[Feature]:
    at = {r.id: r.released_at for r in releases}
    lo = datetime.combine(start, datetime.min.time(), tzinfo=UTC)
    hi = datetime.combine(end, datetime.max.time(), tzinfo=UTC)
    out = []
    for f in features:
        when = at.get(f.release_id) if f.release_id else None
        when = when or f.updated_at
        if f.status == "released" and when is not None and lo <= when <= hi:
            out.append(f)
    return out


class ProductDashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def today() -> date:
        return business_today()

    async def dashboard(self, user: Principal, period: str | None) -> ProductDashboardOut:
        today = self.today()
        p = calc.resolve_period(period, today)
        products = list(await ProductRepository(self.db).all_live())
        launched = {x.id for x in products if is_launched(x)}
        rows = await MetricRepository(self.db).current_rows(max_period=p.last_month)
        snaps = [to_snapshot(m) for m in latest_per_product(rows, launched, p.last_month)]
        arpu = calc.weighted(snaps, "arpu")
        feats = released_in(
            await FeatureRepository(self.db).all_live(),
            await ReleaseRepository(self.db).all_live(), p.start, p.end,
        )  # fmt: skip
        items = await RoadmapRepository(self.db).by_quarter(calc.quarter_key(p.end))
        summary = ProductSummary(
            products_total=len(products),
            products_active=sum(1 for x in products if x.status == "active"),
            products_in_dev=sum(1 for x in products if x.lifecycle_stage in DEV_STAGES),
            mau=calc.total_mau(snaps), adoption_pct=calc.weighted(snaps, "adoption_pct"),
            churn_rate_pct=calc.worst_churn(snaps),
            retention_30d_pct=calc.weighted(snaps, "retention_30d_pct"),
            nps=calc.weighted(snaps, "nps"), arpu=round(arpu) if arpu is not None else None,
            features_released=len(feats),
            roadmap_on_time_pct=calc.roadmap_on_time_pct(
                [(i.status, i.planned_date, i.completed_at) for i in items], today
            ),
        )  # fmt: skip
        live_ids = {x.id for x in products}
        mau_trend, churn_trend = [], []
        for key in calc.trend_keys(p.last_month):
            month = [
                to_snapshot(r) for r in rows if r.period_key == key and r.product_id in live_ids
            ]
            mau_trend.append(MauPoint(period_key=key, mau=calc.total_mau(month)))
            churn_trend.append(ChurnPoint(period_key=key, churn_rate_pct=calc.worst_churn(month)))
        metrics: list[dict[str, object]] = []  # METRIC-PRD-* from the metric store (T-220)
        return ProductDashboardOut(
            status=calc.pillar_status(str(m["status"]) for m in metrics),
            period=PeriodOut(key=p.key, type=p.type, start_date=p.start, end_date=p.end),
            summary=summary, metrics=metrics, mau_trend=mau_trend, churn_trend=churn_trend,
        )  # fmt: skip

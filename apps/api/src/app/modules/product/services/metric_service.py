"""EP-95 product metric snapshots (FR-PRD-05/06) + BR-PRD-01 churn anomaly.

Append-only (05 C5): numbers are never updated. A new snapshot for a period that already has a
current one supersedes it: the old row is first pointed at itself (frees the partial UQ
`(product_id, period_key) WHERE superseded_by_id IS NULL`, FK still valid), the new row is
inserted, then the old row is pointed at the new one — all in the caller's transaction.

BR-PRD-01 runs on every new snapshot against the current snapshots of the 3 previous months;
`EVT-product.metric_anomaly` is published at most once per (product, period) — a correction
of an already-reported period does not re-publish (DEC-213).
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import BusinessRuleError
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.product.models import ProductMetric
from app.modules.product.repositories import MetricRepository
from app.modules.product.schemas.metrics import MetricCreate, MetricOut
from app.modules.product.services import calculations as calc
from app.modules.product.services import scope
from app.modules.product.services.common import audit
from app.modules.product.services.product_service import ProductService


def _f(value: object) -> float | None:
    return None if value is None else float(str(value))


def metric_out(m: ProductMetric) -> MetricOut:
    return MetricOut(
        id=m.id, product_id=m.product_id, period_key=m.period_key, mau=m.mau, dau=m.dau,
        adoption_pct=_f(m.adoption_rate_pct), churn_rate_pct=float(m.churn_rate_pct),
        retention_30d_pct=_f(m.retention_30d_pct), nps=_f(m.nps), arpu=m.arpu,
        currency=m.currency, superseded_by_id=m.superseded_by_id,
        source_document_id=m.source_document_id, created_at=m.created_at,
    )  # fmt: skip


class MetricService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.metrics = MetricRepository(db)
        self.products = ProductService(db)

    async def list_metrics(
        self, user: Principal, product_id: uuid.UUID, page: PageParams
    ) -> tuple[list[MetricOut], int]:
        """Current snapshots of one product (superseded rows are history, not listed)."""
        await self.products.require_product(product_id)
        items, total = await self.metrics.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters={"product_id": product_id},
            where=[ProductMetric.superseded_by_id.is_(None)],
        )  # fmt: skip
        return [metric_out(m) for m in items], total

    async def create_metric(
        self, user: Principal, product_id: uuid.UUID, body: MetricCreate
    ) -> MetricOut:
        scope.require_writer(user)
        await self.products.require_product(product_id)
        if body.dau is not None and body.dau > body.mau:
            raise BusinessRuleError("dau must be <= mau", details={"field": "dau"})
        old = await self.metrics.current_for(product_id, body.period_key)
        before = metric_out(old) if old is not None else None
        if old is not None:
            old.superseded_by_id = old.id
            await self.db.flush()
        new = ProductMetric(
            product_id=product_id, period_key=body.period_key, mau=body.mau, dau=body.dau,
            adoption_rate_pct=body.adoption_pct, churn_rate_pct=body.churn_rate_pct,
            retention_30d_pct=body.retention_30d_pct, nps=body.nps, arpu=body.arpu,
            currency=body.currency, source_document_id=body.source_document_id,
        )  # fmt: skip
        self.db.add(new)
        await self.db.flush()
        await self.db.refresh(new)
        out = metric_out(new)
        await audit(self.db, "product.metric_create", "product_metrics", new, after=out)
        if old is not None:
            old.superseded_by_id = new.id
            await self.db.flush()
            await audit(self.db, "product.metric_supersede", "product_metrics", old,
                        before, metric_out(old))  # fmt: skip
        await self._check_anomaly(new)
        return out

    async def _check_anomaly(self, m: ProductMetric) -> None:
        prev = calc.previous_periods(m.period_key)
        rows = await self.metrics.current_rows(product_id=m.product_id, max_period=prev[-1])
        by_period = {r.period_key: float(r.churn_rate_pct) for r in rows}
        base = calc.baseline([by_period.get(k) for k in prev])
        current = float(m.churn_rate_pct)
        if not calc.is_churn_anomaly(current, base):
            return
        if m.period_key in await self.metrics.anomaly_periods(m.product_id):
            return
        await publish_in_tx(
            self.db, event_type="product.metric_anomaly", producer="product",
            aggregate_schema="product", aggregate_table="products", aggregate_id=m.product_id,
            payload={"product_metric_id": str(m.id), "product_id": str(m.product_id),
                     "metric": "churn_rate_pct",
                     "value": current, "baseline": calc.round1(base)},
        )  # fmt: skip

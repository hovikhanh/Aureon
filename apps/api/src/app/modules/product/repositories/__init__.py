"""Product repositories — only `product` services use them (DEC-125)."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select

from app.core.base_repository import BaseRepository
from app.core.events.envelope import OUTBOX
from app.modules.product.models import Feature, Product, ProductMetric, Release, RoadmapItem


class ProductRepository(BaseRepository[Product]):
    model = Product

    async def by_code(self, code: str) -> Product | None:
        stmt = select(Product).where(Product.code == code).limit(1)  # UQ spans deleted rows
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def has_open_work(self, product_id: uuid.UUID) -> bool:
        """05 §5.4: features `in_progress` or releases `planned/in_progress` block delete."""
        feats = select(Feature.id).where(
            Feature.product_id == product_id,
            Feature.deleted_at.is_(None),
            Feature.status == "in_progress",
        )
        rels = select(Release.id).where(
            Release.product_id == product_id,
            Release.deleted_at.is_(None),
            Release.status.in_(("planned", "in_progress")),
        )
        return bool((await self.db.execute(select(feats.exists() | rels.exists()))).scalar_one())

    async def all_live(self) -> Sequence[Product]:
        return (await self.db.execute(self._live())).scalars().all()


class FeatureRepository(BaseRepository[Feature]):
    model = Feature

    async def all_live(self) -> Sequence[Feature]:
        return (await self.db.execute(self._live())).scalars().all()


class RoadmapRepository(BaseRepository[RoadmapItem]):
    model = RoadmapItem

    async def all_live(self) -> Sequence[RoadmapItem]:
        return (await self.db.execute(self._live())).scalars().all()

    async def by_quarter(self, quarter: str) -> Sequence[RoadmapItem]:
        stmt = self._live().where(RoadmapItem.quarter == quarter)
        return (await self.db.execute(stmt)).scalars().all()


class ReleaseRepository(BaseRepository[Release]):
    model = Release

    async def by_version(self, product_id: uuid.UUID, release_version: str) -> Release | None:
        stmt = select(Release).where(
            Release.product_id == product_id, Release.release_version == release_version
        )
        return (await self.db.execute(stmt.limit(1))).scalar_one_or_none()

    async def all_live(self) -> Sequence[Release]:
        return (await self.db.execute(self._live())).scalars().all()


class MetricRepository(BaseRepository[ProductMetric]):
    model = ProductMetric

    def _current(self) -> Any:
        return select(ProductMetric).where(ProductMetric.superseded_by_id.is_(None))

    async def current_for(self, product_id: uuid.UUID, period_key: str) -> ProductMetric | None:
        stmt = self._current().where(
            ProductMetric.product_id == product_id, ProductMetric.period_key == period_key
        )
        return (await self.db.execute(stmt.with_for_update())).scalar_one_or_none()

    async def current_rows(
        self, *, product_id: uuid.UUID | None = None, max_period: str | None = None
    ) -> Sequence[ProductMetric]:
        """Current (not superseded) snapshots, ascending by `period_key`."""
        stmt = self._current()
        if product_id is not None:
            stmt = stmt.where(ProductMetric.product_id == product_id)
        if max_period is not None:
            stmt = stmt.where(ProductMetric.period_key <= max_period)
        stmt = stmt.order_by(ProductMetric.period_key, ProductMetric.id)
        return (await self.db.execute(stmt)).scalars().all()

    async def anomaly_periods(self, product_id: uuid.UUID) -> set[str]:
        """Periods of the snapshots already reported by `product.metric_anomaly` (outbox)."""
        ids = select(OUTBOX.c.payload["product_metric_id"].astext).where(
            OUTBOX.c.event_type == "product.metric_anomaly",
            OUTBOX.c.aggregate_id == product_id,
        )
        rows = (await self.db.execute(ids)).all()
        uuids = [uuid.UUID(r[0]) for r in rows if r[0]]
        if not uuids:
            return set()
        stmt = select(ProductMetric.period_key).where(ProductMetric.id.in_(uuids))
        return {r[0] for r in (await self.db.execute(stmt)).all()}

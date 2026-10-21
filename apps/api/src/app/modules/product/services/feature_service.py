"""EP-92 features — → `released` publishes `EVT-product.feature_released` (FR-PRD-02)."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import BusinessRuleError, NotFoundError
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.product.models import Feature
from app.modules.product.repositories import (
    FeatureRepository,
    ProductRepository,
    ReleaseRepository,
    RoadmapRepository,
)
from app.modules.product.schemas import FeatureCreate, FeatureOut, FeatureUpdate
from app.modules.product.services import scope
from app.modules.product.services.common import audit, feature_out, uid
from app.modules.product.services.product_service import reject_nulls


class FeatureService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.features = FeatureRepository(db)
        self.products = ProductRepository(db)
        self.releases = ReleaseRepository(db)
        self.roadmap = RoadmapRepository(db)

    async def list_features(
        self, user: Principal, page: PageParams, **filters: Any
    ) -> tuple[list[FeatureOut], int]:
        scope.require_reader(user)
        items, total = await self.features.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters={k: v for k, v in filters.items() if v is not None},
        )  # fmt: skip
        return [feature_out(f) for f in items], total

    async def get_feature(self, user: Principal, id_: uuid.UUID) -> Feature:
        scope.require_reader(user)
        obj = await self.features.get(id_)
        if obj is None:
            raise NotFoundError("feature not found")
        return obj

    async def _check_links(
        self, product_id: uuid.UUID, release_id: uuid.UUID | None, roadmap_id: uuid.UUID | None
    ) -> None:
        if await self.products.get(product_id) is None:
            raise BusinessRuleError("product does not exist", details={"field": "product_id"})
        rel = await self.releases.get(release_id) if release_id else None
        if release_id and (rel is None or rel.product_id != product_id):
            raise BusinessRuleError(
                "release not found for this product", details={"field": "release_id"}
            )
        item = await self.roadmap.get(roadmap_id) if roadmap_id else None
        if roadmap_id and (item is None or item.product_id != product_id):
            raise BusinessRuleError(
                "roadmap item not found for this product", details={"field": "roadmap_item_id"}
            )

    async def _released(self, f: Feature) -> None:
        """05 §5.3 payload: `feature_id`, `product_id`, `release_id` — ids only (10 §8.1)."""
        await publish_in_tx(
            self.db, event_type="product.feature_released", producer="product",
            aggregate_schema="product", aggregate_table="features", aggregate_id=f.id,
            payload={"feature_id": str(f.id), "product_id": str(f.product_id),
                     "release_id": uid(f.release_id)},
        )  # fmt: skip

    async def create_feature(self, user: Principal, body: FeatureCreate) -> FeatureOut:
        scope.require_writer(user)
        await self._check_links(body.product_id, body.release_id, body.roadmap_item_id)
        obj = Feature(**body.model_dump(), source="MANUAL", created_by=user.user_id)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        out = feature_out(obj)
        await audit(self.db, "product.feature_create", "features", obj, after=out)
        if obj.status == "released":
            await self._released(obj)
        return out

    async def update_feature(
        self, user: Principal, id_: uuid.UUID, body: FeatureUpdate, expected: int
    ) -> FeatureOut:
        scope.require_writer(user)
        obj = await self.get_feature(user, id_)
        before = feature_out(obj)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        reject_nulls(data, ("name", "status"))
        await self._check_links(obj.product_id, data.get("release_id"), data.get("roadmap_item_id"))
        was_released = obj.status == "released"
        await self.features.update(obj, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(obj)
        out = feature_out(obj)
        await audit(self.db, "product.feature_update", "features", obj, before, out)
        if obj.status == "released" and not was_released:
            await self._released(obj)
        return out

    async def delete_feature(self, user: Principal, id_: uuid.UUID) -> None:
        scope.require_writer(user)
        obj = await self.get_feature(user, id_)
        before = feature_out(obj)
        obj.updated_by = user.user_id
        await self.features.soft_delete(obj)
        await audit(self.db, "product.feature_delete", "features", obj, before=before)

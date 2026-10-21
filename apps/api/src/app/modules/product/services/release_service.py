"""EP-94 releases (FR-PRD-04). `release_version` UQ per product (DEC-154) → `409`.

The product's first release reaching `released` publishes `EVT-product.product_launched`
once: `products.launched_at` is stamped (it is the "already launched" marker) and an
`idea`/`development` lifecycle moves to `launched` (05 §4.5, DEC-211).
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import BusinessRuleError, DuplicateResourceError, NotFoundError
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.product.models import Release
from app.modules.product.repositories import ProductRepository, ReleaseRepository
from app.modules.product.schemas import ReleaseCreate, ReleaseOut, ReleaseUpdate
from app.modules.product.services import scope
from app.modules.product.services.common import audit, flush_unique, product_out, release_out
from app.modules.product.services.product_service import reject_nulls

PRE_LAUNCH_STAGES = frozenset({"idea", "development"})


class ReleaseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.releases = ReleaseRepository(db)
        self.products = ProductRepository(db)

    async def list_releases(
        self, user: Principal, page: PageParams, **filters: Any
    ) -> tuple[list[ReleaseOut], int]:
        scope.require_reader(user)
        items, total = await self.releases.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters={k: v for k, v in filters.items() if v is not None},
        )  # fmt: skip
        return [release_out(r) for r in items], total

    async def get_release(self, user: Principal, id_: uuid.UUID) -> Release:
        scope.require_reader(user)
        obj = await self.releases.get(id_)
        if obj is None:
            raise NotFoundError("release not found")
        return obj

    async def _check_version(
        self, product_id: uuid.UUID, version: str, exclude: uuid.UUID | None = None
    ) -> None:
        dup = await self.releases.by_version(product_id, version)
        if dup is not None and dup.id != exclude:
            raise DuplicateResourceError(
                "release_version already exists for this product",
                details={"field": "release_version"},
            )

    async def _launch_if_first(self, rel: Release) -> None:
        product = await self.products.get(rel.product_id)
        if product is None or product.launched_at is not None:
            return
        before = product_out(product)
        released = rel.released_at or datetime.now(UTC)
        values: dict[str, Any] = {"launched_at": released.date()}
        if product.lifecycle_stage in PRE_LAUNCH_STAGES:
            values["lifecycle_stage"] = "launched"
        await self.products.update(product, **values)
        await self.db.refresh(product)
        await audit(self.db, "product.product_launch", "products", product, before,
                    product_out(product))  # fmt: skip
        await publish_in_tx(
            self.db, event_type="product.product_launched", producer="product",
            aggregate_schema="product", aggregate_table="products", aggregate_id=product.id,
            payload={"product_id": str(product.id),
                     "launched_at": values["launched_at"].isoformat()},
        )  # fmt: skip

    async def create_release(self, user: Principal, body: ReleaseCreate) -> ReleaseOut:
        scope.require_writer(user)
        if await self.products.get(body.product_id) is None:
            raise BusinessRuleError("product does not exist", details={"field": "product_id"})
        await self._check_version(body.product_id, body.release_version)
        obj = Release(**body.model_dump(), source="MANUAL", created_by=user.user_id)
        if obj.status == "released" and obj.released_at is None:
            obj.released_at = datetime.now(UTC)
        self.db.add(obj)
        await flush_unique(self.db, "release_version")
        await self.db.refresh(obj)
        out = release_out(obj)
        await audit(self.db, "product.release_create", "releases", obj, after=out)
        if obj.status == "released":
            await self._launch_if_first(obj)
        return out

    async def update_release(
        self, user: Principal, id_: uuid.UUID, body: ReleaseUpdate, expected: int
    ) -> ReleaseOut:
        scope.require_writer(user)
        obj = await self.get_release(user, id_)
        before = release_out(obj)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        reject_nulls(data, ("release_version", "status"))
        if "release_version" in data:
            await self._check_version(obj.product_id, data["release_version"], obj.id)
        becomes_released = data.get("status") == "released" and obj.status != "released"
        if becomes_released and obj.released_at is None and data.get("released_at") is None:
            data["released_at"] = datetime.now(UTC)
        await self.releases.update(obj, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(obj)
        out = release_out(obj)
        await audit(self.db, "product.release_update", "releases", obj, before, out)
        if becomes_released:
            await self._launch_if_first(obj)
        return out

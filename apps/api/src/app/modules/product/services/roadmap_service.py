"""EP-93 roadmap items (FR-PRD-03). API `target_date` ↔ column `planned_date` (DEC-210).

→ `done` stamps `completed_at` (business today unless sent) — METRIC-PRD-04 needs it.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today
from app.core.deps import Principal
from app.core.errors import BusinessRuleError, NotFoundError
from app.core.pagination import PageParams
from app.modules.product.models import RoadmapItem
from app.modules.product.repositories import ProductRepository, RoadmapRepository
from app.modules.product.schemas import RoadmapCreate, RoadmapOut, RoadmapUpdate
from app.modules.product.services import scope
from app.modules.product.services.common import ROADMAP_API_TO_DB, audit, roadmap_out
from app.modules.product.services.product_service import reject_nulls


class RoadmapService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.items = RoadmapRepository(db)
        self.products = ProductRepository(db)

    async def list_items(
        self, user: Principal, page: PageParams, **filters: Any
    ) -> tuple[list[RoadmapOut], int]:
        scope.require_reader(user)
        sort_by = ROADMAP_API_TO_DB.get(page.sort_by, page.sort_by)
        items, total = await self.items.list_page(
            limit=page.limit, offset=page.offset, sort_by=sort_by, order=page.order,
            filters={k: v for k, v in filters.items() if v is not None},
        )  # fmt: skip
        return [roadmap_out(r) for r in items], total

    async def get_item(self, user: Principal, id_: uuid.UUID) -> RoadmapItem:
        scope.require_reader(user)
        obj = await self.items.get(id_)
        if obj is None:
            raise NotFoundError("roadmap item not found")
        return obj

    async def create_item(self, user: Principal, body: RoadmapCreate) -> RoadmapOut:
        scope.require_writer(user)
        if await self.products.get(body.product_id) is None:
            raise BusinessRuleError("product does not exist", details={"field": "product_id"})
        obj = RoadmapItem(
            product_id=body.product_id, title=body.title, quarter=body.quarter,
            planned_date=body.target_date, status=body.status,
            completed_at=business_today() if body.status == "done" else None,
            source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        out = roadmap_out(obj)
        await audit(self.db, "product.roadmap_item_create", "roadmap_items", obj, after=out)
        return out

    async def update_item(
        self, user: Principal, id_: uuid.UUID, body: RoadmapUpdate, expected: int
    ) -> RoadmapOut:
        scope.require_writer(user)
        obj = await self.get_item(user, id_)
        before = roadmap_out(obj)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        reject_nulls(data, ("title", "quarter", "status"))
        status = data.get("status", obj.status)
        if status == "done" and obj.completed_at is None and data.get("completed_at") is None:
            data["completed_at"] = business_today()
        if status != "done" and "status" in data:
            data["completed_at"] = None
        values = {ROADMAP_API_TO_DB.get(k, k): v for k, v in data.items()}
        await self.items.update(obj, expected_version=expected, updated_by=user.user_id, **values)
        await self.db.refresh(obj)
        out = roadmap_out(obj)
        await audit(self.db, "product.roadmap_item_update", "roadmap_items", obj, before, out)
        return out

    async def delete_item(self, user: Principal, id_: uuid.UUID) -> None:
        scope.require_writer(user)
        obj = await self.get_item(user, id_)
        before = roadmap_out(obj)
        obj.updated_by = user.user_id
        await self.items.soft_delete(obj)
        await audit(self.db, "product.roadmap_item_delete", "roadmap_items", obj, before=before)

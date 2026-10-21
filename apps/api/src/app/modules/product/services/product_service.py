"""Public service interface of `product` — the only entry point for other modules.

EP-91 products. Every mutation writes `ENT-AuditLog` in the caller's transaction (10 §1.8);
the route commits. Features / roadmap / releases / metrics live in sibling services.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import BusinessRuleError, DuplicateResourceError, NotFoundError
from app.core.pagination import PageParams
from app.modules.product.models import Product
from app.modules.product.repositories import ProductRepository
from app.modules.product.schemas import ProductCreate, ProductOut, ProductUpdate
from app.modules.product.services import scope
from app.modules.product.services.common import audit, flush_unique, product_out

NOT_NULL = ("code", "name", "status", "lifecycle_stage", "owner_id")


def reject_nulls(data: dict[str, Any], keys: tuple[str, ...]) -> None:
    for key in keys:
        if key in data and data[key] is None:
            raise BusinessRuleError(f"{key} cannot be null", details={"field": key})


class ProductService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.products = ProductRepository(db)

    async def list_products(
        self, user: Principal, page: PageParams, **filters: Any
    ) -> tuple[list[ProductOut], int]:
        scope.require_reader(user)
        items, total = await self.products.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters={k: v for k, v in filters.items() if v is not None},
        )  # fmt: skip
        return [product_out(p) for p in items], total

    async def get_product(self, user: Principal, id_: uuid.UUID) -> Product:
        scope.require_reader(user)
        return await self.require_product(id_)

    async def require_product(self, id_: uuid.UUID) -> Product:
        obj = await self.products.get(id_)
        if obj is None:
            raise NotFoundError("product not found")
        return obj

    async def _check_code(self, code: str, exclude: uuid.UUID | None = None) -> None:
        dup = await self.products.by_code(code)
        if dup is not None and dup.id != exclude:
            raise DuplicateResourceError("product code already exists", details={"field": "code"})

    async def create_product(self, user: Principal, body: ProductCreate) -> ProductOut:
        scope.require_writer(user)
        await self._check_code(body.code)
        obj = Product(**body.model_dump(), source="MANUAL", created_by=user.user_id)
        self.db.add(obj)
        await flush_unique(self.db, "product code")
        await self.db.refresh(obj)
        out = product_out(obj)
        await audit(self.db, "product.product_create", "products", obj, after=out)
        return out

    async def update_product(
        self, user: Principal, id_: uuid.UUID, body: ProductUpdate, expected: int
    ) -> ProductOut:
        scope.require_writer(user)
        obj = await self.require_product(id_)
        before = product_out(obj)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        reject_nulls(data, NOT_NULL)
        if "code" in data:
            await self._check_code(data["code"], obj.id)
        await self.products.update(obj, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(obj)
        out = product_out(obj)
        await audit(self.db, "product.product_update", "products", obj, before, out)
        return out

    async def delete_product(self, user: Principal, id_: uuid.UUID) -> None:
        """05 §5.4: blocked while work is open; a launched product goes `sunset` + soft delete."""
        scope.require_writer(user)
        obj = await self.require_product(id_)
        if await self.products.has_open_work(obj.id):
            raise BusinessRuleError(
                "product still has in-progress features or open releases",
                details={"product_id": str(obj.id), "rule": "FR-PRD-01"},
            )
        before = product_out(obj)
        if obj.launched_at is not None:
            obj.lifecycle_stage, obj.status = "sunset", "retired"
        obj.updated_by = user.user_id
        await self.products.soft_delete(obj)
        await audit(self.db, "product.product_delete", "products", obj, before=before)

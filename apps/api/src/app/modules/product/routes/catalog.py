"""EP-91 products, EP-92 features (10 §3.9, §4.9). One permission per route, `Idem` on
create, `IfMatch` + body `version` on PATCH, `Page` on lists, commit at the end."""

import uuid
from typing import Annotated, Any

from fastapi import Depends, Query, Response

from app.core.concurrency import IfMatch, expected_version
from app.core.envelope import Page
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.modules.product.routes.deps import Db, Reader, Writer, router
from app.modules.product.schemas import (
    FeatureCreate,
    FeatureOut,
    FeatureStatus,
    FeatureUpdate,
    LifecycleStage,
    ProductCreate,
    ProductOut,
    ProductStatus,
    ProductUpdate,
)
from app.modules.product.services.common import feature_out, product_out
from app.modules.product.services.feature_service import FeatureService
from app.modules.product.services.product_service import ProductService


# ---------- EP-91 products ----------
@router.get("/product/products", response_model=list[ProductOut])
async def list_products(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("code", "name", "updated_at"))],
    status: ProductStatus | None = None, lifecycle_stage: LifecycleStage | None = None,
    owner_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    items, total = await ProductService(db).list_products(
        user, page, status=status, lifecycle_stage=lifecycle_stage, owner_id=owner_id
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/product/products", response_model=ProductOut, status_code=201)
async def create_product(body: ProductCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ProductOut.model_validate(hit)
    out = await ProductService(db).create_product(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/product/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return product_out(await ProductService(db).get_product(user, product_id))


@router.patch("/product/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: uuid.UUID, body: ProductUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await ProductService(db).update_product(user, product_id, body, exp)
    await db.commit()
    return out


@router.delete("/product/products/{product_id}", status_code=204, response_class=Response)
async def delete_product(product_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await ProductService(db).delete_product(user, product_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-92 features ----------
@router.get("/product/features", response_model=list[FeatureOut])
async def list_features(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("name", "updated_at"))],
    product_id: uuid.UUID | None = None, status: FeatureStatus | None = None,
    release_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Any:  # fmt: skip
    items, total = await FeatureService(db).list_features(
        user, page, product_id=product_id, status=status, release_id=release_id
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/product/features", response_model=FeatureOut, status_code=201)
async def create_feature(body: FeatureCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return FeatureOut.model_validate(hit)
    out = await FeatureService(db).create_feature(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/product/features/{feature_id}", response_model=FeatureOut)
async def get_feature(feature_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return feature_out(await FeatureService(db).get_feature(user, feature_id))


@router.patch("/product/features/{feature_id}", response_model=FeatureOut)
async def update_feature(
    feature_id: uuid.UUID, body: FeatureUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await FeatureService(db).update_feature(user, feature_id, body, exp)
    await db.commit()
    return out


@router.delete("/product/features/{feature_id}", status_code=204, response_class=Response)
async def delete_feature(feature_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await FeatureService(db).delete_feature(user, feature_id)
    await db.commit()
    return Response(status_code=204)

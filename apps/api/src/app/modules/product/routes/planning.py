"""EP-93 roadmap items (L C R U D), EP-94 releases (L C R U — no delete, 10 §3.9)."""

import uuid
from typing import Annotated, Any

from fastapi import Depends, Query, Response

from app.core.concurrency import IfMatch, expected_version
from app.core.envelope import Page
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.modules.product.routes.deps import Db, Reader, Writer, router
from app.modules.product.schemas import (
    QUARTER_PATTERN,
    ReleaseCreate,
    ReleaseOut,
    ReleaseStatus,
    ReleaseUpdate,
    RoadmapCreate,
    RoadmapOut,
    RoadmapStatus,
    RoadmapUpdate,
)
from app.modules.product.services.common import release_out, roadmap_out
from app.modules.product.services.release_service import ReleaseService
from app.modules.product.services.roadmap_service import RoadmapService


# ---------- EP-93 roadmap items ----------
@router.get("/product/roadmap-items", response_model=list[RoadmapOut])
async def list_roadmap_items(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("quarter", "target_date", "updated_at"))],
    product_id: uuid.UUID | None = None, status: RoadmapStatus | None = None,
    quarter: Annotated[str | None, Query(pattern=QUARTER_PATTERN)] = None,
) -> Any:  # fmt: skip
    items, total = await RoadmapService(db).list_items(
        user, page, product_id=product_id, status=status, quarter=quarter
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/product/roadmap-items", response_model=RoadmapOut, status_code=201)
async def create_roadmap_item(body: RoadmapCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return RoadmapOut.model_validate(hit)
    out = await RoadmapService(db).create_item(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/product/roadmap-items/{item_id}", response_model=RoadmapOut)
async def get_roadmap_item(item_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return roadmap_out(await RoadmapService(db).get_item(user, item_id))


@router.patch("/product/roadmap-items/{item_id}", response_model=RoadmapOut)
async def update_roadmap_item(
    item_id: uuid.UUID, body: RoadmapUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await RoadmapService(db).update_item(user, item_id, body, exp)
    await db.commit()
    return out


@router.delete("/product/roadmap-items/{item_id}", status_code=204, response_class=Response)
async def delete_roadmap_item(item_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await RoadmapService(db).delete_item(user, item_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-94 releases ----------
@router.get("/product/releases", response_model=list[ReleaseOut])
async def list_releases(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("released_at", "release_version"))],
    product_id: uuid.UUID | None = None, status: ReleaseStatus | None = None,
) -> Any:  # fmt: skip
    items, total = await ReleaseService(db).list_releases(
        user, page, product_id=product_id, status=status
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/product/releases", response_model=ReleaseOut, status_code=201)
async def create_release(body: ReleaseCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ReleaseOut.model_validate(hit)
    out = await ReleaseService(db).create_release(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/product/releases/{release_id}", response_model=ReleaseOut)
async def get_release(release_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return release_out(await ReleaseService(db).get_release(user, release_id))


@router.patch("/product/releases/{release_id}", response_model=ReleaseOut)
async def update_release(
    release_id: uuid.UUID, body: ReleaseUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await ReleaseService(db).update_release(user, release_id, body, exp)
    await db.commit()
    return out

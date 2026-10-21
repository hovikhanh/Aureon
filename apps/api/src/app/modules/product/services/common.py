"""Shared helpers for the product services: DTO mappers (DEC-210), audit, unique flush."""

import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.base_model import Base
from app.core.errors import DuplicateResourceError
from app.modules.product.models import Feature, Product, Release, RoadmapItem
from app.modules.product.schemas import FeatureOut, ProductOut, ReleaseOut, RoadmapOut

# 10 field name → 05 column (DEC-210)
ROADMAP_API_TO_DB = {"target_date": "planned_date"}


def _base(o: Any) -> dict[str, Any]:
    return {"id": o.id, "version": o.version, "created_at": o.created_at,
            "updated_at": o.updated_at}  # fmt: skip


def product_out(p: Product) -> ProductOut:
    return ProductOut(
        **_base(p), code=p.code, name=p.name, description=p.description, status=p.status,
        lifecycle_stage=p.lifecycle_stage, target_launch_date=p.target_launch_date,
        launched_at=p.launched_at, owner_id=p.owner_id,
    )  # fmt: skip


def feature_out(f: Feature) -> FeatureOut:
    return FeatureOut(
        **_base(f), product_id=f.product_id, name=f.name, status=f.status,
        release_id=f.release_id, roadmap_item_id=f.roadmap_item_id,
    )  # fmt: skip


def roadmap_out(r: RoadmapItem) -> RoadmapOut:
    return RoadmapOut(
        **_base(r), product_id=r.product_id, title=r.title, quarter=r.quarter,
        target_date=r.planned_date, completed_at=r.completed_at, status=r.status,
    )  # fmt: skip


def release_out(r: Release) -> ReleaseOut:
    return ReleaseOut(
        **_base(r), product_id=r.product_id, release_version=r.release_version,
        status=r.status, released_at=r.released_at, release_notes=r.release_notes,
    )  # fmt: skip


async def audit(
    db: AsyncSession, action: str, table: str, obj: Base,
    before: BaseModel | None = None, after: BaseModel | None = None,
) -> None:  # fmt: skip
    await record_audit(
        db, action=action, target_schema="product", target_table=table,
        target_id=getattr(obj, "id", None),
        before=before.model_dump(mode="json") if before is not None else None,
        after=after.model_dump(mode="json") if after is not None else None,
    )  # fmt: skip


async def flush_unique(db: AsyncSession, what: str) -> None:
    try:
        await db.flush()
    except IntegrityError as exc:  # concurrent insert won the UQ race
        raise DuplicateResourceError(f"{what} already exists") from exc


def uid(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None

"""Product API DTOs (10 §4.9 EP-91..94). Enum values and columns follow 05 (DEC-210).

10 ↔ 05 mapping (service side, never the DB): product/feature/roadmap `status` use the 05 enums
(`active|paused|retired`, `planned|in_progress|released|deprecated`, roadmap adds `delayed`);
roadmap `target_date` ↔ column `planned_date`. Fields beyond the 10 "main fields" column carry
the exact 05 column name.
"""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ProductStatus = Literal["active", "paused", "retired"]
LifecycleStage = Literal["idea", "development", "launched", "growth", "mature", "sunset"]
FeatureStatus = Literal["planned", "in_progress", "released", "deprecated"]
RoadmapStatus = Literal["planned", "in_progress", "done", "delayed", "dropped"]
ReleaseStatus = Literal["planned", "in_progress", "released", "rolled_back"]
QUARTER_PATTERN = r"^\d{4}-Q[1-4]$"
CODE_PATTERN = r"^[A-Za-z0-9_.-]+$"


def _opt(**kw: Any) -> Any:
    return Field(default=None, **kw)


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Patch(_In):
    """PATCH bodies: only sent fields are applied (`model_dump(exclude_unset=True)`)."""

    version: int | None = None


# ---------- EP-91 products ----------
class ProductCreate(_In):
    code: str = Field(min_length=1, max_length=50, pattern=CODE_PATTERN)
    name: str = Field(min_length=1, max_length=300)
    description: str | None = _opt(max_length=4000)
    status: ProductStatus = "active"
    lifecycle_stage: LifecycleStage = "idea"
    target_launch_date: date | None = None
    owner_id: uuid.UUID


class ProductUpdate(_Patch):
    code: str | None = _opt(min_length=1, max_length=50, pattern=CODE_PATTERN)
    name: str | None = _opt(min_length=1, max_length=300)
    description: str | None = _opt(max_length=4000)
    status: ProductStatus | None = None
    lifecycle_stage: LifecycleStage | None = None
    target_launch_date: date | None = None
    owner_id: uuid.UUID | None = None


class ProductOut(_Out):
    code: str
    name: str
    description: str | None
    status: ProductStatus
    lifecycle_stage: LifecycleStage
    target_launch_date: date | None
    launched_at: date | None
    owner_id: uuid.UUID


# ---------- EP-92 features ----------
class FeatureCreate(_In):
    product_id: uuid.UUID
    name: str = Field(min_length=1, max_length=300)
    status: FeatureStatus = "planned"
    release_id: uuid.UUID | None = None
    roadmap_item_id: uuid.UUID | None = None


class FeatureUpdate(_Patch):
    name: str | None = _opt(min_length=1, max_length=300)
    status: FeatureStatus | None = None
    release_id: uuid.UUID | None = None
    roadmap_item_id: uuid.UUID | None = None


class FeatureOut(_Out):
    product_id: uuid.UUID
    name: str
    status: FeatureStatus
    release_id: uuid.UUID | None
    roadmap_item_id: uuid.UUID | None


# ---------- EP-93 roadmap items ----------
class RoadmapCreate(_In):
    product_id: uuid.UUID
    title: str = Field(min_length=1, max_length=300)
    quarter: str = Field(pattern=QUARTER_PATTERN)
    target_date: date | None = None
    status: RoadmapStatus = "planned"


class RoadmapUpdate(_Patch):
    title: str | None = _opt(min_length=1, max_length=300)
    quarter: str | None = _opt(pattern=QUARTER_PATTERN)
    target_date: date | None = None
    status: RoadmapStatus | None = None
    completed_at: date | None = None


class RoadmapOut(_Out):
    product_id: uuid.UUID
    title: str
    quarter: str
    target_date: date | None
    completed_at: date | None
    status: RoadmapStatus


# ---------- EP-94 releases ----------
class ReleaseCreate(_In):
    product_id: uuid.UUID
    release_version: str = Field(min_length=1, max_length=50)
    status: ReleaseStatus = "planned"
    released_at: datetime | None = None
    release_notes: str | None = _opt(max_length=8000)


class ReleaseUpdate(_Patch):
    release_version: str | None = _opt(min_length=1, max_length=50)
    status: ReleaseStatus | None = None
    released_at: datetime | None = None
    release_notes: str | None = _opt(max_length=8000)


class ReleaseOut(_Out):
    product_id: uuid.UUID
    release_version: str
    status: ReleaseStatus
    released_at: datetime | None
    release_notes: str | None

"""Schema `product` — 5 tables (05 §4.5). Column groups follow 05 §2.1."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, Date, Index, Integer, Numeric, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BusinessModel, LogModel
from app.core.columns import currency, fk, money, pct, schema_args, sr, ts, txt
from app.core.enums import pg_enum

S = "product"

# ---------- module-owned enums (05 §6) ----------
PRODUCT_STATUS = pg_enum(S, "product_status", "active", "paused", "retired")
LIFECYCLE_STAGE = pg_enum(
    S, "lifecycle_stage", "idea", "development", "launched", "growth", "mature", "sunset"
)
FEATURE_STATUS = pg_enum(S, "feature_status", "planned", "in_progress", "released", "deprecated")
ROADMAP_STATUS = pg_enum(
    S, "roadmap_status", "planned", "in_progress", "done", "delayed", "dropped"
)
RELEASE_STATUS = pg_enum(S, "release_status", "planned", "in_progress", "released", "rolled_back")

MODULE_ENUMS: tuple[ENUM, ...] = (
    PRODUCT_STATUS,
    LIFECYCLE_STAGE,
    FEATURE_STATUS,
    ROADMAP_STATUS,
    RELEASE_STATUS,
)


class Product(BusinessModel):
    """ENT-Product — first release emits EVT-product.product_launched."""

    __tablename__ = "products"
    __table_args__ = schema_args(S)

    code: Mapped[str] = txt(unique=True)
    name: Mapped[str] = txt()
    description: Mapped[str | None] = txt(nullable=True)
    status: Mapped[str] = mapped_column(PRODUCT_STATUS, nullable=False)
    lifecycle_stage: Mapped[str] = mapped_column(LIFECYCLE_STAGE, nullable=False)
    target_launch_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    launched_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner_id: Mapped[uuid.UUID] = sr(nullable=False)


class RoadmapItem(BusinessModel):
    """ENT-RoadmapItem — `quarter` is `YYYY-Qn` (METRIC-PRD-04)."""

    __tablename__ = "roadmap_items"
    __table_args__ = schema_args(S)

    product_id: Mapped[uuid.UUID] = fk(f"{S}.products.id")
    title: Mapped[str] = txt()
    quarter: Mapped[str] = txt()
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(ROADMAP_STATUS, nullable=False)


class Release(BusinessModel):
    """ENT-Release — `release_version` renamed from `version` (DEC-154, C19)."""

    __tablename__ = "releases"
    __table_args__ = (
        UniqueConstraint("product_id", "release_version"),
        {"schema": S},
    )

    product_id: Mapped[uuid.UUID] = fk(f"{S}.products.id")
    release_version: Mapped[str] = txt()
    status: Mapped[str] = mapped_column(RELEASE_STATUS, nullable=False)
    released_at: Mapped[datetime | None] = ts()
    release_notes: Mapped[str | None] = txt(nullable=True)


class Feature(BusinessModel):
    """ENT-Feature — → `released` emits EVT-product.feature_released."""

    __tablename__ = "features"
    __table_args__ = schema_args(S)

    product_id: Mapped[uuid.UUID] = fk(f"{S}.products.id")
    name: Mapped[str] = txt()
    status: Mapped[str] = mapped_column(FEATURE_STATUS, nullable=False)
    release_id: Mapped[uuid.UUID | None] = fk(f"{S}.releases.id", nullable=True)
    roadmap_item_id: Mapped[uuid.UUID | None] = fk(f"{S}.roadmap_items.id", nullable=True)


class ProductMetric(LogModel):
    """ENT-ProductMetric — append-only snapshot; corrections via `superseded_by_id` (05 C5)."""

    __tablename__ = "product_metrics"
    __table_args__ = (
        CheckConstraint("dau IS NULL OR dau <= mau", name="dau_le_mau"),
        CheckConstraint(
            "adoption_rate_pct IS NULL OR adoption_rate_pct BETWEEN 0 AND 100",
            name="adoption_rate_pct_0_100",
        ),
        CheckConstraint("churn_rate_pct BETWEEN 0 AND 100", name="churn_rate_pct_0_100"),
        CheckConstraint(
            "retention_30d_pct IS NULL OR retention_30d_pct BETWEEN 0 AND 100",
            name="retention_30d_pct_0_100",
        ),
        CheckConstraint("nps IS NULL OR nps BETWEEN -100 AND 100", name="nps_range"),
        Index(
            "uq_product_metrics_product_id_period_key_current",
            "product_id",
            "period_key",
            unique=True,
            postgresql_where=text("superseded_by_id IS NULL"),
        ),
        {"schema": S},
    )

    product_id: Mapped[uuid.UUID] = fk(f"{S}.products.id")
    period_key: Mapped[str] = txt()
    mau: Mapped[int] = mapped_column(Integer, nullable=False)
    dau: Mapped[int | None] = mapped_column(Integer, nullable=True)
    adoption_rate_pct: Mapped[Any] = pct()
    churn_rate_pct: Mapped[Any] = pct(nullable=False)
    retention_30d_pct: Mapped[Any] = pct()
    nps: Mapped[Any] = mapped_column(Numeric(6, 2), nullable=True)
    arpu: Mapped[int | None] = money(nullable=True)
    currency: Mapped[str] = currency()
    superseded_by_id: Mapped[uuid.UUID | None] = fk(f"{S}.product_metrics.id", nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()

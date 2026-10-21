"""Product seed (T-236, DEC-208) — 3 products of ABC (08 §3, DOC-08), 6 months of metric
snapshots, Q3/Q4 roadmap items, 2 releases and 5 features. Idempotent (`source='SEED'`).

Designed so PRD-01..05 + CUS-05 all carry values for the demo month (last closed month 2026-09):
"ABC Order" churn jumps 3.1 → 5.4% (BR-PRD-01 anomaly → PRD-02 critical), retention 30d
weighted ≈ 38% (warning), one Q3 roadmap item late (PRD-04 ≈ 67% warning), 2 of 3 planned
features released in September (PRD-05 ≈ 67% warning).
"""

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.product.models import Feature, Product, ProductMetric, Release, RoadmapItem
from app.seed.ids import seed_uuid

SEED: dict[str, Any] = {"source": "SEED"}
# code, name, lifecycle, launched
PRODUCTS = (
    ("ABC-ORDER", "ABC Order", "growth", date(2024, 3, 1)),
    ("ABC-CARE", "ABC Care — bảo trì thiết bị", "mature", date(2021, 6, 1)),
    ("ABC-INSIGHT", "ABC Insight", "development", None),
)
# period → product → (mau, dau, churn %, retention 30d %, nps)
SNAPSHOTS: dict[str, dict[str, tuple[int, int, float, float, float]]] = {
    "2026-04": {"ABC-ORDER": (4200, 1500, 3.0, 41.0, 34), "ABC-CARE": (900, 260, 1.5, 55.0, 41)},
    "2026-05": {"ABC-ORDER": (4350, 1560, 3.1, 40.5, 33), "ABC-CARE": (910, 262, 1.4, 54.0, 41)},
    "2026-06": {"ABC-ORDER": (4480, 1600, 3.2, 40.0, 33), "ABC-CARE": (915, 265, 1.6, 54.5, 40)},
    "2026-07": {"ABC-ORDER": (4560, 1620, 3.0, 39.0, 32), "ABC-CARE": (920, 268, 1.5, 53.0, 40)},
    "2026-08": {"ABC-ORDER": (4610, 1630, 3.1, 37.5, 31), "ABC-CARE": (925, 270, 1.6, 53.5, 39)},
    "2026-09": {"ABC-ORDER": (4380, 1540, 5.4, 34.0, 27), "ABC-CARE": (930, 272, 1.5, 54.0, 39)},
}
# key, product, title, quarter, planned, completed, status
ROADMAP = (
    ("RM-01", "ABC-ORDER", "Thanh toán QR trong app", "2026-Q3", date(2026, 7, 31),
     date(2026, 7, 28), "done"),
    ("RM-02", "ABC-ORDER", "Đặt hàng định kỳ", "2026-Q3", date(2026, 9, 15), None, "delayed"),
    ("RM-03", "ABC-CARE", "Lịch bảo trì tự động", "2026-Q3", date(2026, 9, 30),
     date(2026, 9, 25), "done"),
    ("RM-04", "ABC-INSIGHT", "Bản beta dashboard", "2026-Q4", date(2026, 12, 15), None,
     "in_progress"),
)  # fmt: skip
RELEASES = (("REL-1", "ABC-ORDER", "3.4.0", datetime(2026, 9, 10, 3, tzinfo=UTC)),
            ("REL-2", "ABC-CARE", "2.9.0", datetime(2026, 9, 24, 3, tzinfo=UTC)))  # fmt: skip
# key, product, name, status, release, roadmap item
FEATURES = (
    ("F-01", "ABC-ORDER", "QR VietQR", "released", "REL-1", "RM-01"),
    ("F-02", "ABC-ORDER", "Đơn định kỳ hàng tháng", "in_progress", None, "RM-02"),
    ("F-03", "ABC-CARE", "Nhắc lịch bảo trì", "released", "REL-2", "RM-03"),
    ("F-04", "ABC-INSIGHT", "Biểu đồ doanh thu", "planned", None, "RM-04"),
    ("F-05", "ABC-ORDER", "Giỏ hàng nhiều kho", "planned", None, None),
)


def pid(code: str) -> uuid.UUID:
    return seed_uuid("product", code)


async def seed_product(db: AsyncSession, owner: uuid.UUID | None) -> dict[str, int]:
    has = select(func.count()).select_from(Product).where(Product.source == "SEED")
    if owner is None or int((await db.execute(has)).scalar_one()):
        return {"products": 0}
    db.add_all([
        Product(id=pid(code), code=code, name=name, description=f"Sản phẩm {name} của ABC",
                status="active", lifecycle_stage=stage, launched_at=launched,
                target_launch_date=launched or date(2027, 3, 1), owner_id=owner, **SEED)
        for code, name, stage, launched in PRODUCTS
    ])  # fmt: skip
    await db.flush()
    db.add_all([
        ProductMetric(id=seed_uuid("product_metric", f"{code}:{period}"), product_id=pid(code),
                      period_key=period, mau=mau, dau=dau, churn_rate_pct=churn,
                      retention_30d_pct=ret, nps=nps, adoption_rate_pct=round(dau / mau * 100, 2),
                      currency="VND")
        for period, rows in SNAPSHOTS.items()
        for code, (mau, dau, churn, ret, nps) in rows.items()
    ])  # fmt: skip
    db.add_all([
        RoadmapItem(id=seed_uuid("roadmap", key), product_id=pid(p), title=title, quarter=q,
                    planned_date=planned, completed_at=done, status=status, **SEED)
        for key, p, title, q, planned, done, status in ROADMAP
    ])  # fmt: skip
    db.add_all([
        Release(id=seed_uuid("release", key), product_id=pid(p), release_version=v,
                status="released", released_at=at, **SEED)
        for key, p, v, at in RELEASES
    ])  # fmt: skip
    await db.flush()
    db.add_all([
        Feature(id=seed_uuid("feature", key), product_id=pid(p), name=name, status=status,
                release_id=seed_uuid("release", rel) if rel else None,
                roadmap_item_id=seed_uuid("roadmap", rm) if rm else None, **SEED)
        for key, p, name, status, rel, rm in FEATURES
    ])  # fmt: skip
    await db.flush()
    n = len(PRODUCTS) + sum(len(r) for r in SNAPSHOTS.values())
    return {"products": n + len(ROADMAP) + len(RELEASES) + len(FEATURES)}

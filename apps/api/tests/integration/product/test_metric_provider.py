"""T-202 / DEC-205 — product metric provider METRIC-PRD-01..05 + CUS-05 (TC-PRD-004).

Periods are in 2038 (after any seed row). CUS-05 uses each live product's latest snapshot, so
other (seed) products are soft-deleted inside the rolled-back test transaction.
"""

import uuid
from datetime import date
from typing import Any

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import METRIC_PROVIDERS
from app.modules.product.models import Product
from app.modules.product.services.metrics import compute
from tests.conftest import ApiClient
from tests.integration.product.helpers import make, make_product

pytestmark = pytest.mark.integration


async def snap(api: ApiClient, pid: str, period: str, mau: int, churn: float, **kw: Any) -> None:
    body = {"period_key": period, "mau": mau, "churn_rate_pct": churn, **kw}
    r = await api.call("POST", f"/product/products/{pid}/metrics", "CPO", json=body)
    assert r.status_code == 201, r.text


async def hide_other_snapshots(db: AsyncSession, keep: set[str]) -> None:
    """Soft-delete every other product (test transaction is rolled back)."""
    await db.execute(
        update(Product)
        .where(Product.id.not_in([uuid.UUID(k) for k in keep]), Product.deleted_at.is_(None))
        .values(deleted_at=date(2038, 1, 1))
    )


def by_code(readings: list[Any]) -> dict[str, Any]:
    return {r.code: r for r in readings}


async def test_provider_registered_and_values(api: ApiClient, db_session: AsyncSession) -> None:
    assert METRIC_PROVIDERS.providers["product"] is compute
    a = await make_product(api, lifecycle_stage="growth")
    b = await make_product(api, lifecycle_stage="mature")
    await make_product(api, lifecycle_stage="idea")  # not launched: excluded from PRD-01..03
    await hide_other_snapshots(db_session, {a["id"], b["id"]})
    for period in ("2038-01", "2038-02", "2038-03"):
        await snap(api, a["id"], period, 1000, 1.0)
        await snap(api, b["id"], period, 1000, 1.0)
    await snap(api, a["id"], "2038-04", 1000, 2.0, retention_30d_pct=50, nps=40)
    await snap(api, b["id"], "2038-04", 600, 1.0, retention_30d_pct=30, nps=0)

    base = {"product_id": a["id"], "title": "x", "quarter": "2038-Q2"}
    item = await make(api, "roadmap-items", {**base, "target_date": "2038-04-10"})  # late
    await make(api, "roadmap-items", {**base, "target_date": "2038-06-30"})  # on track
    rel = await make(
        api,
        "releases",
        {
            "product_id": a["id"],
            "release_version": "1",
            "status": "released",
            "released_at": "2038-04-05T00:00:00Z",
        },
    )
    await make(
        api,
        "features",
        {"product_id": a["id"], "name": "f1", "status": "released", "release_id": rel["id"]},
    )
    await make(
        api, "features", {"product_id": a["id"], "name": "f2", "roadmap_item_id": item["id"]}
    )

    out = by_code(await compute(db_session, date(2038, 5, 3)))
    assert set(out) == {f"METRIC-PRD-0{i}" for i in range(1, 6)} | {"METRIC-CUS-05"}
    assert all(r.period_key == "2038-04" and r.scope_type == "company" for r in out.values())
    prd1 = out["METRIC-PRD-01"]
    assert prd1.value == 1600 and prd1.threshold_input == 20.0 and len(prd1.records) == 2
    prd2 = out["METRIC-PRD-02"]
    assert prd2.value == 2.0 and prd2.threshold_input == 100.0
    assert out["METRIC-PRD-03"].value == 42.5
    assert out["METRIC-PRD-04"].value == 50.0 and len(out["METRIC-PRD-04"].records) == 2
    assert out["METRIC-PRD-05"].value == 50.0
    assert {r.table for r in out["METRIC-PRD-05"].records} == {"features"}
    assert out["METRIC-CUS-05"].value == 25.0
    assert all(r.status_reason is None for r in out.values())


async def test_provider_no_data(db_session: AsyncSession) -> None:
    await db_session.execute(
        update(Product).where(Product.deleted_at.is_(None)).values(deleted_at=date(2038, 1, 1))
    )
    out = by_code(await compute(db_session, date(2039, 1, 15)))
    for code, r in out.items():
        assert r.value is None and r.status_reason == "NO_DATA", code
        assert r.period_key == "2038-12"
    assert out["METRIC-PRD-01"].threshold_input == 0.0
    assert out["METRIC-PRD-02"].threshold_input == 0.0

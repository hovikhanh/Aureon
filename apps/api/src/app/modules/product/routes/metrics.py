"""EP-95 product metric snapshots (L `product:query`, C `product:write` — 10 §3.9), EP-90."""

import uuid
from typing import Annotated, Any

from fastapi import Depends, Query, Response

from app.core.envelope import Page
from app.core.errors import BadRequestError
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.modules.product.routes.deps import DASHBOARD_CACHE, Db, Querier, Writer, router
from app.modules.product.schemas.metrics import MetricCreate, MetricOut, ProductDashboardOut
from app.modules.product.services import calculations as calc
from app.modules.product.services.dashboard_service import ProductDashboardService
from app.modules.product.services.metric_service import MetricService


@router.get("/product/products/{product_id}/metrics", response_model=list[MetricOut])
async def list_metrics(
    product_id: uuid.UUID, db: Db, user: Querier,
    page: Annotated[PageParams, Depends(page_params("period_key"))],
) -> Any:  # fmt: skip
    items, total = await MetricService(db).list_metrics(user, product_id, page)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/product/products/{product_id}/metrics", response_model=MetricOut, status_code=201)
async def create_metric(
    product_id: uuid.UUID, body: MetricCreate, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return MetricOut.model_validate(hit)
    out = await MetricService(db).create_metric(user, product_id, body)
    await db.commit()
    await idem.remember(out)
    return out


async def _period(period: Annotated[str | None, Query(max_length=20)] = None) -> str | None:
    """10 §1.5 `period` — validated up front so a bad value is `400 BAD_REQUEST`."""
    if period is not None:
        try:
            calc.resolve_period(period, ProductDashboardService.today())
        except ValueError as exc:
            raise BadRequestError(str(exc), details={"param": "period"}) from exc
    return period


@router.get("/product/dashboard", response_model=ProductDashboardOut)
async def dashboard(
    db: Db, user: Querier, response: Response,
    period: Annotated[str | None, Depends(_period)] = None,
) -> Any:  # fmt: skip
    """EP-90 (10 §5) — `private, max-age=60` + `Vary: Authorization`."""
    response.headers.update(DASHBOARD_CACHE)
    return await ProductDashboardService(db).dashboard(user, period)

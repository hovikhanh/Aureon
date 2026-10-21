"""HTTP routes for `dashboard` — EP-11, EP-12, EP-15, EP-16, EP-17 (10 §3.2, §4.2; T-220/221).

GET responses: `Cache-Control: private, max-age=60` + `Vary: Authorization` (CLAUDE §5.2).
"""

import uuid
from typing import Annotated, Any, Literal

from fastapi import Depends, Header, Query, Response

from app.core.deps import DbSession, Principal, require_permission
from app.core.envelope import Page
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.dashboard.schemas import (
    AcknowledgeIn,
    AlertOut,
    DismissIn,
    MetricDetail,
    MetricStatus,
    MetricValueOut,
    Pillar,
)
from app.modules.dashboard.services.dashboard_service import DashboardService

router = EnvelopeRouter(prefix="/dashboard", tags=["dashboard"])

Reader = Annotated[Principal, Depends(require_permission("dashboard", "read"))]
Writer = Annotated[Principal, Depends(require_permission("dashboard", "write"))]
AlertPage = Annotated[PageParams, Depends(page_params())]


def _cache(response: Response) -> None:
    response.headers["Cache-Control"] = "private, max-age=60"
    response.headers["Vary"] = "Authorization"


@router.get("/metrics", response_model=list[MetricValueOut], summary="EP-11 Metrics")
async def list_metrics(
    db: DbSession, user: Reader, response: Response,
    pillar: Pillar | None = None, status: MetricStatus | None = None,
    period: Annotated[str | None, Query(max_length=20)] = None,
) -> Any:  # fmt: skip
    _cache(response)
    return await DashboardService(db).metrics(user, pillar=pillar, status=status)


@router.get("/metrics/{metric_code}", response_model=MetricDetail, summary="EP-12 Metric detail")
async def metric_detail(
    metric_code: str, db: DbSession, user: Reader, response: Response,
    accept_language: Annotated[str | None, Header()] = None,
) -> Any:  # fmt: skip
    _cache(response)
    lang = "en" if (accept_language or "").lower().startswith("en") else "vi"
    return await DashboardService(db).detail(user, metric_code, lang)


@router.get("/alerts", response_model=list[AlertOut], summary="EP-15 Alerts")
async def list_alerts(
    db: DbSession, user: Reader, page: AlertPage, response: Response,
    status: Literal["open", "acknowledged", "resolved", "dismissed"] | None = None,
    severity: Literal["warning", "critical"] | None = None,
    pillar: Pillar | None = None,
) -> Page[AlertOut]:  # fmt: skip
    response.headers["Cache-Control"] = "no-store"
    return await DashboardService(db).alerts(
        user, status=status, severity=severity, pillar=pillar,
        limit=page.limit, offset=page.offset,
    )  # fmt: skip


@router.post("/alerts/{id}/acknowledge", response_model=AlertOut, summary="EP-16 Acknowledge")
async def acknowledge(
    id: uuid.UUID, body: AcknowledgeIn, db: DbSession, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return AlertOut.model_validate(hit)
    out = await DashboardService(db).acknowledge(user, id, body.note)
    await db.commit()
    await idem.remember(out)
    return out


@router.post("/alerts/{id}/dismiss", response_model=AlertOut, summary="EP-17 Dismiss")
async def dismiss(id: uuid.UUID, body: DismissIn, db: DbSession, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return AlertOut.model_validate(hit)
    out = await DashboardService(db).dismiss(user, id, body.reason)
    await db.commit()
    await idem.remember(out)
    return out

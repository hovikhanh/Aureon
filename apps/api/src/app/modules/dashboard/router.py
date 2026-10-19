"""FastAPI router for Dashboard endpoints — EP-10..EP-17 (10 §4).

Reads precomputed metric values; mutations (ack/dismiss) write audit logs.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.envelope import Envelope, Page
from app.core.pagination import PageParams, build_page_meta, get_page_params
from app.db.session import get_db
from app.modules.auth.deps import require_role
from app.modules.auth.models import User
from app.modules.dashboard import alerts as alerts_svc
from app.modules.dashboard import detail as detail_svc
from app.modules.dashboard import service as dash_svc
from app.modules.dashboard.schemas import (
    AlertActionRequest,
    AlertDismissRequest,
    AlertOut,
    DashboardOut,
    MetricDetailOut,
    MetricValueOut,
    RecordLineageOut,
    RecordOut,
)

router = APIRouter(tags=["dashboard"])

# ROLE-05 (Reviewer) has no dashboard (03 §5.1) -> excluded from require_role.
_DASHBOARD_ROLES = ("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04")


@router.get("/dashboard", response_model=Envelope[DashboardOut])
def get_dashboard(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_role(*_DASHBOARD_ROLES))],
    period_key: Annotated[str | None, Query()] = None,
) -> Envelope[DashboardOut]:
    """EP-10: role-scoped dashboard (pillars, headline metrics, top alerts, AI summary)."""
    return Envelope(data=dash_svc.build_dashboard(db, user, period_key))


@router.get("/metrics", response_model=Page[MetricValueOut])
def list_metrics(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_role(*_DASHBOARD_ROLES))],
    pillar: Annotated[str | None, Query()] = None,
    period_key: Annotated[str | None, Query()] = None,
) -> Page[MetricValueOut]:
    """EP-11: list in-scope metric values."""
    items = dash_svc.list_metrics(db, user, pillar, period_key)
    params = PageParams(page=1, page_size=max(len(items), 1))
    return Page(data=items, meta=build_page_meta(params, total=len(items)))


@router.get("/metrics/{metric_code}", response_model=Envelope[MetricDetailOut])
def get_metric_detail(
    metric_code: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_role(*_DASHBOARD_ROLES))],
    period_key: Annotated[str | None, Query()] = None,
    history: Annotated[int, Query(ge=1, le=24)] = 12,
) -> Envelope[MetricDetailOut]:
    """EP-12: metric detail with P01 lineage panel (drill-down click 1)."""
    return Envelope(data=detail_svc.get_metric_detail(db, user, metric_code, period_key, history))


@router.get("/metrics/{metric_code}/records", response_model=Page[RecordOut])
def get_metric_records(
    metric_code: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_role(*_DASHBOARD_ROLES))],
    params: Annotated[PageParams, Depends(get_page_params)],
    period_key: Annotated[str | None, Query()] = None,
    record_filter: Annotated[str | None, Query()] = None,
) -> Page[RecordOut]:
    """EP-13: source records of a metric (drill-down click 2)."""
    items, total = detail_svc.get_metric_records(
        db, user, metric_code, period_key, record_filter, params.offset, params.limit
    )
    return Page(data=items, meta=build_page_meta(params, total=total))


@router.get("/business-records/{id}/lineage", response_model=Envelope[RecordLineageOut])
def get_record_lineage(
    id: UUID,  # EP-14 contract path param name (10 §4)
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_role(*_DASHBOARD_ROLES))],
) -> Envelope[RecordLineageOut]:
    """EP-14: lineage of a business record (drill-down click 3)."""
    return Envelope(data=detail_svc.get_record_lineage(db, user, id))


@router.get("/alerts", response_model=Page[AlertOut])
def list_alerts(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_role(*_DASHBOARD_ROLES))],
    params: Annotated[PageParams, Depends(get_page_params)],
    status: Annotated[str | None, Query()] = None,
    severity: Annotated[str | None, Query()] = None,
) -> Page[AlertOut]:
    """EP-15: alerts in the role's receiving pillars."""
    items, total = alerts_svc.list_alerts(db, user, status, severity, params.offset, params.limit)
    return Page(data=items, meta=build_page_meta(params, total=total))


@router.post("/alerts/{id}/acknowledge", response_model=Envelope[AlertOut])
def acknowledge_alert(
    id: UUID,  # EP-16 contract path param name (10 §4)
    body: AlertActionRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_role(*_DASHBOARD_ROLES))],
) -> Envelope[AlertOut]:
    """EP-16: acknowledge an OPEN alert."""
    result = alerts_svc.acknowledge_alert(db, user, id, body.note)
    db.commit()
    return Envelope(data=result)


@router.post("/alerts/{id}/dismiss", response_model=Envelope[AlertOut])
def dismiss_alert(
    id: UUID,  # EP-17 contract path param name (10 §4)
    body: AlertDismissRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_role(*_DASHBOARD_ROLES))],
) -> Envelope[AlertOut]:
    """EP-17: dismiss an alert."""
    result = alerts_svc.dismiss_alert(db, user, id, body.reason)
    db.commit()
    return Envelope(data=result)

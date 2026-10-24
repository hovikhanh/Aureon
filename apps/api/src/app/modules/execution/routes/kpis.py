"""`/kpis/*` — D08 KPI + D10 KPI check-ins: EP-KPI-01..10, EP-PRF-03/04 (10 §7.2.3, R-DEC-58).

EP-KPI-01..07 moved from `/execution/kpis*` with v2.1 behaviour (no alias); EP-PRF-03/04 replace
`/execution/check-ins?kpi_id=` / `POST /execution/check-ins {kpi_id}`. EP-KPI-08..10 (T-627):
effective-dated targets and per-period evaluations (R-DEC-52/53).
"""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_permission
from app.core.envelope import Page
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.execution.schemas.common import PERIOD, KpiBand
from app.modules.execution.schemas.kpi import (
    KpiCreate,
    KpiEvaluationOut,
    KpiOut,
    KpiTargetCreate,
    KpiTargetOut,
    KpiUpdate,
    MeasurementCreate,
    MeasurementOut,
)
from app.modules.execution.schemas.okr import CheckInCreate, CheckInOut
from app.modules.execution.services.kpi_service import KpiService
from app.modules.execution.services.kpi_target_service import KpiTargetService

router = EnvelopeRouter(prefix="/kpis", tags=["goals"])

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_permission("execution:read"))]
Writer = Annotated[Principal, Depends(require_permission("execution:write"))]


def _page(items: Any, total: int, page: PageParams) -> Page[Any]:
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


# ---------- EP-KPI-01..05 KPIs ----------
@router.get("", response_model=list[KpiOut], summary="EP-KPI-01 List KPIs")
async def list_kpis(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("code", "name", "updated_at"))],
    owner_id: uuid.UUID | None = None, metric_code: str | None = None,
    strategic_objective_id: uuid.UUID | None = None, department_id: uuid.UUID | None = None,
    parent_kpi_id: uuid.UUID | None = None, band: KpiBand | None = None,
) -> Any:  # fmt: skip
    items, total = await KpiService(db).list_kpis(
        user, page, owner_id=owner_id, metric_code=metric_code, department_id=department_id,
        parent_kpi_id=parent_kpi_id, strategic_objective_id=strategic_objective_id, band=band,
    )  # fmt: skip
    return _page(items, total, page)


@router.post("", response_model=KpiOut, status_code=201, summary="EP-KPI-02 Create KPI")
async def create_kpi(body: KpiCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return KpiOut.model_validate(hit)
    out = await KpiService(db).create_kpi(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/{kpi_id}", response_model=KpiOut, summary="EP-KPI-03 Get KPI")
async def get_kpi(kpi_id: uuid.UUID, db: Db, user: Reader) -> Any:
    svc = KpiService(db)
    return await svc.out(await svc.get_kpi(user, kpi_id))


@router.patch("/{kpi_id}", response_model=KpiOut, summary="EP-KPI-04 Update KPI")
async def update_kpi(
    kpi_id: uuid.UUID, body: KpiUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await KpiService(db).update_kpi(user, kpi_id, body, exp)
    await db.commit()
    return out


@router.delete(
    "/{kpi_id}", status_code=204, response_class=Response, summary="EP-KPI-05 Delete KPI"
)
async def delete_kpi(kpi_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await KpiService(db).delete_kpi(user, kpi_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-KPI-06/07 measurements ----------
@router.get(
    "/{kpi_id}/measurements", response_model=list[MeasurementOut],
    summary="EP-KPI-06 List KPI measurements",
)  # fmt: skip
async def list_measurements(
    kpi_id: uuid.UUID, db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("period_key", "measured_at"))],
    period_key: str | None = None,
) -> Any:  # fmt: skip
    items, total = await KpiService(db).list_measurements(user, kpi_id, page, period_key)
    return _page(items, total, page)


@router.post(
    "/{kpi_id}/measurements", response_model=MeasurementOut, status_code=201,
    summary="EP-KPI-07 Record KPI measurement",
)  # fmt: skip
async def create_measurement(
    kpi_id: uuid.UUID, body: MeasurementCreate, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return MeasurementOut.model_validate(hit)
    out = await KpiService(db).measure(user, kpi_id, body)
    await db.commit()
    await idem.remember(out)
    return out


# ---------- EP-KPI-08/09 targets, EP-KPI-10 evaluations (T-627) ----------
@router.get(
    "/{kpi_id}/targets", response_model=list[KpiTargetOut], summary="EP-KPI-08 List KPI targets"
)
async def list_targets(
    kpi_id: uuid.UUID, db: Db, user: Reader, period_key: str | None = None,
    as_of: date | None = None,
) -> Any:  # fmt: skip
    """All versions (closed ones too), sorted `period_key`, `valid_from` (R-DEC-52)."""
    await KpiService(db).get_kpi(user, kpi_id)
    return await KpiTargetService(db).list_targets(kpi_id, period_key, as_of)


@router.post(
    "/{kpi_id}/targets", response_model=KpiTargetOut, status_code=201,
    summary="EP-KPI-09 Set KPI target (effective-dated)",
)  # fmt: skip
async def create_target(
    kpi_id: uuid.UUID, body: KpiTargetCreate, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return KpiTargetOut.model_validate(hit)
    await KpiService(db).get_kpi(user, kpi_id, "write")  # EMP → 403 (10 EP-KPI-09 "không EMP")
    out = await KpiTargetService(db).upsert(kpi_id, body, user.user_id)
    await db.commit()
    await idem.remember(out)
    return out


@router.get(
    "/{kpi_id}/evaluations", response_model=list[KpiEvaluationOut],
    summary="EP-KPI-10 List KPI evaluations",
)  # fmt: skip
async def list_evaluations(
    kpi_id: uuid.UUID, db: Db, user: Reader,
    from_period: Annotated[str | None, Query(pattern=PERIOD)] = None,
    to_period: Annotated[str | None, Query(pattern=PERIOD)] = None,
) -> Any:  # fmt: skip
    """`period_key` asc; default = the latest 12 periods (SCR-58 chart)."""
    await KpiService(db).get_kpi(user, kpi_id)
    return await KpiTargetService(db).list_evaluations(kpi_id, from_period, to_period)


# ---------- EP-PRF-03/04 KPI check-ins ----------
@router.get(
    "/{kpi_id}/check-ins", response_model=list[CheckInOut], summary="EP-PRF-03 List KPI check-ins"
)
async def list_kpi_check_ins(
    kpi_id: uuid.UUID, db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("checked_in_at"))],
) -> Any:  # fmt: skip
    svc = KpiService(db)
    await svc.get_kpi(user, kpi_id)  # 404 / 403 FORBIDDEN_SCOPE on the target
    items, total = await svc.list_check_ins(
        user, page, owner_id=None, period_key=None, kpi_id=kpi_id, key_result_id=None
    )
    return _page(items, total, page)


@router.post(
    "/{kpi_id}/check-ins", response_model=CheckInOut, status_code=201,
    summary="EP-PRF-04 Check in on a KPI",
)  # fmt: skip
async def create_kpi_check_in(
    kpi_id: uuid.UUID, body: CheckInCreate, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return CheckInOut.model_validate(hit)
    out = await KpiService(db).check_in_kpi(user, kpi_id, body)
    await db.commit()
    await idem.remember(out)
    return out

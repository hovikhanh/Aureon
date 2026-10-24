"""`/objectives/*`, `/key-results/*` — D09 OKR + D10 KR check-ins (10 §7.2.3, R-DEC-58).

EP-OKR-01..10 moved from `/execution/objectives*` with v2.1 behaviour (no alias); KR detail /
PATCH / DELETE flattened `/execution/objectives/{oid}/key-results/{id}` → `/key-results/{id}`
(create / list stay under the objective). EP-PRF-01/02 replace `/execution/check-ins` with a
`key_result_id`. Filters / endpoints that need M1.4 columns answer `501` until their task.
"""

import uuid
from typing import Annotated, Any

from fastapi import Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_permission
from app.core.envelope import Page
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.execution.schemas.okr import (
    CheckInCreate,
    CheckInOut,
    KeyResultCreate,
    KeyResultOut,
    KeyResultUpdate,
    KrMeasurementOut,
    ObjectiveCreate,
    ObjectiveOut,
    ObjectiveUpdate,
)
from app.modules.execution.services.kpi_service import KpiService
from app.modules.execution.services.okr_service import OkrService, kr_out

router = EnvelopeRouter(tags=["goals"])

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_permission("execution:read"))]
Writer = Annotated[Principal, Depends(require_permission("execution:write"))]
OBJ = "/objectives"
KR = "/key-results"


def _page(items: Any, total: int, page: PageParams) -> Page[Any]:
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


# ---------- EP-OKR-01..05 objectives ----------
@router.get(OBJ, response_model=list[ObjectiveOut], summary="EP-OKR-01 List objectives")
async def list_objectives(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("period_key", "title", "updated_at"))],
    period_key: str | None = None, owner_id: uuid.UUID | None = None,
    strategic_objective_id: uuid.UUID | None = None, department_id: uuid.UUID | None = None,
    parent_id: uuid.UUID | None = None, at_risk: bool | None = None,
) -> Any:  # fmt: skip
    items, total = await OkrService(db).list_objectives(
        user, page, period_key=period_key, owner_id=owner_id, department_id=department_id,
        parent_id=parent_id, strategic_objective_id=strategic_objective_id, at_risk=at_risk,
    )  # fmt: skip
    return _page(items, total, page)


@router.post(
    OBJ, response_model=ObjectiveOut, status_code=201, summary="EP-OKR-02 Create objective"
)
async def create_objective(body: ObjectiveCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ObjectiveOut.model_validate(hit)
    out = await OkrService(db).create_objective(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get(OBJ + "/{objective_id}", response_model=ObjectiveOut, summary="EP-OKR-03 Get objective")
async def get_objective(objective_id: uuid.UUID, db: Db, user: Reader) -> Any:
    svc = OkrService(db)
    return await svc.out(await svc.get_objective(user, objective_id))


@router.patch(
    OBJ + "/{objective_id}", response_model=ObjectiveOut, summary="EP-OKR-04 Update objective"
)
async def update_objective(
    objective_id: uuid.UUID, body: ObjectiveUpdate, db: Db, user: Writer,
    if_match: IfMatch = None,
) -> Any:  # fmt: skip
    exp = expected_version(if_match, body.version)
    out = await OkrService(db).update_objective(user, objective_id, body, exp)
    await db.commit()
    return out


@router.delete(
    OBJ + "/{objective_id}", status_code=204, response_class=Response,
    summary="EP-OKR-05 Delete objective",
)  # fmt: skip
async def delete_objective(objective_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await OkrService(db).delete_objective(user, objective_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-OKR-06..11 key results ----------
@router.get(
    OBJ + "/{objective_id}/key-results", response_model=list[KeyResultOut],
    summary="EP-OKR-06 List key results of an objective",
)  # fmt: skip
async def list_key_results(
    objective_id: uuid.UUID, db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("title", "updated_at"))],
) -> Any:  # fmt: skip
    items, total = await OkrService(db).list_krs(user, objective_id, page)
    return _page(items, total, page)


@router.post(
    OBJ + "/{objective_id}/key-results", response_model=KeyResultOut, status_code=201,
    summary="EP-OKR-07 Create key result",
)  # fmt: skip
async def create_key_result(
    objective_id: uuid.UUID, body: KeyResultCreate, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return KeyResultOut.model_validate(hit)
    out = await OkrService(db).create_kr(user, objective_id, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get(KR + "/{kr_id}", response_model=KeyResultOut, summary="EP-OKR-08 Get key result")
async def get_key_result(kr_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return kr_out(await OkrService(db).get_kr(user, kr_id))


@router.patch(KR + "/{kr_id}", response_model=KeyResultOut, summary="EP-OKR-09 Update key result")
async def update_key_result(
    kr_id: uuid.UUID, body: KeyResultUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await OkrService(db).update_kr(user, kr_id, body, exp)
    await db.commit()
    return out


@router.delete(
    KR + "/{kr_id}", status_code=204, response_class=Response,
    summary="EP-OKR-10 Delete key result",
)  # fmt: skip
async def delete_key_result(kr_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await OkrService(db).delete_kr(user, kr_id)
    await db.commit()
    return Response(status_code=204)


@router.get(
    KR + "/{kr_id}/measurements", response_model=list[KrMeasurementOut],
    summary="EP-OKR-11 List key result measurements",
)  # fmt: skip
async def list_kr_measurements(
    kr_id: uuid.UUID, db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("measured_at"))],
) -> Any:  # fmt: skip
    """`sort_by=measured_at` desc by default (10: "sort measured_at desc")."""
    await OkrService(db).get_kr(user, kr_id)  # 404 / 403 FORBIDDEN_SCOPE on the target
    items, total = await KpiService(db).list_kr_measurements(kr_id, page)
    return _page(items, total, page)


# ---------- EP-PRF-01/02 KR check-ins ----------
@router.get(
    KR + "/{kr_id}/check-ins", response_model=list[CheckInOut],
    summary="EP-PRF-01 List key result check-ins",
)  # fmt: skip
async def list_kr_check_ins(
    kr_id: uuid.UUID, db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("checked_in_at"))],
) -> Any:  # fmt: skip
    await OkrService(db).get_kr(user, kr_id)  # 404 / 403 FORBIDDEN_SCOPE on the target
    items, total = await KpiService(db).list_check_ins(
        user, page, owner_id=None, period_key=None, kpi_id=None, key_result_id=kr_id
    )
    return _page(items, total, page)


@router.post(
    KR + "/{kr_id}/check-ins", response_model=CheckInOut, status_code=201,
    summary="EP-PRF-02 Check in on a key result",
)  # fmt: skip
async def create_kr_check_in(
    kr_id: uuid.UUID, body: CheckInCreate, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return CheckInOut.model_validate(hit)
    out = await KpiService(db).check_in_kr(user, kr_id, body)
    await db.commit()
    await idem.remember(out)
    return out

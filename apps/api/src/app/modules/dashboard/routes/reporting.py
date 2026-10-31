"""HTTP routes for D28 Reporting v3 — EP-RPT-01..05 (10 §7.2.6, M2.1).

Perm (R-DEC-84, làm rõ 2026-10-31 — ma trận 02 §5.2 KHÔNG đổi): EP-RPT-01 + tiles 04/05 dùng
`dashboard:read`/`dashboard:write` (CEO/DIR); EP-RPT-02/03 (Department/Employee) dùng
`execution:read` — quyền MGR/EMP sẵn có, vì dashboard khối/cá nhân tổng hợp dữ liệu execution
(task/OKR/workload) chứ không phải metric store. Dashboard GET: `private, max-age=60` +
`Vary: Authorization`. PUT tiles bắt buộc Idempotency-Key.
"""

import uuid
from typing import Annotated, Any

from fastapi import Depends, Response

from app.core.deps import DbSession, Principal, require_permission
from app.core.idempotency import Idem
from app.core.routing import EnvelopeRouter
from app.modules.dashboard.schemas.reporting import (
    DepartmentDashboardOut,
    EmployeeDashboardOut,
    ExecutiveDashboardOut,
    ExecutiveTilesIn,
    ExecutiveTilesOut,
)
from app.modules.dashboard.services.dashboard_service import metric_visible
from app.modules.dashboard.services.reporting_service import ReportingService
from app.modules.platform.services.catalog import BY_CODE
from app.modules.platform.services.preference_service import UserPreferenceService

router = EnvelopeRouter(prefix="/reporting", tags=["reporting"])

Reader = Annotated[Principal, Depends(require_permission("dashboard", "read"))]
Writer = Annotated[Principal, Depends(require_permission("dashboard", "write"))]
ExecReader = Annotated[Principal, Depends(require_permission("execution", "read"))]


def _cache(response: Response) -> None:
    response.headers["Cache-Control"] = "private, max-age=60"
    response.headers["Vary"] = "Authorization"


@router.get(
    "/dashboards/executive", response_model=ExecutiveDashboardOut, summary="EP-RPT-01 Executive"
)
async def executive(db: DbSession, user: Reader, response: Response) -> Any:
    _cache(response)
    return await ReportingService(db).executive(user)


@router.get(
    "/dashboards/department", response_model=DepartmentDashboardOut, summary="EP-RPT-02 Department"
)
async def department(
    db: DbSession, user: ExecReader, response: Response, department_id: uuid.UUID | None = None
) -> Any:
    _cache(response)
    return await ReportingService(db).department(user, department_id)


@router.get(
    "/dashboards/employee", response_model=EmployeeDashboardOut, summary="EP-RPT-03 Employee"
)
async def employee(db: DbSession, user: ExecReader, response: Response) -> Any:
    _cache(response)
    return await ReportingService(db).employee(user)


@router.get(
    "/preferences/executive-tiles", response_model=ExecutiveTilesOut, summary="EP-RPT-04 Get tiles"
)
async def get_tiles(db: DbSession, user: Reader, response: Response) -> Any:
    response.headers["Cache-Control"] = "no-store"
    tiles, version = await UserPreferenceService(db).executive_tiles(user)
    return ExecutiveTilesOut(tiles=tiles, version=version)


@router.put(
    "/preferences/executive-tiles", response_model=ExecutiveTilesOut, summary="EP-RPT-05 Set tiles"
)
async def set_tiles(body: ExecutiveTilesIn, db: DbSession, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ExecutiveTilesOut.model_validate(hit)

    def in_scope(code: str) -> bool:
        pillar = BY_CODE[code].pillar
        return metric_visible(user, code, pillar)

    tiles, version = await UserPreferenceService(db).set_executive_tiles(
        user, body.tiles, body.version, in_scope
    )
    await db.commit()
    out = ExecutiveTilesOut(tiles=tiles, version=version)
    await idem.remember(out)
    return out

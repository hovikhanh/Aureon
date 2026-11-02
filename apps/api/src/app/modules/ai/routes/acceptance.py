"""EP-RPT-08 `GET /reporting/acceptance` (M3.5, R-DEC-145, 10 §7.2.12).

Read-only MVP acceptance snapshot (gates G1–G4). The aggregator lives in the `ai` module (top
layer) to avoid a `dashboard → ai` import cycle, but the spec path stays under `/reporting`.
Perm `dashboard:read` (CEO toàn DN / DIR theo scope); EMP/REV → 403 via require_permission.
"""

from typing import Annotated, Any

from fastapi import Depends, Query, Response

from app.core.deps import DbSession, Principal, require_permission
from app.core.routing import EnvelopeRouter
from app.modules.ai.services.acceptance_service import AcceptanceService
from app.modules.dashboard.schemas.reporting import AcceptanceSnapshotOut

router = EnvelopeRouter(prefix="/reporting", tags=["reporting"])

Reader = Annotated[Principal, Depends(require_permission("dashboard", "read"))]


@router.get(
    "/acceptance", response_model=AcceptanceSnapshotOut, summary="EP-RPT-08 MVP acceptance G1-G4"
)
async def acceptance(
    db: DbSession,
    user: Reader,
    response: Response,
    weeks: Annotated[int, Query(ge=1, le=12)] = 4,
) -> Any:
    response.headers["Cache-Control"] = "no-store"
    return await AcceptanceService(db).snapshot(user, weeks=weeks)

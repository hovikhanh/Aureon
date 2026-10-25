"""HTTP routes for `execution` — EP-42 meetings, EP-43 decisions, EP-49 dashboard (10 §3.4, §4.4).

Tasks/projects moved to `/work/*` (`routes/work.py`, 10 §7.2.2 — R-DEC-40, no alias).
KPI / OKR / check-in / initiative moved to `/goals/*`, `/kpis/*`, `/objectives/*`,
`/key-results/*` (`routes/{goals,kpis,okr}.py`, 10 §7.2.3 — R-DEC-39/58, no alias).

Same pattern as sales: one permission per route, `Idem` on create POSTs, `IfMatch` + body
`version` on PATCH, `Page` on lists, commit at the end of the request.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today
from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_permission
from app.core.envelope import Page
from app.core.errors import BadRequestError
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.periods import resolve_period
from app.core.routing import EnvelopeRouter
from app.modules.execution.routes.goals import router as goals_router
from app.modules.execution.routes.kpis import router as kpis_router
from app.modules.execution.routes.okr import router as okr_router
from app.modules.execution.routes.work import router as work_router
from app.modules.execution.schemas.common import DecisionStatus
from app.modules.execution.schemas.dashboard import ExecutionDashboardOut
from app.modules.execution.schemas.meetings import (
    DecisionCreate,
    DecisionOut,
    DecisionUpdate,
    MeetingCreate,
    MeetingOut,
    MeetingUpdate,
)
from app.modules.execution.services.dashboard_service import ExecutionDashboardService
from app.modules.execution.services.meeting_service import (
    MeetingService,
    decision_out,
    meeting_out,
)

router = EnvelopeRouter(tags=["execution"])
module_router = EnvelopeRouter()

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_permission("execution:read"))]
Writer = Annotated[Principal, Depends(require_permission("execution:write"))]
Querier = Annotated[Principal, Depends(require_permission("execution:query"))]


# ---------- EP-49 dashboard (10 §5, PIL-O execution half) ----------
@router.get("/execution/dashboard", response_model=ExecutionDashboardOut)
async def execution_dashboard(
    db: Db, user: Querier, response: Response, period: str | None = None,
    department_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    today = business_today()
    try:
        p = resolve_period(period, today)
    except ValueError as exc:
        raise BadRequestError(str(exc), details={"param": "period"}) from exc
    out = await ExecutionDashboardService(db).dashboard(user, p, today, department_id)
    response.headers["Cache-Control"] = "private, max-age=60"
    response.headers["Vary"] = "Authorization"
    return out


# ---------- EP-42 meetings ----------
@router.get("/execution/meetings", response_model=list[MeetingOut])
async def list_meetings(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("held_at", "updated_at", "title"))],
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None, department_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    items, total = await MeetingService(db).list_meetings(
        user, page, held_from=from_, held_to=to, department_id=department_id
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/execution/meetings", response_model=MeetingOut, status_code=201)
async def create_meeting(body: MeetingCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return MeetingOut.model_validate(hit)
    out = await MeetingService(db).create_meeting(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/execution/meetings/{meeting_id}", response_model=MeetingOut)
async def get_meeting(meeting_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return meeting_out(await MeetingService(db).get_meeting(user, meeting_id))


@router.patch("/execution/meetings/{meeting_id}", response_model=MeetingOut)
async def update_meeting(
    meeting_id: uuid.UUID, body: MeetingUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await MeetingService(db).update_meeting(user, meeting_id, body, exp)
    await db.commit()
    return out


@router.delete("/execution/meetings/{meeting_id}", status_code=204, response_class=Response)
async def delete_meeting(meeting_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await MeetingService(db).delete_meeting(user, meeting_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-43 decisions ----------
@router.get("/execution/decisions", response_model=list[DecisionOut])
async def list_decisions(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("decided_at", "due_date", "updated_at"))],
    status: DecisionStatus | None = None, meeting_id: uuid.UUID | None = None,
    initiative_id: uuid.UUID | None = None, review_due: bool | None = None,
) -> Any:  # fmt: skip
    items, total = await MeetingService(db).list_decisions(
        user, page, status=status, meeting_id=meeting_id, initiative_id=initiative_id,
        review_due=review_due,
    )  # fmt: skip
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/execution/decisions", response_model=DecisionOut, status_code=201)
async def create_decision(body: DecisionCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return DecisionOut.model_validate(hit)
    out = await MeetingService(db).create_decision(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/execution/decisions/{decision_id}", response_model=DecisionOut)
async def get_decision(decision_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return decision_out(await MeetingService(db).get_decision(user, decision_id))


@router.patch("/execution/decisions/{decision_id}", response_model=DecisionOut)
async def update_decision(
    decision_id: uuid.UUID, body: DecisionUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await MeetingService(db).update_decision(user, decision_id, body, exp)
    await db.commit()
    return out


# M1.3 T-619C: `/work/*` (R-DEC-40); M1.4 T-626C: goals (R-DEC-58) — mounted with the module.
module_router.include_router(router)
module_router.include_router(work_router)
module_router.include_router(goals_router)
module_router.include_router(kpis_router)
module_router.include_router(okr_router)

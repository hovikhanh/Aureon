"""`/goals/*` — D07 Strategy / StrategicObjective / Initiative + D10 check-in feed (10 §7.2.3).

EP-STR-12..21 moved from `/execution/initiatives*` with v2.1 behaviour (no alias, R-DEC-58);
EP-PRF-05 replaces `GET /execution/check-ins`. New endpoints answer `501` until their task
(`core/stub.py`). Static paths (`/goals/tree`, `/goals/check-ins/due`) are declared before
`{id}` catch-alls.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_permission
from app.core.envelope import Page
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.core.stub import not_implemented
from app.modules.execution.schemas.common import (
    Confidence,
    InitiativeStatus,
    Pillar,
    StrategyStatus,
)
from app.modules.execution.schemas.initiatives import (
    InitiativeCreate,
    InitiativeOut,
    InitiativeUpdate,
    MilestoneCreate,
    MilestoneOut,
    MilestoneUpdate,
)
from app.modules.execution.schemas.okr import CheckInDueOut, CheckInOut
from app.modules.execution.schemas.strategy import (
    GoalTreeOut,
    InitiativeProjectOut,
    StrategicObjectiveCreate,
    StrategicObjectiveOut,
    StrategicObjectiveUpdate,
    StrategyCreate,
    StrategyOut,
    StrategyUpdate,
)
from app.modules.execution.services.initiative_service import InitiativeService, initiative_out
from app.modules.execution.services.kpi_service import KpiService

router = EnvelopeRouter(prefix="/goals", tags=["goals"])

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_permission("execution:read"))]
Writer = Annotated[Principal, Depends(require_permission("execution:write"))]


def _page(items: Any, total: int, page: PageParams) -> Page[Any]:
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


# ---------- EP-STR-01 tree ----------
@router.get("/tree", response_model=GoalTreeOut, summary="EP-STR-01 Goal alignment tree")
async def goal_tree(
    user: Reader, strategy_id: uuid.UUID | None = None, period_key: str | None = None,
    department_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    not_implemented("EP-STR-01", "T-628")


# ---------- EP-PRF-05/06 check-in feed (static paths before `{id}`) ----------
@router.get("/check-ins", response_model=list[CheckInOut], summary="EP-PRF-05 Check-in feed")
async def list_check_ins(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("checked_in_at"))],
    owner_id: uuid.UUID | None = None, period_key: str | None = None,
    kpi_id: uuid.UUID | None = None, key_result_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None, to: datetime | None = None,
    confidence: Confidence | None = None,
) -> Any:  # fmt: skip
    items, total = await KpiService(db).list_check_ins(
        user, page, owner_id=owner_id, period_key=period_key, kpi_id=kpi_id,
        key_result_id=key_result_id, department_id=department_id, from_=from_, to=to,
        confidence=confidence,
    )  # fmt: skip
    return _page(items, total, page)


@router.get(
    "/check-ins/due", response_model=list[CheckInDueOut],
    summary="EP-PRF-06 My check-ins due (F4 card)",
)  # fmt: skip
async def check_ins_due(user: Reader) -> Any:
    not_implemented("EP-PRF-06", "T-628")


# ---------- EP-STR-02..06 strategies ----------
@router.get("/strategies", response_model=list[StrategyOut], summary="EP-STR-02 List strategies")
async def list_strategies(
    user: Reader,
    page: Annotated[PageParams, Depends(page_params("code", "period_start"))],
    status: StrategyStatus | None = None,
) -> Any:  # fmt: skip
    not_implemented("EP-STR-02", "T-628")


@router.post(
    "/strategies", response_model=StrategyOut, status_code=201,
    summary="EP-STR-03 Create strategy",
)  # fmt: skip
async def create_strategy(body: StrategyCreate, user: Writer, idem: Idem) -> Any:
    not_implemented("EP-STR-03", "T-628")


@router.get(
    "/strategies/{strategy_id}", response_model=StrategyOut, summary="EP-STR-04 Get strategy"
)
async def get_strategy(strategy_id: uuid.UUID, user: Reader) -> Any:
    not_implemented("EP-STR-04", "T-628")


@router.patch(
    "/strategies/{strategy_id}", response_model=StrategyOut, summary="EP-STR-05 Update strategy"
)
async def update_strategy(
    strategy_id: uuid.UUID, body: StrategyUpdate, user: Writer, if_match: IfMatch = None
) -> Any:
    not_implemented("EP-STR-05", "T-628")


@router.delete(
    "/strategies/{strategy_id}", status_code=204, response_class=Response,
    summary="EP-STR-06 Delete strategy",
)  # fmt: skip
async def delete_strategy(strategy_id: uuid.UUID, user: Writer) -> Response:
    not_implemented("EP-STR-06", "T-628")


# ---------- EP-STR-07..11 strategic objectives ----------
SO = "/strategic-objectives"


@router.get(
    SO, response_model=list[StrategicObjectiveOut], summary="EP-STR-07 List strategic objectives"
)
async def list_strategic_objectives(
    user: Reader,
    page: Annotated[PageParams, Depends(page_params("sort_order", "code"))],
    strategy_id: uuid.UUID | None = None, pillar: Pillar | None = None,
    department_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    not_implemented("EP-STR-07", "T-628")


@router.post(
    SO, response_model=StrategicObjectiveOut, status_code=201,
    summary="EP-STR-08 Create strategic objective",
)  # fmt: skip
async def create_strategic_objective(
    body: StrategicObjectiveCreate, user: Writer, idem: Idem
) -> Any:
    not_implemented("EP-STR-08", "T-628")


@router.get(
    SO + "/{so_id}", response_model=StrategicObjectiveOut,
    summary="EP-STR-09 Get strategic objective",
)  # fmt: skip
async def get_strategic_objective(so_id: uuid.UUID, user: Reader) -> Any:
    not_implemented("EP-STR-09", "T-628")


@router.patch(
    SO + "/{so_id}", response_model=StrategicObjectiveOut,
    summary="EP-STR-10 Update strategic objective",
)  # fmt: skip
async def update_strategic_objective(
    so_id: uuid.UUID, body: StrategicObjectiveUpdate, user: Writer, if_match: IfMatch = None
) -> Any:
    not_implemented("EP-STR-10", "T-628")


@router.delete(
    SO + "/{so_id}", status_code=204, response_class=Response,
    summary="EP-STR-11 Delete strategic objective",
)  # fmt: skip
async def delete_strategic_objective(so_id: uuid.UUID, user: Writer) -> Response:
    not_implemented("EP-STR-11", "T-628")


# ---------- EP-STR-12..16 initiatives (v2.1 EP-45) ----------
INI = "/initiatives"


@router.get(INI, response_model=list[InitiativeOut], summary="EP-STR-12 List initiatives")
async def list_initiatives(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(
        page_params("planned_end_date", "start_date", "code", "progress_pct")
    )],
    objective_id: uuid.UUID | None = None, status: InitiativeStatus | None = None,
    pillar: Pillar | None = None, strategic_objective_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    if strategic_objective_id is not None:
        not_implemented("EP-STR-12 strategic_objective_id", "T-626")
    items, total = await InitiativeService(db).list_initiatives(
        user, page, objective_id=objective_id, status=status, pillar=pillar
    )
    return _page(items, total, page)


@router.post(
    INI, response_model=InitiativeOut, status_code=201, summary="EP-STR-13 Create initiative"
)
async def create_initiative(body: InitiativeCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return InitiativeOut.model_validate(hit)
    out = await InitiativeService(db).create_initiative(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get(
    INI + "/{initiative_id}", response_model=InitiativeOut, summary="EP-STR-14 Get initiative"
)
async def get_initiative(initiative_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return initiative_out(await InitiativeService(db).get_initiative(user, initiative_id))


@router.patch(
    INI + "/{initiative_id}", response_model=InitiativeOut, summary="EP-STR-15 Update initiative"
)
async def update_initiative(
    initiative_id: uuid.UUID, body: InitiativeUpdate, db: Db, user: Writer,
    if_match: IfMatch = None,
) -> Any:  # fmt: skip
    exp = expected_version(if_match, body.version)
    out = await InitiativeService(db).update_initiative(user, initiative_id, body, exp)
    await db.commit()
    return out


@router.delete(
    INI + "/{initiative_id}", status_code=204, response_class=Response,
    summary="EP-STR-16 Delete initiative",
)  # fmt: skip
async def delete_initiative(initiative_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await InitiativeService(db).delete_initiative(user, initiative_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-STR-17..21 initiative milestones ----------
MS = INI + "/{initiative_id}/milestones"


@router.get(MS, response_model=list[MilestoneOut], summary="EP-STR-17 List initiative milestones")
async def list_milestones(
    initiative_id: uuid.UUID, db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("due_date", "title"))],
) -> Any:  # fmt: skip
    items, total = await InitiativeService(db).list_milestones(user, initiative_id, page)
    return _page(items, total, page)


@router.post(
    MS, response_model=MilestoneOut, status_code=201,
    summary="EP-STR-18 Create initiative milestone",
)  # fmt: skip
async def create_milestone(
    initiative_id: uuid.UUID, body: MilestoneCreate, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return MilestoneOut.model_validate(hit)
    out = await InitiativeService(db).create_milestone(user, initiative_id, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get(
    MS + "/{milestone_id}", response_model=MilestoneOut,
    summary="EP-STR-19 Get initiative milestone",
)  # fmt: skip
async def get_milestone(
    initiative_id: uuid.UUID, milestone_id: uuid.UUID, db: Db, user: Reader
) -> Any:
    return await InitiativeService(db).get_milestone(user, initiative_id, milestone_id)


@router.patch(
    MS + "/{milestone_id}", response_model=MilestoneOut,
    summary="EP-STR-20 Update initiative milestone",
)  # fmt: skip
async def update_milestone(
    initiative_id: uuid.UUID, milestone_id: uuid.UUID, body: MilestoneUpdate, db: Db,
    user: Writer, if_match: IfMatch = None,
) -> Any:  # fmt: skip
    exp = expected_version(if_match, body.version)
    out = await InitiativeService(db).update_milestone(user, initiative_id, milestone_id, body, exp)
    await db.commit()
    return out


@router.delete(
    MS + "/{milestone_id}", status_code=204, response_class=Response,
    summary="EP-STR-21 Delete initiative milestone",
)  # fmt: skip
async def delete_milestone(
    initiative_id: uuid.UUID, milestone_id: uuid.UUID, db: Db, user: Writer
) -> Response:
    await InitiativeService(db).delete_milestone(user, initiative_id, milestone_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-STR-22 initiative → projects ----------
@router.get(
    INI + "/{initiative_id}/projects", response_model=list[InitiativeProjectOut],
    summary="EP-STR-22 List projects of an initiative",
)  # fmt: skip
async def list_initiative_projects(initiative_id: uuid.UUID, user: Reader) -> Any:
    not_implemented("EP-STR-22", "T-628")

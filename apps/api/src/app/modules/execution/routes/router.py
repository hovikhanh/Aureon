"""HTTP routes for `execution` — EP-42..49 (10 §3.4, §4.4).

Same pattern as sales: one permission per route, `Idem` on create POSTs, `IfMatch` + body
`version` on PATCH, `Page` on lists, commit at the end of the request.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_permission
from app.core.envelope import Page
from app.core.errors import NotFoundError
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.execution.schemas.common import (
    DecisionStatus,
    InitiativeStatus,
    Pillar,
    ProjectStatus,
    TaskStatus,
)
from app.modules.execution.schemas.initiatives import (
    InitiativeCreate,
    InitiativeOut,
    InitiativeUpdate,
    MilestoneCreate,
    MilestoneOut,
    MilestoneUpdate,
)
from app.modules.execution.schemas.meetings import (
    DecisionCreate,
    DecisionOut,
    DecisionUpdate,
    MeetingCreate,
    MeetingOut,
    MeetingUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
)
from app.modules.execution.schemas.okr import (
    CheckInCreate,
    CheckInOut,
    KeyResultCreate,
    KeyResultOut,
    KeyResultUpdate,
    KpiCreate,
    KpiOut,
    KpiUpdate,
    MeasurementCreate,
    MeasurementOut,
    ObjectiveCreate,
    ObjectiveOut,
    ObjectiveUpdate,
)
from app.modules.execution.schemas.tasks import TaskCreate, TaskOut, TaskUpdate
from app.modules.execution.services.initiative_service import InitiativeService, initiative_out
from app.modules.execution.services.kpi_service import KpiService, kpi_out
from app.modules.execution.services.meeting_service import (
    MeetingService,
    ProjectService,
    decision_out,
    meeting_out,
    project_out,
)
from app.modules.execution.services.okr_service import OkrService, kr_out, objective_out
from app.modules.execution.services.task_service import TaskService, task_out

router = EnvelopeRouter(tags=["execution"])

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_permission("execution:read"))]
Writer = Annotated[Principal, Depends(require_permission("execution:write"))]


# ---------- EP-44 tasks ----------
@router.get("/execution/tasks", response_model=list[TaskOut])
async def list_tasks(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(
        page_params("due_date", "priority", "status", "updated_at", "title")
    )],
    assignee_id: uuid.UUID | None = None, owner_id: uuid.UUID | None = None,
    status: TaskStatus | None = None, overdue: bool | None = None,
    department_id: uuid.UUID | None = None, initiative_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    filters = {
        "assignee_id": assignee_id, "owner_id": owner_id, "status": status,
        "department_id": department_id, "initiative_id": initiative_id, "project_id": project_id,
    }  # fmt: skip
    items, total = await TaskService(db).list_tasks(user, page, filters=filters, overdue=overdue)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/execution/tasks", response_model=TaskOut, status_code=201)
async def create_task(body: TaskCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return TaskOut.model_validate(hit)
    out = await TaskService(db).create(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/execution/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return task_out(await TaskService(db).get(user, task_id))


@router.patch("/execution/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: uuid.UUID, body: TaskUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await TaskService(db).update(user, task_id, body, exp)
    await db.commit()
    return out


@router.delete("/execution/tasks/{task_id}", status_code=204, response_class=Response)
async def delete_task(task_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await TaskService(db).delete(user, task_id)
    await db.commit()
    return Response(status_code=204)


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


# ---------- EP-45 projects ----------
@router.get("/execution/projects", response_model=list[ProjectOut])
async def list_projects(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("start_date", "planned_end_date", "name"))],
    status: ProjectStatus | None = None, department_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    items, total = await ProjectService(db).list_projects(
        user, page, status=status, department_id=department_id
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/execution/projects", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ProjectOut.model_validate(hit)
    out = await ProjectService(db).create_project(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/execution/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return project_out(await ProjectService(db).get_project(user, project_id))


@router.patch("/execution/projects/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID, body: ProjectUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await ProjectService(db).update_project(user, project_id, body, exp)
    await db.commit()
    return out


@router.delete("/execution/projects/{project_id}", status_code=204, response_class=Response)
async def delete_project(project_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await ProjectService(db).delete_project(user, project_id)
    await db.commit()
    return Response(status_code=204)


def _page(items: Any, total: int, page: PageParams) -> Page[Any]:
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


# ---------- EP-46 objectives + key results ----------
@router.get("/execution/objectives", response_model=list[ObjectiveOut])
async def list_objectives(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("period_key", "title", "updated_at"))],
    period_key: str | None = None, owner_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    items, total = await OkrService(db).list_objectives(
        user, page, period_key=period_key, owner_id=owner_id
    )
    return _page(items, total, page)


@router.post("/execution/objectives", response_model=ObjectiveOut, status_code=201)
async def create_objective(body: ObjectiveCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ObjectiveOut.model_validate(hit)
    out = await OkrService(db).create_objective(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/execution/objectives/{objective_id}", response_model=ObjectiveOut)
async def get_objective(objective_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return objective_out(await OkrService(db).get_objective(user, objective_id))


@router.patch("/execution/objectives/{objective_id}", response_model=ObjectiveOut)
async def update_objective(
    objective_id: uuid.UUID, body: ObjectiveUpdate, db: Db, user: Writer,
    if_match: IfMatch = None,
) -> Any:  # fmt: skip
    exp = expected_version(if_match, body.version)
    out = await OkrService(db).update_objective(user, objective_id, body, exp)
    await db.commit()
    return out


@router.delete("/execution/objectives/{objective_id}", status_code=204, response_class=Response)
async def delete_objective(objective_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await OkrService(db).delete_objective(user, objective_id)
    await db.commit()
    return Response(status_code=204)


KR_PATH = "/execution/objectives/{objective_id}/key-results"


@router.get(KR_PATH, response_model=list[KeyResultOut])
async def list_key_results(
    objective_id: uuid.UUID, db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("title", "updated_at"))],
) -> Any:  # fmt: skip
    items, total = await OkrService(db).list_krs(user, objective_id, page)
    return _page(items, total, page)


@router.post(KR_PATH, response_model=KeyResultOut, status_code=201)
async def create_key_result(
    objective_id: uuid.UUID, body: KeyResultCreate, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return KeyResultOut.model_validate(hit)
    out = await OkrService(db).create_kr(user, objective_id, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get(KR_PATH + "/{kr_id}", response_model=KeyResultOut)
async def get_key_result(objective_id: uuid.UUID, kr_id: uuid.UUID, db: Db, user: Reader) -> Any:
    kr = await OkrService(db).get_kr(user, kr_id)
    if kr.objective_id != objective_id:
        raise NotFoundError("key result not found")
    return kr_out(kr)


@router.patch(KR_PATH + "/{kr_id}", response_model=KeyResultOut)
async def update_key_result(
    objective_id: uuid.UUID, kr_id: uuid.UUID, body: KeyResultUpdate, db: Db, user: Writer,
    if_match: IfMatch = None,
) -> Any:  # fmt: skip
    exp = expected_version(if_match, body.version)
    out = await OkrService(db).update_kr(user, objective_id, kr_id, body, exp)
    await db.commit()
    return out


@router.delete(KR_PATH + "/{kr_id}", status_code=204, response_class=Response)
async def delete_key_result(
    objective_id: uuid.UUID, kr_id: uuid.UUID, db: Db, user: Writer
) -> Response:
    await OkrService(db).delete_kr(user, objective_id, kr_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-47 KPIs + measurements ----------
@router.get("/execution/kpis", response_model=list[KpiOut])
async def list_kpis(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("code", "name", "updated_at"))],
    owner_id: uuid.UUID | None = None, metric_code: str | None = None,
) -> Any:  # fmt: skip
    items, total = await KpiService(db).list_kpis(
        user, page, owner_id=owner_id, metric_code=metric_code
    )
    return _page(items, total, page)


@router.post("/execution/kpis", response_model=KpiOut, status_code=201)
async def create_kpi(body: KpiCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return KpiOut.model_validate(hit)
    out = await KpiService(db).create_kpi(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/execution/kpis/{kpi_id}", response_model=KpiOut)
async def get_kpi(kpi_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return kpi_out(await KpiService(db).get_kpi(user, kpi_id))


@router.patch("/execution/kpis/{kpi_id}", response_model=KpiOut)
async def update_kpi(
    kpi_id: uuid.UUID, body: KpiUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await KpiService(db).update_kpi(user, kpi_id, body, exp)
    await db.commit()
    return out


@router.delete("/execution/kpis/{kpi_id}", status_code=204, response_class=Response)
async def delete_kpi(kpi_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await KpiService(db).delete_kpi(user, kpi_id)
    await db.commit()
    return Response(status_code=204)


@router.get("/execution/kpis/{kpi_id}/measurements", response_model=list[MeasurementOut])
async def list_measurements(
    kpi_id: uuid.UUID, db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("period_key", "measured_at"))],
) -> Any:  # fmt: skip
    items, total = await KpiService(db).list_measurements(user, kpi_id, page)
    return _page(items, total, page)


@router.post(
    "/execution/kpis/{kpi_id}/measurements", response_model=MeasurementOut, status_code=201
)
async def create_measurement(
    kpi_id: uuid.UUID, body: MeasurementCreate, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return MeasurementOut.model_validate(hit)
    out = await KpiService(db).measure(user, kpi_id, body)
    await db.commit()
    await idem.remember(out)
    return out


# ---------- EP-48 check-ins ----------
@router.get("/execution/check-ins", response_model=list[CheckInOut])
async def list_check_ins(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("checked_in_at"))],
    owner_id: uuid.UUID | None = None, period_key: str | None = None,
    kpi_id: uuid.UUID | None = None, key_result_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    items, total = await KpiService(db).list_check_ins(
        user, page, owner_id=owner_id, period_key=period_key, kpi_id=kpi_id,
        key_result_id=key_result_id,
    )  # fmt: skip
    return _page(items, total, page)


@router.post("/execution/check-ins", response_model=CheckInOut, status_code=201)
async def create_check_in(body: CheckInCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return CheckInOut.model_validate(hit)
    out = await KpiService(db).check_in(user, body)
    await db.commit()
    await idem.remember(out)
    return out


# ---------- EP-45 initiatives + milestones ----------
@router.get("/execution/initiatives", response_model=list[InitiativeOut])
async def list_initiatives(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(
        page_params("planned_end_date", "start_date", "code", "progress_pct")
    )],
    objective_id: uuid.UUID | None = None, status: InitiativeStatus | None = None,
    pillar: Pillar | None = None,
) -> Any:  # fmt: skip
    items, total = await InitiativeService(db).list_initiatives(
        user, page, objective_id=objective_id, status=status, pillar=pillar
    )
    return _page(items, total, page)


@router.post("/execution/initiatives", response_model=InitiativeOut, status_code=201)
async def create_initiative(body: InitiativeCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return InitiativeOut.model_validate(hit)
    out = await InitiativeService(db).create_initiative(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/execution/initiatives/{initiative_id}", response_model=InitiativeOut)
async def get_initiative(initiative_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return initiative_out(await InitiativeService(db).get_initiative(user, initiative_id))


@router.patch("/execution/initiatives/{initiative_id}", response_model=InitiativeOut)
async def update_initiative(
    initiative_id: uuid.UUID, body: InitiativeUpdate, db: Db, user: Writer,
    if_match: IfMatch = None,
) -> Any:  # fmt: skip
    exp = expected_version(if_match, body.version)
    out = await InitiativeService(db).update_initiative(user, initiative_id, body, exp)
    await db.commit()
    return out


@router.delete("/execution/initiatives/{initiative_id}", status_code=204, response_class=Response)
async def delete_initiative(initiative_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await InitiativeService(db).delete_initiative(user, initiative_id)
    await db.commit()
    return Response(status_code=204)


MS_PATH = "/execution/initiatives/{initiative_id}/milestones"


@router.get(MS_PATH, response_model=list[MilestoneOut])
async def list_milestones(
    initiative_id: uuid.UUID, db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("due_date", "title"))],
) -> Any:  # fmt: skip
    items, total = await InitiativeService(db).list_milestones(user, initiative_id, page)
    return _page(items, total, page)


@router.post(MS_PATH, response_model=MilestoneOut, status_code=201)
async def create_milestone(
    initiative_id: uuid.UUID, body: MilestoneCreate, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return MilestoneOut.model_validate(hit)
    out = await InitiativeService(db).create_milestone(user, initiative_id, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get(MS_PATH + "/{milestone_id}", response_model=MilestoneOut)
async def get_milestone(
    initiative_id: uuid.UUID, milestone_id: uuid.UUID, db: Db, user: Reader
) -> Any:
    return await InitiativeService(db).get_milestone(user, initiative_id, milestone_id)


@router.patch(MS_PATH + "/{milestone_id}", response_model=MilestoneOut)
async def update_milestone(
    initiative_id: uuid.UUID, milestone_id: uuid.UUID, body: MilestoneUpdate, db: Db,
    user: Writer, if_match: IfMatch = None,
) -> Any:  # fmt: skip
    exp = expected_version(if_match, body.version)
    out = await InitiativeService(db).update_milestone(user, initiative_id, milestone_id, body, exp)
    await db.commit()
    return out


@router.delete(MS_PATH + "/{milestone_id}", status_code=204, response_class=Response)
async def delete_milestone(
    initiative_id: uuid.UUID, milestone_id: uuid.UUID, db: Db, user: Writer
) -> Response:
    await InitiativeService(db).delete_milestone(user, initiative_id, milestone_id)
    await db.commit()
    return Response(status_code=204)

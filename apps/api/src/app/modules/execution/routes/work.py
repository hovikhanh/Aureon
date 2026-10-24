"""`/work/*` — D11 Task / Project / Milestone / Workload (10 §7.2.2, R-DEC-40).

EP-TASK-01..05, 09..13 moved from `/execution/{tasks,projects}` with v2.1 behaviour (no alias).
EP-TASK-06..08 dependencies (T-619). EP-TASK-14..19 stubs (`501`) until T-620/T-622. Static paths
(`/work/workload`, `/work/tasks/{id}/dependencies`) are declared before `{id}` catch-alls.
"""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_permission
from app.core.envelope import Page
from app.core.errors import BadRequestError
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.core.stub import not_implemented
from app.modules.execution.schemas.common import ProjectStatus, TaskStatus
from app.modules.execution.schemas.initiatives import MilestoneCreate, MilestoneOut, MilestoneUpdate
from app.modules.execution.schemas.meetings import ProjectCreate, ProjectOut, ProjectUpdate
from app.modules.execution.schemas.tasks import (
    ReassignRequestCreate,
    SourceRefKind,
    TaskCreate,
    TaskDependenciesOut,
    TaskDependencyCreate,
    TaskDependencyOut,
    TaskOut,
    TaskUpdate,
)
from app.modules.execution.schemas.work import ProjectDetailOut, WorkloadOut
from app.modules.execution.services.meeting_service import ProjectService, project_out
from app.modules.execution.services.task_service import TaskService
from app.modules.platform.schemas import ApprovalRequestOut

router = EnvelopeRouter(prefix="/work", tags=["work"])

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_permission("execution:read"))]
Writer = Annotated[Principal, Depends(require_permission("execution:write"))]
Querier = Annotated[Principal, Depends(require_permission("execution:query"))]


# ---------- EP-TASK-18 workload (static path first) ----------
@router.get("/workload", response_model=WorkloadOut, summary="EP-TASK-18 Workload heatmap")
async def get_workload(
    user: Querier, week: str | None = None,
    weeks: Annotated[int, Query(ge=1, le=8)] = 4, department_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    not_implemented("EP-TASK-18", "T-620")


# ---------- EP-TASK-01..05 tasks ----------
@router.get("/tasks", response_model=list[TaskOut], summary="EP-TASK-01 List tasks")
async def list_tasks(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(
        page_params("due_date", "priority", "status", "updated_at", "title")
    )],
    assignee_id: uuid.UUID | None = None, owner_id: uuid.UUID | None = None,
    status: Annotated[list[TaskStatus] | None, Query()] = None, overdue: bool | None = None,
    department_id: uuid.UUID | None = None, initiative_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None, mine: bool = False,
    due_from: date | None = None, due_to: date | None = None,
    parent_task_id: uuid.UUID | None = None, source_kind: SourceRefKind | None = None,
) -> Any:  # fmt: skip
    if due_from is not None and due_to is not None and due_from > due_to:
        raise BadRequestError("due_from must be on/before due_to", details={"param": "due_from"})
    filters = {
        "assignee_id": assignee_id, "owner_id": owner_id, "department_id": department_id,
        "initiative_id": initiative_id, "project_id": project_id,
        "parent_task_id": parent_task_id,
    }  # fmt: skip
    items, total = await TaskService(db).list_tasks(
        user, page, filters=filters, overdue=overdue, statuses=status, mine=mine,
        due_from=due_from, due_to=due_to, source_kind=source_kind,
    )  # fmt: skip
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/tasks", response_model=TaskOut, status_code=201, summary="EP-TASK-02 Create task")
async def create_task(body: TaskCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return TaskOut.model_validate(hit)
    out = await TaskService(db).create(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get(
    "/tasks/{task_id}/dependencies", response_model=TaskDependenciesOut,
    summary="EP-TASK-06 List task dependencies",
)  # fmt: skip
async def list_dependencies(task_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return await TaskService(db).list_dependencies(user, task_id)


@router.post(
    "/tasks/{task_id}/dependencies", response_model=TaskDependencyOut, status_code=201,
    summary="EP-TASK-07 Add task dependency",
)  # fmt: skip
async def create_dependency(
    task_id: uuid.UUID, body: TaskDependencyCreate, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return TaskDependencyOut.model_validate(hit)
    out = await TaskService(db).add_dependency(user, task_id, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.delete(
    "/tasks/{task_id}/dependencies/{dependency_id}", status_code=204, response_class=Response,
    summary="EP-TASK-08 Remove task dependency",
)  # fmt: skip
async def delete_dependency(
    task_id: uuid.UUID, dependency_id: uuid.UUID, db: Db, user: Writer
) -> Response:
    await TaskService(db).remove_dependency(user, task_id, dependency_id)
    await db.commit()
    return Response(status_code=204)


@router.post(
    "/tasks/{task_id}/reassign-requests", response_model=ApprovalRequestOut, status_code=201,
    summary="EP-TASK-19 Request task reassignment",
)  # fmt: skip
async def create_reassign_request(
    task_id: uuid.UUID, body: ReassignRequestCreate, user: Writer, idem: Idem
) -> Any:
    not_implemented("EP-TASK-19", "T-622")


@router.get("/tasks/{task_id}", response_model=TaskOut, summary="EP-TASK-03 Get task")
async def get_task(task_id: uuid.UUID, db: Db, user: Reader) -> Any:
    svc = TaskService(db)
    return await svc.out(await svc.get(user, task_id))


@router.patch("/tasks/{task_id}", response_model=TaskOut, summary="EP-TASK-04 Update task")
async def update_task(
    task_id: uuid.UUID, body: TaskUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await TaskService(db).update(user, task_id, body, exp)
    await db.commit()
    return out


@router.delete(
    "/tasks/{task_id}", status_code=204, response_class=Response, summary="EP-TASK-05 Delete task"
)
async def delete_task(task_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await TaskService(db).delete(user, task_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-TASK-09..13 projects ----------
@router.get("/projects", response_model=list[ProjectOut], summary="EP-TASK-09 List projects")
async def list_projects(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("start_date", "planned_end_date", "name"))],
    status: ProjectStatus | None = None, department_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None, late: bool | None = None,
    initiative_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    # TODO-T-620: `late` / `initiative_id` filters (computed late, column from 0014).
    items, total = await ProjectService(db).list_projects(
        user, page, status=status, department_id=department_id, owner_id=owner_id
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post(
    "/projects", response_model=ProjectOut, status_code=201, summary="EP-TASK-10 Create project"
)
async def create_project(body: ProjectCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ProjectOut.model_validate(hit)
    out = await ProjectService(db).create_project(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get(
    "/projects/{project_id}", response_model=ProjectDetailOut, summary="EP-TASK-11 Get project"
)
async def get_project(project_id: uuid.UUID, db: Db, user: Reader) -> Any:
    p = project_out(await ProjectService(db).get_project(user, project_id))
    # TODO-T-620: fill `milestones` + `task_counts` (ProjectDetailOut defaults are empty).
    return ProjectDetailOut(**p.model_dump())


@router.patch(
    "/projects/{project_id}", response_model=ProjectOut, summary="EP-TASK-12 Update project"
)
async def update_project(
    project_id: uuid.UUID, body: ProjectUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await ProjectService(db).update_project(user, project_id, body, exp)
    await db.commit()
    return out


@router.delete(
    "/projects/{project_id}", status_code=204, response_class=Response,
    summary="EP-TASK-13 Delete project",
)  # fmt: skip
async def delete_project(project_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await ProjectService(db).delete_project(user, project_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-TASK-14..17 milestones per project (stubs → T-620) ----------
MS_PATH = "/projects/{project_id}/milestones"


@router.get(MS_PATH, response_model=list[MilestoneOut], summary="EP-TASK-14 List milestones")
async def list_project_milestones(project_id: uuid.UUID, user: Reader) -> Any:
    not_implemented("EP-TASK-14", "T-620")


@router.post(
    MS_PATH, response_model=MilestoneOut, status_code=201, summary="EP-TASK-15 Create milestone"
)
async def create_project_milestone(
    project_id: uuid.UUID, body: MilestoneCreate, user: Writer, idem: Idem
) -> Any:
    not_implemented("EP-TASK-15", "T-620")


@router.patch(
    MS_PATH + "/{milestone_id}", response_model=MilestoneOut, summary="EP-TASK-16 Update milestone"
)
async def update_project_milestone(
    project_id: uuid.UUID, milestone_id: uuid.UUID, body: MilestoneUpdate, user: Writer,
    if_match: IfMatch = None,
) -> Any:  # fmt: skip
    not_implemented("EP-TASK-16", "T-620")


@router.delete(
    MS_PATH + "/{milestone_id}", status_code=204, response_class=Response,
    summary="EP-TASK-17 Delete milestone",
)  # fmt: skip
async def delete_project_milestone(
    project_id: uuid.UUID, milestone_id: uuid.UUID, user: Writer
) -> Response:
    not_implemented("EP-TASK-17", "T-620")

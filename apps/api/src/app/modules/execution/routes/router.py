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
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.execution.schemas.common import DecisionStatus, ProjectStatus, TaskStatus
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
from app.modules.execution.schemas.tasks import TaskCreate, TaskOut, TaskUpdate
from app.modules.execution.services.meeting_service import (
    MeetingService,
    ProjectService,
    decision_out,
    meeting_out,
    project_out,
)
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

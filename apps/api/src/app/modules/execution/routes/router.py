"""HTTP routes for `execution` — EP-42..49 (10 §3.4, §4.4).

Same pattern as sales: one permission per route, `Idem` on create POSTs, `IfMatch` + body
`version` on PATCH, `Page` on lists, commit at the end of the request.
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
from app.modules.execution.schemas.common import TaskStatus
from app.modules.execution.schemas.tasks import TaskCreate, TaskOut, TaskUpdate
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

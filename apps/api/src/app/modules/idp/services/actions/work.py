"""ACT-create_task → `execution` `TaskService.create` (10 §7.2.4; doc #1/#2 + AI L2/L3).

M1.6 (T-645, 10 §7.2.5): `ACT-update_task` / `ACT-assign_task` → `TaskService.update` (AI only).
`run` keeps the pre-write snapshot of the changed fields; `undo` writes them back at the version
the action left (a later human edit → `409`, never silently overwritten).

Two callers share the ACT: a document (`assignee_code`, `kr_ref`/`kpi_code`, provenance
`task_source="document"`, `source_ref={kind: document, id}`) and an AI action (`TaskCreate`-shaped
input; provenance forced to `task_source="ai"`, `source_ref={kind: ai_action, id}` — the AI
cannot claim another origin, 05 §2.5).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import NotFoundError
from app.modules.execution.schemas.tasks import TaskCreate, TaskUpdate
from app.modules.execution.services.kpi_service import KpiService
from app.modules.execution.services.task_service import TaskService
from app.modules.hr.services.hr_service import HrService
from app.modules.idp.services.actions.registry import (
    ActionContext,
    ActionDef,
    ActionOutcome,
    RowError,
    ref,
    register,
)


class TaskParams(BaseModel):
    """Document params; AI input passes the `TaskCreate` fields through (`extra="allow"`)."""

    model_config = ConfigDict(extra="allow")

    title: str = Field(min_length=1, max_length=500)
    assignee_code: str | None = Field(default=None, max_length=50)
    due_date: date | None = None
    kr_ref: uuid.UUID | None = None
    kpi_code: str | None = Field(default=None, max_length=50)


async def _validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    errors: list[RowError] = []
    if p.assignee_code and not (
        ctx.is_planned("employee", p.assignee_code)
        or await HrService(db).employee_id_by_code(p.assignee_code)
    ):
        errors.append({"field": "assignee_code", "code": "not_found",
                       "message": f"employee {p.assignee_code} not found"})  # fmt: skip
    if p.kpi_code and not (
        ctx.is_planned("kpi", p.kpi_code) or await KpiService(db).kpi_id_by_code(p.kpi_code)
    ):
        errors.append({"field": "kpi_code", "code": "not_found",
                       "message": f"KPI {p.kpi_code} not found"})  # fmt: skip
    return errors


async def _document_body(db: AsyncSession, p: Any, ctx: ActionContext) -> TaskCreate:
    assignee = None
    if p.assignee_code:
        assignee = ctx.recall("employee", p.assignee_code) or await HrService(
            db
        ).employee_id_by_code(p.assignee_code)
        if assignee is None:
            raise NotFoundError("assignee not found", details={"field": "assignee_code"})
    kpi = None
    if p.kpi_code:
        kpi = ctx.recall("kpi", p.kpi_code) or await KpiService(db).kpi_id_by_code(p.kpi_code)
    source_ref = None
    if ctx.source_document_id is not None:
        source_ref = {"kind": "document", "id": str(ctx.source_document_id)}
    return TaskCreate.model_validate({
        "title": p.title, "assignee_id": assignee, "due_date": p.due_date,
        "key_result_id": p.kr_ref, "kpi_id": kpi, "source_document_id": ctx.source_document_id,
        "task_source": "document" if source_ref else "manual", "source_ref": source_ref,
    })  # fmt: skip


async def _run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    if ctx.ai_action_id is not None:
        raw = p.model_dump(exclude_none=True, exclude={"assignee_code", "kr_ref", "kpi_code"})
        body = TaskCreate.model_validate({
            **raw, "task_source": "ai",
            "source_ref": {"kind": "ai_action", "id": str(ctx.ai_action_id)},
        })  # fmt: skip
    else:
        body = await _document_body(db, p, ctx)
    out = await TaskService(db).create(user, body, source=ctx.source)
    return ActionOutcome([ref("execution", "tasks", out.id)], target_version=out.version)


async def _undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    try:
        await TaskService(db).delete(user, uuid.UUID(outcome.result_refs[0]["id"]))
    except NotFoundError:
        return  # already gone


register(ActionDef(
    name="ACT-create_task", module="execution", required_permission=("execution:write",),
    reversible=True, is_finance=False, params_model=TaskParams, validate=_validate, run=_run,
    undo=_undo,
))  # fmt: skip


# ---------------------------------------------------------------- M1.6 update / assign (T-645)
class UpdateTaskParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: uuid.UUID
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    due_date: date | None = None
    priority: str | None = None
    status: str | None = None


class AssignTaskParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: uuid.UUID
    assignee_code: str = Field(min_length=1, max_length=50)


async def _no_errors(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    return []


async def _validate_assign(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    if await HrService(db).employee_id_by_code(p.assignee_code):
        return []
    return [{"field": "assignee_code", "code": "not_found",
             "message": f"employee {p.assignee_code} not found"}]  # fmt: skip


async def _patch(
    db: AsyncSession, user: Principal, task_id: uuid.UUID, changes: dict[str, Any]
) -> ActionOutcome:
    svc = TaskService(db)
    current = await svc.out(await svc.get(user, task_id, "write"))
    snapshot = {k: getattr(current, k) for k in changes}
    body = TaskUpdate.model_validate({**changes, "version": current.version})
    out = await svc.update(user, task_id, body, current.version)
    return ActionOutcome([ref("execution", "tasks", out.id)],
                         snapshot=TaskUpdate.model_validate(snapshot).model_dump(
                             mode="json", exclude_unset=True, exclude={"version"}),
                         target_version=out.version)  # fmt: skip


async def _run_update(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> ActionOutcome:
    changes = p.model_dump(exclude_none=True, exclude={"task_id"})
    return await _patch(db, user, p.task_id, changes)


async def _run_assign(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> ActionOutcome:
    assignee = await HrService(db).employee_id_by_code(p.assignee_code)
    if assignee is None:
        raise NotFoundError("assignee not found", details={"field": "assignee_code"})
    return await _patch(db, user, p.task_id, {"assignee_id": assignee})


async def _undo_snapshot(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    task_id = uuid.UUID(outcome.result_refs[0]["id"])
    version = int(outcome.target_version or 0)
    body = TaskUpdate.model_validate({**(outcome.snapshot or {}), "version": version})
    await TaskService(db).update(user, task_id, body, version)


register(ActionDef(
    name="ACT-update_task", module="execution", required_permission=("execution:write",),
    reversible=True, is_finance=False, params_model=UpdateTaskParams, validate=_no_errors,
    run=_run_update, undo=_undo_snapshot,
))  # fmt: skip
register(ActionDef(
    name="ACT-assign_task", module="execution", required_permission=("execution:write",),
    reversible=True, is_finance=False, params_model=AssignTaskParams, validate=_validate_assign,
    run=_run_assign, undo=_undo_snapshot,
))  # fmt: skip

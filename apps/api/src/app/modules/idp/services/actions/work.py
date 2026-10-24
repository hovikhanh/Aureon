"""ACT-create_task → `execution` `TaskService.create` (10 §7.2.4; doc #1/#2 + AI L2/L3).

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
from app.modules.execution.schemas.tasks import TaskCreate
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

"""ACT-create_action_item / ACT-create_task_from_action_item → `execution` `MeetingService`
(10 §7, M2.3 R-DEC-101; doc type #1 "Biên bản họp").

`create_action_item` writes an `ActionItem` (no Task) at doc commit — undo soft-deletes it.
`create_task_from_action_item` turns an approved item into a Task (chair approval is enforced at
the review/ACT layer) — undo deletes the Task and clears `ActionItem.task_id`.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import BusinessRuleError
from app.modules.execution.services.meeting_service import MeetingService
from app.modules.idp.services.actions.finance import as_date, as_str
from app.modules.idp.services.actions.registry import (
    ActionContext,
    ActionDef,
    ActionOutcome,
    RowError,
    ref,
    register,
)


class ActionItemParams(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: Any = None
    owner_name: Any = None
    due_date: Any = None


async def _validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    if not as_str(p.title):
        return [{"field": "title", "code": "empty", "message": "action item title is required"}]
    return []


async def _run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    ai = await MeetingService(db).create_action_item(
        user, title=as_str(p.title) or "", owner_name=as_str(p.owner_name),
        due_date=as_date(p.due_date), source_document_id=ctx.source_document_id,
    )  # fmt: skip
    return ActionOutcome([ref("execution", "action_items", ai.id)])


async def _undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    await MeetingService(db).delete_action_item(user, uuid.UUID(outcome.result_refs[0]["id"]))


register(ActionDef(
    name="ACT-create_action_item", module="execution",
    required_permission=("execution:write",), reversible=True, is_finance=False,
    params_model=ActionItemParams, validate=_validate, run=_run, undo=_undo,
))  # fmt: skip


class TaskFromActionItemParams(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action_item_ref: Any = None


def _as_uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


async def _validate_task(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    if _as_uuid(p.action_item_ref) is None:
        return [{"field": "action_item_ref", "code": "invalid_uuid",
                 "message": "action_item_ref must be a UUID"}]  # fmt: skip
    return []


async def _run_task(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    action_item_id = _as_uuid(p.action_item_ref)
    if action_item_id is None:  # guarded by _validate_task; defensive for a direct _run
        raise BusinessRuleError(
            "action_item_ref must be a UUID", details={"field": "action_item_ref"}
        )
    task = await MeetingService(db).create_task_from_action_item(user, action_item_id)
    return ActionOutcome([ref("execution", "tasks", task.id)], target_version=task.version)


async def _undo_task(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    await MeetingService(db).detach_task(user, uuid.UUID(outcome.result_refs[0]["id"]))


register(ActionDef(
    name="ACT-create_task_from_action_item", module="execution",
    required_permission=("execution:write",), reversible=True, is_finance=False,
    params_model=TaskFromActionItemParams, validate=_validate_task, run=_run_task,
    undo=_undo_task,
))  # fmt: skip

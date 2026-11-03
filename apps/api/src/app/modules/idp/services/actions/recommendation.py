"""ACT-execute_recommendation (M3.2, T-812, R-DEC-127) — the single Autonomy-L3 composite that
closes the CEO loop step 5 (Act): in **one transaction** it creates a Task (owner + deadline), an
internal CalendarEvent for the caller, and a Notification ("AI đã làm"). The whole thing runs
through the Action Registry v2 so the existing L3 auto-execute + 24h-undo lifecycle
(`ai/services/action_service.py`) applies unchanged.

Cross-module writes reuse the **public services** of the target modules on the Action Registry's
`AsyncSession` (DEC-125): `execution` `TaskService` + `CalendarService`, `platform`
`NotificationService`. `idp` already imports other modules' services in the sibling `work.py`/
`finance.py` action files — the import-boundary test counts these as `idp → <module>.services`
(public, allowed).

`undo` reverses the reversible effects in reverse order: soft-delete the CalendarEvent (which
publishes `execution.calendar_event_changed change=deleted` → the M3.1 push consumer withdraws any
event already pushed to Google/Outlook — R-DEC-129, no provider call in-request) then soft-delete
the Task. The Notification is an append-only `LogModel` record of what the AI did and is not
reversed (02 §6 — undo does not apply to effects that cannot be undone); the `ai.action_undone`
audit + the reversal itself are the trail.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import NotFoundError
from app.modules.execution.schemas.calendar import CalendarEventCreate
from app.modules.execution.schemas.tasks import TaskCreate
from app.modules.execution.services.calendar_service import CalendarService
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
from app.modules.platform.services.notification_service import NotificationService


class ExecuteRecommendationParams(BaseModel):
    """L3 recommendation → task + calendar + notify (R-DEC-127). Calendar fields optional; when
    `starts_at` is omitted the event anchors on the task's `due_date` (09:00 local-naive UTC)."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    assignee_code: str | None = Field(default=None, max_length=50)
    due_date: date | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    description: str | None = Field(default=None, max_length=10000)


async def _validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    errors: list[RowError] = []
    if p.assignee_code and not await HrService(db).employee_id_by_code(p.assignee_code):
        errors.append({"field": "assignee_code", "code": "not_found",
                       "message": f"employee {p.assignee_code} not found"})  # fmt: skip
    if p.starts_at is None and p.due_date is None:
        errors.append({"field": "starts_at", "code": "required",
                       "message": "need starts_at or due_date for the calendar event"})  # fmt: skip
    return errors


def _event_start(p: Any) -> datetime:
    starts_at: datetime | None = p.starts_at
    if starts_at is not None:
        return starts_at
    due: date = p.due_date
    return datetime.combine(due, datetime.min.time().replace(hour=9))


async def _run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    assignee_id = (
        await HrService(db).employee_id_by_code(p.assignee_code) if p.assignee_code else None
    )
    if p.assignee_code and assignee_id is None:
        raise NotFoundError("assignee not found", details={"field": "assignee_code"})
    ai_ref = {"kind": "ai_action", "id": str(ctx.ai_action_id)} if ctx.ai_action_id else None

    # 1) Task — provenance forced to AI (05 §2.5), owner = caller, assignee + deadline from params.
    task = await TaskService(db).create(
        user,
        TaskCreate.model_validate({
            "title": p.title, "description": p.description, "assignee_id": assignee_id,
            "owner_id": user.user_id, "due_date": p.due_date, "task_source": "ai",
            "source_ref": ai_ref,
        }),
        source=ctx.source,
    )  # fmt: skip

    # 2) Internal CalendarEvent for the caller, linked to the task (Confidential, R-DEC-123).
    event = await CalendarService(db).create_event(
        user,
        CalendarEventCreate(
            title=p.title, starts_at=_event_start(p), ends_at=p.ends_at,
            description=p.description, task_id=task.id,
        ),
    )  # fmt: skip

    # 3) Notification to the caller ("AI đã làm" — L3 Act & Notify).
    notif_id = await NotificationService(db).create(
        recipient_id=user.user_id,
        kind="system",
        title=p.title,
        body="AI đã tạo việc và đặt lịch theo khuyến nghị.",
        link=f"/work?task={task.id}",
        ref_schema="execution",
        ref_table="tasks",
        ref_id=task.id,
    )

    return ActionOutcome(
        [
            ref("execution", "tasks", task.id),
            ref("execution", "calendar_events", event.id),
            ref("platform", "notifications", notif_id),
        ],
        target_version=task.version,
    )


async def _undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    by_table = {r["table"]: uuid.UUID(r["id"]) for r in outcome.result_refs}
    # Reverse order: calendar first (publishes change=deleted → provider withdrawal), then task.
    if "calendar_events" in by_table:
        try:
            await CalendarService(db).delete_event(user, by_table["calendar_events"])
        except NotFoundError:
            pass
    if "tasks" in by_table:
        try:
            await TaskService(db).delete(user, by_table["tasks"])
        except NotFoundError:
            pass


register(ActionDef(
    name="ACT-execute_recommendation", module="execution",
    required_permission=("execution:write",), reversible=True, is_finance=False,
    params_model=ExecuteRecommendationParams, validate=_validate, run=_run, undo=_undo,
))  # fmt: skip

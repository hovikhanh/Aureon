"""EP-44 tasks (T-131, T-133): CRUD, 7-status transitions (DEC-147), overdue job.

`detect_overdue_tasks(db, as_of)` is the daily job body: open tasks with `due_date < as_of`
publish `EVT-execution.task_overdue` once — `overdue_notified_at` marks the task; moving
`due_date` re-arms it. Caller commits.
"""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import Actor, record_audit
from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ConflictStateError
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.execution.models import Task
from app.modules.execution.repositories import OPEN_TASK_STATUSES, TaskRepository
from app.modules.execution.schemas.tasks import TaskCreate, TaskOut, TaskUpdate
from app.modules.execution.services import scope
from app.modules.execution.services.base import ExecBase, not_found, now_utc, num, today
from app.modules.execution.services.initiative_service import InitiativeService
from app.modules.execution.services.task_rules import can_transition, is_overdue

RULE = "FR-TASK-01"
NOT_NULL = frozenset({"title", "priority", "status", "is_critical"})


def task_out(t: Task, as_of: date | None = None) -> TaskOut:
    return TaskOut(
        id=t.id, version=t.version, source=t.source, data_classification=t.data_classification,
        created_at=t.created_at, updated_at=t.updated_at, title=t.title,
        description=t.description, owner_id=t.owner_id, assignee_id=t.assignee_id,
        department_id=t.department_id, start_date=t.start_date, due_date=t.due_date,
        priority=t.priority, status=t.status, blocked_reason=t.blocked_reason,
        done_at=t.done_at, estimate_hours=num(t.estimate_hours),
        actual_hours=num(t.actual_hours), evidence=t.evidence, project_id=t.project_id,
        initiative_id=t.initiative_id, milestone_id=t.milestone_id, meeting_id=t.meeting_id,
        decision_id=t.decision_id, key_result_id=t.key_result_id, kpi_id=t.kpi_id,
        parent_id=t.parent_id, is_critical=t.is_critical, task_source=t.task_source,
        source_document_id=t.source_document_id,
        overdue=is_overdue(t.status, t.due_date, as_of or today()),
    )  # fmt: skip


def _own(user: Principal) -> list[ColumnElement[bool]]:
    return [Task.owner_id == user.user_id, Task.assignee_id == user.user_id]


def _check_dates(start: date | None, due: date | None) -> None:
    if start is not None and due is not None and due < start:
        raise BusinessRuleError(
            "due_date must be on/after start_date", details={"field": "due_date", "rule": RULE}
        )


class TaskService(ExecBase):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.tasks = TaskRepository(db)

    async def list_tasks(
        self, user: Principal, page: PageParams, *, filters: dict[str, Any],
        overdue: bool | None,
    ) -> tuple[list[TaskOut], int]:  # fmt: skip
        where: list[ColumnElement[bool]] = []
        pred = scope.predicate(user, "read", dept=Task.department_id, own=_own(user))
        if pred is not None:
            where.append(pred)
        as_of = today()
        if overdue is True:
            where += [Task.due_date < as_of, Task.status.in_(OPEN_TASK_STATUSES)]
        elif overdue is False:
            where.append(~(Task.due_date < as_of) | ~Task.status.in_(OPEN_TASK_STATUSES)
                         | Task.due_date.is_(None))  # fmt: skip
        items, total = await self.tasks.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters={k: v for k, v in filters.items() if v is not None}, where=where,
        )  # fmt: skip
        return [task_out(t, as_of) for t in items], total

    async def get(self, user: Principal, id_: uuid.UUID, action: str = "read") -> Task:
        t = await self.tasks.get(id_)
        if t is None:
            raise not_found("task")
        scope.check(user, action, dept=t.department_id, owners=(t.owner_id, t.assignee_id),
                    what="task")  # fmt: skip
        return t

    async def create(self, user: Principal, body: TaskCreate) -> TaskOut:
        data = body.model_dump(mode="python")
        data["owner_id"] = data["owner_id"] or user.user_id
        if scope.level(user, "write") == "o" and data["assignee_id"] is None:
            data["assignee_id"] = user.user_id
        scope.require_self(user, data["owner_id"], data["assignee_id"], field="assignee_id")
        data["department_id"] = scope.pin_department(user, data["department_id"])
        _check_dates(data["start_date"], data["due_date"])
        self._status_fields(data, None, data["status"])
        await self.require_refs(data, RULE, parent_id=Task)
        if data["evidence"] is not None:
            data["evidence"] = [dict(e) for e in data["evidence"]]
        t = await self.tasks.create(**data, source="MANUAL", created_by=user.user_id)
        await self._progress(t.initiative_id)
        await self.db.refresh(t)
        out = task_out(t)
        await self.audit("task_create", "tasks", t.id, after=out)
        return out

    @staticmethod
    def _status_fields(data: dict[str, Any], current: Task | None, status: str) -> None:
        src = current.status if current is not None else None
        if src is not None and not can_transition(src, status):
            raise ConflictStateError(
                f"cannot move task from {src} to {status}",
                details={"from_status": src, "to_status": status},
            )
        if status == "blocked":
            reason = data.get("blocked_reason") or (current.blocked_reason if current else None)
            if not reason:
                raise BusinessRuleError(
                    "blocked requires blocked_reason",
                    details={"field": "blocked_reason", "rule": "DEC-147"},
                )
        elif src != status or current is None:
            data["blocked_reason"] = None
        if status == "done" and (current is None or current.status != "done"):
            data["done_at"] = now_utc()
        elif status != "done":
            data["done_at"] = None

    async def update(
        self, user: Principal, id_: uuid.UUID, body: TaskUpdate, expected: int
    ) -> TaskOut:
        t = await self.get(user, id_, "write")
        before = task_out(t)
        data = body.model_dump(mode="python", exclude_unset=True, exclude={"version"})
        scope.require_self(user, data.get("owner_id"), data.get("assignee_id"), field="assignee_id")
        if "department_id" in data:
            data["department_id"] = scope.pin_department(user, data["department_id"])
        _check_dates(data.get("start_date", t.start_date), data.get("due_date", t.due_date))
        if "status" in data or "blocked_reason" in data:
            self._status_fields(data, t, data.get("status") or t.status)
        if data.get("parent_id") == t.id:
            raise BusinessRuleError("task cannot be its own parent",
                                    details={"field": "parent_id", "rule": RULE})  # fmt: skip
        await self.require_refs(data, RULE, parent_id=Task)
        if data.get("evidence") is not None:
            data["evidence"] = [dict(e) for e in data["evidence"]]
        if "due_date" in data and data["due_date"] != t.due_date:
            data["overdue_notified_at"] = None  # re-arm EVT-execution.task_overdue
        data = {k: v for k, v in data.items() if k not in NOT_NULL or v is not None}
        old_initiative = t.initiative_id
        await self.tasks.update(t, expected_version=expected, updated_by=user.user_id, **data)
        await self._progress(old_initiative, t.initiative_id)
        await self.db.refresh(t)
        out = task_out(t)
        await self.audit("task_update", "tasks", t.id, before, out)
        return out

    async def delete(self, user: Principal, id_: uuid.UUID) -> None:
        t = await self.get(user, id_, "write")
        before = task_out(t)
        t.updated_by = user.user_id
        await self.tasks.soft_delete(t)
        await self._progress(t.initiative_id)
        await self.audit("task_delete", "tasks", t.id, before=before)

    async def _progress(self, *initiative_ids: uuid.UUID | None) -> None:
        """Initiative `progress_pct` falls back to task completion (DEC-225)."""
        svc = InitiativeService(self.db)
        for iid in dict.fromkeys(initiative_ids):
            await svc.recompute_progress(iid)

    async def detect_overdue(self, as_of: date) -> list[uuid.UUID]:
        found: list[uuid.UUID] = []
        stamp = now_utc()
        for t in await self.tasks.overdue_unnotified(as_of):
            t.overdue_notified_at = stamp
            payload = {
                "task_id": str(t.id),
                "assignee_id": str(t.assignee_id) if t.assignee_id else None,
                "department_id": str(t.department_id) if t.department_id else None,
                "due_date": t.due_date.isoformat() if t.due_date else None,
            }
            await publish_in_tx(
                self.db, event_type="execution.task_overdue", producer="execution",
                aggregate_schema="execution", aggregate_table="tasks", aggregate_id=t.id,
                payload=payload,
            )  # fmt: skip
            await record_audit(
                self.db, action="execution.task_overdue", target_schema="execution",
                target_table="tasks", target_id=t.id,
                after={"days_late": (as_of - t.due_date).days if t.due_date else None},
                actor=Actor(type="SYSTEM"),
            )  # fmt: skip
            found.append(t.id)
        await self.db.flush()
        return found


async def detect_overdue_tasks(db: AsyncSession, as_of: date) -> list[uuid.UUID]:
    """Public job entry (EVT-execution.task_overdue): caller commits; safe to rerun."""
    return await TaskService(db).detect_overdue(as_of)

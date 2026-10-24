"""EP-TASK-01..05 tasks (T-131, T-133, T-619): CRUD, 7-status transitions (DEC-147), sub-task
one level (R-DEC-42), `source_ref` (05 §2.5), dependency gate on `done` (R-DEC-43), overdue job.

`detect_overdue_tasks(db, as_of)` is the daily job body: open tasks with `due_date < as_of`
publish `EVT-execution.task_overdue` once — `overdue_notified_at` marks the task; moving
`due_date` re-arms it. Caller commits.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, date
from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.approval_hooks import register_approval_hook
from app.core.audit import Actor, record_audit
from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ConflictStateError, DuplicateResourceError
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.execution.models import Task, TaskDependency
from app.modules.execution.repositories import (
    OPEN_TASK_STATUSES,
    TaskDependencyRepository,
    TaskRepository,
)
from app.modules.execution.schemas.tasks import (
    ReassignRequestCreate,
    SourceRef,
    TaskBriefOut,
    TaskCreate,
    TaskDependenciesOut,
    TaskDependencyCreate,
    TaskDependencyOut,
    TaskOut,
    TaskUpdate,
)
from app.modules.execution.services import scope
from app.modules.execution.services.base import ExecBase, not_found, now_utc, num, today
from app.modules.execution.services.initiative_service import InitiativeService
from app.modules.execution.services.task_rules import (
    CLOSED,
    MAX_DEPENDENCY_DEPTH,
    can_transition,
    find_cycle,
    is_overdue,
    source_kind_matches,
)
from app.modules.platform.schemas import ApprovalRequestOut
from app.modules.platform.services.approval_service import ApprovalService

RULE = "FR-TASK-01"
NOT_NULL = frozenset({"title", "priority", "status", "is_critical"})


def task_out(
    t: Task, as_of: date | None = None, *, subtasks: int = 0, blockers: int = 0
) -> TaskOut:
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
        parent_task_id=t.parent_task_id, is_critical=t.is_critical, task_source=t.task_source,
        source_ref=SourceRef.model_validate(t.source_ref) if t.source_ref else None,
        source_document_id=t.source_document_id,
        overdue=is_overdue(t.status, t.due_date, as_of or today()),
        subtask_count=subtasks, depends_on_open=blockers,
    )  # fmt: skip


def _s(v: uuid.UUID | None) -> str | None:
    return str(v) if v is not None else None


def _own(user: Principal) -> list[ColumnElement[bool]]:
    me = scope.self_ids(user)
    return [Task.owner_id.in_(me), Task.assignee_id.in_(me)]


def _check_source(source_ref: dict[str, Any] | None, task_source: str) -> None:
    """05 §2.5: `source_ref.kind` must agree with `task_source` → else 422."""
    if source_ref is not None and not source_kind_matches(source_ref["kind"], task_source):
        raise BusinessRuleError(
            "source_ref.kind does not match task_source",
            details={"field": "source_ref", "kind": source_ref["kind"],
                     "task_source": task_source, "rule": RULE},
        )  # fmt: skip


def _check_dates(start: date | None, due: date | None) -> None:
    if start is not None and due is not None and due < start:
        raise BusinessRuleError(
            "due_date must be on/after start_date", details={"field": "due_date", "rule": RULE}
        )


class TaskService(ExecBase):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.tasks = TaskRepository(db)
        self.deps = TaskDependencyRepository(db)

    async def outs(self, items: Sequence[Task], as_of: date | None = None) -> list[TaskOut]:
        """`TaskOut` + `subtask_count` / `depends_on_open` (EP-TASK-03) in two grouped queries."""
        ids = [t.id for t in items]
        subs = await self.tasks.count_by(Task.parent_task_id, ids)
        blockers = await self.deps.open_blockers(ids)
        day = as_of or today()
        return [task_out(t, day, subtasks=subs.get(t.id, 0), blockers=blockers.get(t.id, 0))
                for t in items]  # fmt: skip

    async def out(self, t: Task) -> TaskOut:
        return (await self.outs([t]))[0]

    async def list_tasks(
        self, user: Principal, page: PageParams, *, filters: dict[str, Any],
        overdue: bool | None, statuses: Sequence[str] | None = None, mine: bool = False,
        due_from: date | None = None, due_to: date | None = None, source_kind: str | None = None,
    ) -> tuple[list[TaskOut], int]:  # fmt: skip
        where: list[ColumnElement[bool]] = []
        pred = scope.predicate(user, "read", dept=Task.department_id, own=_own(user))
        if pred is not None:
            where.append(pred)
        if statuses:
            where.append(Task.status.in_(statuses))
        if mine:  # R-DEC-41: assignee = employee id (or legacy user id)
            where.append(Task.assignee_id.in_(scope.self_ids(user)))
        if due_from is not None:
            where.append(Task.due_date >= due_from)
        if due_to is not None:
            where.append(Task.due_date <= due_to)
        if source_kind is not None:
            where.append(Task.source_ref["kind"].astext == source_kind)
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
        return await self.outs(items, as_of), total

    async def get(self, user: Principal, id_: uuid.UUID, action: str = "read") -> Task:
        """Read by id outside scope → 404 (10 §7.2.2); write outside scope → 403."""
        t = await self.tasks.get(id_)
        if t is None:
            raise not_found("task")
        owners = (t.owner_id, t.assignee_id)
        if action == "read" and not scope.allowed(user, "read", dept=t.department_id,
                                                  owners=owners):  # fmt: skip
            raise not_found("task")
        scope.check(user, action, dept=t.department_id, owners=owners, what="task")
        return t

    async def _check_parent(self, parent_id: uuid.UUID | None, child: Task | None) -> None:
        """R-DEC-42: one level — the parent has no parent; a task with sub-tasks has no parent."""
        if parent_id is None:
            return
        rule = {"field": "parent_task_id", "rule": "R-DEC-42"}
        if child is not None and parent_id == child.id:
            raise BusinessRuleError("task cannot be its own parent", details=rule)
        parent = await self.tasks.get(parent_id)
        if parent is None:
            raise BusinessRuleError("parent_task_id does not exist", details=rule)
        if parent.parent_task_id is not None:
            raise BusinessRuleError("parent task is already a sub-task", details=rule)
        if child is not None and (await self.tasks.count_by(Task.parent_task_id, [child.id])):
            raise BusinessRuleError("task with sub-tasks cannot become a sub-task", details=rule)

    async def create(self, user: Principal, body: TaskCreate) -> TaskOut:
        data = body.model_dump(mode="python")
        data["owner_id"] = data["owner_id"] or user.user_id
        if scope.level(user, "write") == "o" and data["assignee_id"] is None:
            data["assignee_id"] = scope.self_assignee(user)
        scope.require_self(user, data["owner_id"], data["assignee_id"], field="assignee_id")
        data["department_id"] = scope.pin_department(user, data["department_id"])
        _check_dates(data["start_date"], data["due_date"])
        _check_source(data["source_ref"], data["task_source"])
        self._status_fields(data, None, data["status"])
        await self.require_refs(data, RULE)
        await self._check_parent(data["parent_task_id"], None)
        if data["evidence"] is not None:
            data["evidence"] = [dict(e) for e in data["evidence"]]
        if data["source_ref"] is not None:
            data["source_ref"] = body.source_ref.model_dump(mode="json", exclude_none=True)  # type: ignore[union-attr]
        t = await self.tasks.create(**data, source="MANUAL", created_by=user.user_id)
        await self._progress(t.initiative_id)
        await self.db.refresh(t)
        out = await self.out(t)
        await self.audit("task_create", "tasks", t.id, after=out)
        await self._emit("execution.task_created", t, {
            "parent_task_id": _s(t.parent_task_id), "task_source": t.task_source,
            "source_ref_kind": (t.source_ref or {}).get("kind"),
        })  # fmt: skip
        return out

    async def _emit(self, event_type: str, t: Task, extra: dict[str, Any]) -> None:
        """Outbox event in the caller's tx (10 §9.2, R-DEC-47) — ids only, no `title`/PII."""
        payload = {
            "task_id": str(t.id), "assignee_id": _s(t.assignee_id),
            "department_id": _s(t.department_id), "project_id": _s(t.project_id),
            "due_date": t.due_date.isoformat() if t.due_date else None, **extra,
        }  # fmt: skip
        await publish_in_tx(
            self.db, event_type=event_type, producer="execution", aggregate_schema="execution",
            aggregate_table="tasks", aggregate_id=t.id, payload=payload,
        )  # fmt: skip

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
        before = await self.out(t)
        data = body.model_dump(mode="python", exclude_unset=True, exclude={"version"})
        scope.require_self(user, data.get("owner_id"), data.get("assignee_id"), field="assignee_id")
        if "department_id" in data:
            data["department_id"] = scope.pin_department(user, data["department_id"])
        _check_dates(data.get("start_date", t.start_date), data.get("due_date", t.due_date))
        if "source_ref" in data or "task_source" in data:
            _check_source(data.get("source_ref", t.source_ref), t.task_source)
        if "status" in data or "blocked_reason" in data:
            self._status_fields(data, t, data.get("status") or t.status)
        if data.get("status") == "done" and t.status != "done":
            await self._require_unblocked(t)
        if "parent_task_id" in data:
            await self._check_parent(data["parent_task_id"], t)
        await self.require_refs(data, RULE)
        if data.get("evidence") is not None:
            data["evidence"] = [dict(e) for e in data["evidence"]]
        if data.get("source_ref") is not None:
            data["source_ref"] = body.source_ref.model_dump(mode="json", exclude_none=True)  # type: ignore[union-attr]
        if "due_date" in data and data["due_date"] != t.due_date:
            data["overdue_notified_at"] = None  # re-arm EVT-execution.task_overdue
        data = {k: v for k, v in data.items() if k not in NOT_NULL or v is not None}
        old_initiative, old_status = t.initiative_id, t.status
        await self.tasks.update(t, expected_version=expected, updated_by=user.user_id, **data)
        await self._progress(old_initiative, t.initiative_id)
        await self.db.refresh(t)
        out = await self.out(t)
        await self.audit("task_update", "tasks", t.id, before, out)
        if t.status == "done" and old_status != "done":
            await self._completed(t)
        return out

    async def _completed(self, t: Task) -> None:
        """`execution.task_completed` (R-DEC-47); `on_time` = same rule as METRIC-OPS-01."""
        done_at = t.done_at or now_utc()
        on_time = t.due_date is not None and done_at.astimezone(UTC).date() <= t.due_date
        await self._emit("execution.task_completed", t,
                         {"done_at": done_at.isoformat(), "on_time": on_time})  # fmt: skip

    async def _require_unblocked(self, t: Task) -> None:
        """R-DEC-43: `done` only when every `depends_on` task is `done`/`cancelled` → else 422."""
        n = (await self.deps.open_blockers([t.id])).get(t.id, 0)
        if n:
            raise BusinessRuleError(
                "task still blocked by open dependencies",
                details={"rule": "FR-TASK-02", "open_dependencies": n},
            )

    async def delete(self, user: Principal, id_: uuid.UUID) -> None:
        t = await self.get(user, id_, "write")
        if await self.tasks.count_by(Task.parent_task_id, [t.id]):
            raise BusinessRuleError(
                "task still has sub-tasks", details={"field": "parent_task_id", "rule": "R-DEC-42"}
            )
        before = await self.out(t)
        for dep in await self.deps.touching(t.id):  # soft-delete the task's edges (EP-TASK-05)
            dep.updated_by = user.user_id
            await self.deps.soft_delete(dep)
        t.updated_by = user.user_id
        await self.tasks.soft_delete(t)
        await self._progress(t.initiative_id)
        await self.audit("task_delete", "tasks", t.id, before=before)

    # ---------- EP-TASK-06..08 dependencies (FR-TASK-02, R-DEC-43) ----------
    async def _brief(self, user: Principal, dep: TaskDependency, other: uuid.UUID) -> TaskBriefOut:
        t = await self.tasks.get(other)
        if t is None or not scope.allowed(user, "read", dept=t.department_id,
                                          owners=(t.owner_id, t.assignee_id)):  # fmt: skip
            return TaskBriefOut(dependency_id=dep.id, task_id=other, restricted=True)
        return TaskBriefOut(
            dependency_id=dep.id, task_id=t.id, title=t.title, status=t.status,
            due_date=t.due_date, overdue=is_overdue(t.status, t.due_date, today()),
            assignee_id=t.assignee_id,
        )  # fmt: skip

    async def list_dependencies(self, user: Principal, id_: uuid.UUID) -> TaskDependenciesOut:
        t = await self.get(user, id_)
        depends_on: list[TaskBriefOut] = []
        blocks: list[TaskBriefOut] = []
        for dep in await self.deps.touching(t.id):
            if dep.task_id == t.id:
                depends_on.append(await self._brief(user, dep, dep.depends_on_task_id))
            else:
                blocks.append(await self._brief(user, dep, dep.task_id))
        return TaskDependenciesOut(depends_on=depends_on, blocks=blocks)

    async def add_dependency(
        self, user: Principal, id_: uuid.UUID, body: TaskDependencyCreate
    ) -> TaskDependencyOut:
        t = await self.get(user, id_, "write")
        target = body.depends_on_task_id
        if target == t.id:
            cycle = [str(t.id), str(t.id)]
            raise BusinessRuleError(
                "task cannot depend on itself", details={"rule": "FR-TASK-02", "cycle": cycle}
            )
        await self.get(user, target)  # 404 if missing / other tenant / not readable
        await self.tasks.lock(t.id, target)
        if await self.deps.find(t.id, target) is not None:
            raise DuplicateResourceError("dependency already exists",
                                         details={"depends_on_task_id": str(target)})  # fmt: skip
        path = await self._cycle(target, t.id)
        if path is not None:
            raise BusinessRuleError("dependency would create a cycle",
                                    details={"rule": "FR-TASK-02",
                                             "cycle": [str(c) for c in path]})  # fmt: skip
        dep = await self.deps.create(
            task_id=t.id, depends_on_task_id=target, dependency_type=body.dependency_type,
            source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        await self.db.refresh(dep)
        out = TaskDependencyOut.model_validate(dep)
        await self.audit("task_dependency_create", "task_dependencies", dep.id, after=out)
        return out

    async def _cycle(self, start: uuid.UUID, target: uuid.UUID) -> list[uuid.UUID] | None:
        """BFS from `start` along `depends_on` (level by level, depth ≤ 50) looking for `target`."""
        edges: dict[uuid.UUID, list[uuid.UUID]] = {}
        frontier, seen = [start], {start}
        for _ in range(MAX_DEPENDENCY_DEPTH):
            if not frontier:
                break
            nxt: list[uuid.UUID] = []
            for e in await self.deps.edges_from(frontier):
                edges.setdefault(e.task_id, []).append(e.depends_on_task_id)
                if e.depends_on_task_id not in seen:
                    seen.add(e.depends_on_task_id)
                    nxt.append(e.depends_on_task_id)
            frontier = nxt
        else:
            if frontier:
                raise BusinessRuleError("dependency chain too deep",
                                        details={"rule": "FR-TASK-02",
                                                 "max_depth": MAX_DEPENDENCY_DEPTH})  # fmt: skip
        try:
            return find_cycle(start, target, edges)
        except ValueError as exc:  # pragma: no cover — edges were collected within the limit
            raise BusinessRuleError(
                "dependency chain too deep", details={"rule": "FR-TASK-02"}
            ) from exc

    async def remove_dependency(
        self, user: Principal, id_: uuid.UUID, dependency_id: uuid.UUID
    ) -> None:
        t = await self.get(user, id_, "write")
        dep = await self.deps.get(dependency_id)
        if dep is None or dep.task_id != t.id:
            raise not_found("dependency")
        before = TaskDependencyOut.model_validate(dep)
        dep.updated_by = user.user_id
        await self.deps.soft_delete(dep)
        await self.audit("task_dependency_delete", "task_dependencies", dep.id, before=before)

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
                "days_late": (as_of - t.due_date).days if t.due_date else None,  # M1.3
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

    # ---------- EP-TASK-19 reassign request (R-DEC-45) ----------
    async def request_reassign(
        self, user: Principal, id_: uuid.UUID, body: ReassignRequestCreate
    ) -> ApprovalRequestOut:
        """EMP asks to move their task to someone else; the department MGR approves (EP-WF-03).

        MGR/DIR/CEO who may write the task change the assignee directly → 422."""
        if scope.level(user, "write") != "o":
            await self.get(user, id_, "write")  # out of scope → 403
            raise BusinessRuleError("direct reassign allowed for this role",
                                    details={"reason": "direct_reassign_allowed"})  # fmt: skip
        t = await self.get(user, id_)
        if t.status in CLOSED:
            raise ConflictStateError(f"task is {t.status}", details={"status": t.status})
        payload = {
            "task_id": str(t.id), "from_assignee_id": _s(t.assignee_id),
            "to_assignee_id": str(body.to_assignee_id), "reason": body.reason,
            "task_version": t.version,
        }  # fmt: skip
        return await ApprovalService(self.db).create_for_task_reassign(
            task_id=t.id, department_id=t.department_id, requested_by=user.user_id,
            payload=payload,
        )  # fmt: skip


async def _apply_approved_reassign(
    db: Any, approver: Any, task_id: uuid.UUID, payload: dict[str, Any]
) -> None:
    """Approval hook `task_reassign` (R-DEC-45): same tx as the final approve. The task must
    still be at the version seen when the request was made — else 409 and the whole decide
    rolls back (request stays PENDING)."""
    version = int(payload["task_version"])
    body = TaskUpdate(assignee_id=uuid.UUID(str(payload["to_assignee_id"])), version=version)
    await TaskService(db).update(approver, task_id, body, version)


register_approval_hook("task_reassign", _apply_approved_reassign)


async def detect_overdue_tasks(db: AsyncSession, as_of: date) -> list[uuid.UUID]:
    """Public job entry (EVT-execution.task_overdue): caller commits; safe to rerun."""
    return await TaskService(db).detect_overdue(as_of)

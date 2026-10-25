"""Execution repositories — only `execution` services use them (DEC-125)."""

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import ColumnElement, func, select

from app.core.base_model import Base
from app.core.base_repository import BaseRepository, tenant_ids_where
from app.modules.execution.models import (
    CheckIn,
    Decision,
    Initiative,
    KeyResult,
    Kpi,
    KpiMeasurement,
    KpiTarget,
    Meeting,
    Milestone,
    Objective,
    Project,
    Task,
    TaskDependency,
)

OPEN_TASK_STATUSES = ("backlog", "todo", "in_progress", "blocked", "in_review")


class Repo[M: Base](BaseRepository[M]):
    """Generic repository + helpers shared by every execution table."""

    async def where(self, *clauses: ColumnElement[bool], order: Any = None) -> Sequence[M]:
        stmt = self._live()
        for c in clauses:
            stmt = stmt.where(c)
        if order is not None:
            stmt = stmt.order_by(order)
        return (await self.db.execute(stmt)).scalars().all()


class TaskRepository(Repo[Task]):
    model = Task

    async def overdue_unnotified(self, as_of: date) -> Sequence[Task]:
        """Open tasks past `due_date` not yet announced — locked so two jobs cannot both send."""
        stmt = (
            self._live()
            .where(
                Task.due_date < as_of,
                Task.status.in_(OPEN_TASK_STATUSES),
                Task.overdue_notified_at.is_(None),
            )
            .order_by(Task.due_date, Task.id)
            .with_for_update(skip_locked=True)
        )
        return (await self.db.execute(stmt)).scalars().all()

    async def due_between(self, start: date, end: date) -> Sequence[Task]:
        """Tasks with `due_date` in `[start, end)`."""
        return await self.where(Task.due_date >= start, Task.due_date < end, order=Task.id)

    async def for_parents(self, column: Any, ids: Sequence[uuid.UUID]) -> Sequence[Task]:
        if not ids:
            return []
        return await self.where(column.in_(ids), order=Task.id)

    async def assigned_active(
        self, since: date, until: date, department_id: uuid.UUID | None = None
    ) -> Sequence[Task]:
        """Assigned, non-cancelled tasks created before `until` and not done before `since`."""
        since_ts = datetime.combine(since, time.min, tzinfo=UTC)
        until_ts = datetime.combine(until, time.min, tzinfo=UTC)
        clauses: list[ColumnElement[bool]] = [
            Task.assignee_id.is_not(None),
            Task.status != "cancelled",
            Task.created_at < until_ts,
            Task.done_at.is_(None) | (Task.done_at >= since_ts),
        ]
        if department_id is not None:
            clauses.append(Task.department_id == department_id)
        return await self.where(*clauses, order=Task.id)

    async def by_ids(self, ids: Sequence[uuid.UUID]) -> Sequence[Task]:
        """Live tasks with these ids in one query (EP-TASK-06 briefs, FR-TASK-02 blockers)."""
        if not ids:
            return []
        return (
            (await self.db.execute(self._live().where(Task.id.in_(list(set(ids)))))).scalars().all()
        )

    async def lock(self, *ids: uuid.UUID) -> Sequence[Task]:
        """`SELECT … FOR UPDATE` live tasks in ascending id order (deadlock-free, 05 §2.5)."""
        stmt = self._live().where(Task.id.in_(ids)).order_by(Task.id).with_for_update()
        return (await self.db.execute(stmt)).scalars().all()

    async def count_by(
        self, column: Any, ids: Sequence[uuid.UUID], *extra: ColumnElement[bool]
    ) -> dict[uuid.UUID, int]:
        """Live task count grouped by `column` (e.g. sub-tasks per parent), `extra` filters."""
        if not ids:
            return {}
        stmt = self._scoped(select(column, func.count()).where(
            column.in_(ids), Task.deleted_at.is_(None), *extra
        ).group_by(column))  # fmt: skip
        return {k: int(n) for k, n in (await self.db.execute(stmt)).all()}

    async def status_counts(
        self, column: Any, ids: Sequence[uuid.UUID]
    ) -> list[tuple[Any, str, int]]:
        """`(parent, status, count)` of live tasks grouped by `column` + status."""
        if not ids:
            return []
        stmt = self._scoped(select(column, Task.status, func.count()).where(
            column.in_(ids), Task.deleted_at.is_(None)
        ).group_by(column, Task.status))  # fmt: skip
        return [(k, st, int(n)) for k, st, n in (await self.db.execute(stmt)).all()]

    @staticmethod
    def project_ids_assigned_to(ids: Sequence[uuid.UUID]) -> Any:
        """Subquery: projects having a live task assigned to one of `ids` (EMP project scope)."""
        stmt = tenant_ids_where(Task, Task.assignee_id.in_(ids), Task.deleted_at.is_(None))
        return stmt.with_only_columns(Task.project_id)


class TaskDependencyRepository(Repo[TaskDependency]):
    model = TaskDependency

    async def edges_from(self, ids: Sequence[uuid.UUID]) -> Sequence[TaskDependency]:
        """Live `depends_on` edges leaving `ids` (one BFS level)."""
        if not ids:
            return []
        return await self.where(TaskDependency.task_id.in_(ids))

    async def find(self, task_id: uuid.UUID, depends_on: uuid.UUID) -> TaskDependency | None:
        rows = await self.where(
            TaskDependency.task_id == task_id, TaskDependency.depends_on_task_id == depends_on
        )
        return rows[0] if rows else None

    async def touching(self, task_id: uuid.UUID) -> Sequence[TaskDependency]:
        return await self.where(
            (TaskDependency.task_id == task_id) | (TaskDependency.depends_on_task_id == task_id),
            order=TaskDependency.created_at,
        )

    async def open_blocker_ids(self, task_id: uuid.UUID) -> list[uuid.UUID]:
        """Live `depends_on` task ids of `task_id` not yet `done`/`cancelled` (R-DEC-43)."""
        stmt = self._scoped(
            select(TaskDependency.depends_on_task_id)
            .join(Task, Task.id == TaskDependency.depends_on_task_id)
            .where(
                TaskDependency.task_id == task_id, TaskDependency.deleted_at.is_(None),
                Task.deleted_at.is_(None), Task.status.in_(OPEN_TASK_STATUSES),
            )
            .order_by(TaskDependency.depends_on_task_id)
        )  # fmt: skip
        return list((await self.db.execute(stmt)).scalars())

    async def open_blockers(self, ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
        """Per blocked task: number of live `depends_on` tasks not `done`/`cancelled`."""
        if not ids:
            return {}
        stmt = self._scoped(
            select(TaskDependency.task_id, func.count())
            .join(Task, Task.id == TaskDependency.depends_on_task_id)
            .where(
                TaskDependency.task_id.in_(ids), TaskDependency.deleted_at.is_(None),
                Task.deleted_at.is_(None), Task.status.in_(OPEN_TASK_STATUSES),
            )
            .group_by(TaskDependency.task_id)
        )  # fmt: skip
        return {k: int(n) for k, n in (await self.db.execute(stmt)).all()}


class MeetingRepository(Repo[Meeting]):
    model = Meeting


class DecisionRepository(Repo[Decision]):
    model = Decision


class ProjectRepository(Repo[Project]):
    model = Project

    async def ids_matching(
        self, filters: dict[str, Any], where: Sequence[ColumnElement[bool]]
    ) -> Sequence[Project]:
        """Every live project matching (for computed filters such as `late`)."""
        clauses = [getattr(Project, k) == v for k, v in filters.items()]
        return await self.where(*clauses, *where, order=Project.id)

    async def running(self, as_of: date) -> Sequence[Project]:
        """`active` projects with a schedule that has started by `as_of` (METRIC-OPS-02)."""
        return await self.where(
            Project.status == "active",
            Project.start_date.is_not(None),
            Project.planned_end_date.is_not(None),
            Project.start_date <= as_of,
            order=Project.id,
        )


class ObjectiveRepository(Repo[Objective]):
    model = Objective


class KeyResultRepository(Repo[KeyResult]):
    model = KeyResult


class KpiRepository(Repo[Kpi]):
    model = Kpi


class KpiTargetRepository(Repo[KpiTarget]):
    model = KpiTarget

    async def find(self, kpi_id: uuid.UUID, period_key: str) -> KpiTarget | None:
        rows = await self.where(KpiTarget.kpi_id == kpi_id, KpiTarget.period_key == period_key)
        return rows[0] if rows else None


class MeasurementRepository(Repo[KpiMeasurement]):
    model = KpiMeasurement

    async def find(self, kpi_id: uuid.UUID, period_key: str) -> KpiMeasurement | None:
        """Row lock so two concurrent measurements of one period serialise."""
        stmt = (
            self._live()
            .where(KpiMeasurement.kpi_id == kpi_id, KpiMeasurement.period_key == period_key)
            .with_for_update()
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()


class CheckInRepository(Repo[CheckIn]):
    model = CheckIn


class InitiativeRepository(Repo[Initiative]):
    model = Initiative

    async def in_flight(self, start: date, end: date) -> Sequence[Initiative]:
        """`active`/`at_risk` initiatives overlapping `[start, end)` (METRIC-RSK-06)."""
        return await self.where(
            Initiative.status.in_(("active", "at_risk")),
            Initiative.start_date < end,
            Initiative.planned_end_date >= start,
            order=Initiative.id,
        )


class MilestoneRepository(Repo[Milestone]):
    model = Milestone

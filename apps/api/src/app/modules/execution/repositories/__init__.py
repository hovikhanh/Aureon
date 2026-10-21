"""Execution repositories — only `execution` services use them (DEC-125)."""

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import ColumnElement

from app.core.base_model import Base
from app.core.base_repository import BaseRepository
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


class MeetingRepository(Repo[Meeting]):
    model = Meeting


class DecisionRepository(Repo[Decision]):
    model = Decision


class ProjectRepository(Repo[Project]):
    model = Project

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

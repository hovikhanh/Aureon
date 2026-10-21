"""Execution repositories — only `execution` services use them (DEC-125)."""

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import ColumnElement

from app.core.base_model import Base
from app.core.base_repository import BaseRepository
from app.modules.execution.models import (
    CheckIn,
    Decision,
    KeyResult,
    Kpi,
    KpiMeasurement,
    KpiTarget,
    Meeting,
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

    async def open_assigned(self, department_id: uuid.UUID | None = None) -> Sequence[Task]:
        clauses: list[ColumnElement[bool]] = [
            Task.status.in_(OPEN_TASK_STATUSES),
            Task.assignee_id.is_not(None),
        ]
        if department_id is not None:
            clauses.append(Task.department_id == department_id)
        return await self.where(*clauses, order=Task.id)

    async def for_parents(self, column: Any, ids: Sequence[uuid.UUID]) -> Sequence[Task]:
        if not ids:
            return []
        return await self.where(column.in_(ids), order=Task.id)


class MeetingRepository(Repo[Meeting]):
    model = Meeting


class DecisionRepository(Repo[Decision]):
    model = Decision


class ProjectRepository(Repo[Project]):
    model = Project


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

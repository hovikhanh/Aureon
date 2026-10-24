"""Execution repositories — only `execution` services use them (DEC-125)."""

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import ColumnElement, Select, func, select

from app.core.base_model import Base
from app.core.base_repository import BaseRepository, tenant_ids_where
from app.modules.execution.models import (
    CheckIn,
    Decision,
    Initiative,
    KeyResult,
    Kpi,
    KpiEvaluation,
    KpiMeasurement,
    KpiTarget,
    KrMeasurement,
    Meeting,
    Milestone,
    Objective,
    Project,
    StrategicObjective,
    Strategy,
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
            stmt = stmt.order_by(*order) if isinstance(order, tuple) else stmt.order_by(order)
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


class StrategyRepository(Repo[Strategy]):
    model = Strategy

    async def active_overlapping(
        self, start: date, end: date, exclude: uuid.UUID | None
    ) -> Sequence[Strategy]:
        """Live `active` strategies overlapping `[start, end]`, locked `FOR UPDATE` (05 §2.6)."""
        stmt = self._live().where(
            Strategy.status == "active", Strategy.period_start < end, Strategy.period_end > start
        )
        if exclude is not None:
            stmt = stmt.where(Strategy.id != exclude)
        return (await self.db.execute(stmt.with_for_update())).scalars().all()


class StrategicObjectiveRepository(Repo[StrategicObjective]):
    model = StrategicObjective


class ObjectiveRepository(Repo[Objective]):
    model = Objective


class KeyResultRepository(Repo[KeyResult]):
    model = KeyResult

    async def at_risk_counts(self, objective_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
        """Live `at_risk` KRs per objective (ObjectiveOut `at_risk_kr_count`)."""
        if not objective_ids:
            return {}
        stmt = self._scoped(select(KeyResult.objective_id, func.count()).where(
            KeyResult.objective_id.in_(objective_ids), KeyResult.deleted_at.is_(None),
            KeyResult.at_risk.is_(True),
        ).group_by(KeyResult.objective_id))  # fmt: skip
        return {k: int(n) for k, n in (await self.db.execute(stmt)).all()}

    @staticmethod
    def objectives_with_at_risk() -> Select[tuple[uuid.UUID]]:
        """Subquery: objective ids having a live at-risk KR (EP-OKR-01 `at_risk`)."""
        stmt = tenant_ids_where(KeyResult, KeyResult.at_risk.is_(True),
                                KeyResult.deleted_at.is_(None))  # fmt: skip
        return stmt.with_only_columns(KeyResult.objective_id)


class KpiRepository(Repo[Kpi]):
    model = Kpi

    async def lock(self, kpi_id: uuid.UUID) -> Kpi | None:
        """`SELECT … FOR UPDATE` the KPI — mutex for its targets / measurements / evaluation."""
        stmt = self._live().where(Kpi.id == kpi_id).with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()


class KpiTargetRepository(Repo[KpiTarget]):
    model = KpiTarget

    async def versions(self, kpi_id: uuid.UUID, period_key: str) -> Sequence[KpiTarget]:
        """Every live version of `(kpi, period)`, oldest `valid_from` first (R-DEC-52)."""
        return await self.where(KpiTarget.kpi_id == kpi_id, KpiTarget.period_key == period_key,
                                order=KpiTarget.valid_from)  # fmt: skip

    async def history(
        self, kpi_id: uuid.UUID, period_key: str | None, as_of: date | None
    ) -> Sequence[KpiTarget]:
        clauses: list[ColumnElement[bool]] = [KpiTarget.kpi_id == kpi_id]
        if period_key is not None:
            clauses.append(KpiTarget.period_key == period_key)
        if as_of is not None:
            clauses += [KpiTarget.valid_from <= as_of,
                        KpiTarget.valid_to.is_(None) | (KpiTarget.valid_to > as_of)]  # fmt: skip
        stmt = self._live().where(*clauses).order_by(KpiTarget.period_key, KpiTarget.valid_from)
        return (await self.db.execute(stmt)).scalars().all()


class KpiEvaluationRepository(Repo[KpiEvaluation]):
    model = KpiEvaluation

    async def find(self, kpi_id: uuid.UUID, period_key: str) -> KpiEvaluation | None:
        rows = await self.where(KpiEvaluation.kpi_id == kpi_id,
                                KpiEvaluation.period_key == period_key)  # fmt: skip
        return rows[0] if rows else None

    async def between(
        self, kpi_id: uuid.UUID, start: str | None, end: str | None, limit: int
    ) -> Sequence[KpiEvaluation]:
        """Evaluations in `[start, end]` asc; the latest `limit` periods."""
        stmt = self._live().where(KpiEvaluation.kpi_id == kpi_id)
        if start is not None:
            stmt = stmt.where(KpiEvaluation.period_key >= start)
        if end is not None:
            stmt = stmt.where(KpiEvaluation.period_key <= end)
        stmt = stmt.order_by(KpiEvaluation.period_key.desc()).limit(limit)
        rows = (await self.db.execute(stmt)).scalars().all()
        return list(reversed(rows))

    async def latest_for(self, kpi_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, KpiEvaluation]:
        """Latest-period evaluation per KPI (KpiOut `latest_evaluation`)."""
        if not kpi_ids:
            return {}
        stmt = (
            self._live().where(KpiEvaluation.kpi_id.in_(kpi_ids))
            .order_by(KpiEvaluation.kpi_id, KpiEvaluation.period_key.desc())
            .distinct(KpiEvaluation.kpi_id)
        )  # fmt: skip
        return {e.kpi_id: e for e in (await self.db.execute(stmt)).scalars().all()}

    async def of_periods(
        self, pairs: Sequence[tuple[uuid.UUID, str]]
    ) -> set[tuple[uuid.UUID, str]]:
        """Which `(kpi_id, period_key)` pairs already have an evaluation."""
        return set(await self.for_pairs(pairs))

    async def for_pairs(
        self, pairs: Sequence[tuple[uuid.UUID, str]]
    ) -> dict[tuple[uuid.UUID, str], KpiEvaluation]:
        """Live evaluations of the given `(kpi_id, period_key)` pairs (G2 METRIC-STR-01)."""
        if not pairs:
            return {}
        rows = await self.where(KpiEvaluation.kpi_id.in_({k for k, _ in pairs}),
                                KpiEvaluation.period_key.in_({p for _, p in pairs}))  # fmt: skip
        want = set(pairs)
        return {(e.kpi_id, e.period_key): e for e in rows if (e.kpi_id, e.period_key) in want}

    @staticmethod
    def kpis_with_latest_band(band: str) -> Select[tuple[uuid.UUID]]:
        """Subquery: KPI ids whose latest-period evaluation has `band` (EP-KPI-01 `band`)."""
        latest = (
            tenant_ids_where(KpiEvaluation, KpiEvaluation.deleted_at.is_(None))
            .with_only_columns(KpiEvaluation.kpi_id, KpiEvaluation.band)
            .order_by(KpiEvaluation.kpi_id, KpiEvaluation.period_key.desc())
            .distinct(KpiEvaluation.kpi_id)
            .subquery()
        )  # fmt: skip
        return select(latest.c.kpi_id).where(latest.c.band == band)

    async def remove(self, ev: KpiEvaluation) -> None:
        """Derived row of a period left without measurement (undo, R-DEC-53) — FK to the
        measurement is RESTRICT, so it cannot survive soft-deleted."""
        await self.db.delete(ev)
        await self.db.flush()


class MeasurementRepository(Repo[KpiMeasurement]):
    model = KpiMeasurement

    async def of_period(self, kpi_id: uuid.UUID, period_key: str) -> Sequence[KpiMeasurement]:
        """Every measurement of `(kpi, period)`, latest first."""
        return await self.where(
            KpiMeasurement.kpi_id == kpi_id, KpiMeasurement.period_key == period_key,
            order=(KpiMeasurement.measured_at.desc(), KpiMeasurement.id.desc()),
        )  # fmt: skip

    async def for_check_in(self, check_in_id: uuid.UUID) -> Sequence[KpiMeasurement]:
        return await self.where(KpiMeasurement.check_in_id == check_in_id)

    async def remove(self, m: KpiMeasurement) -> None:
        """Delete an append-only row created by an action being undone (no `deleted_at`)."""
        await self.db.delete(m)
        await self.db.flush()


class CheckInRepository(Repo[CheckIn]):
    model = CheckIn

    async def remove(self, c: CheckIn) -> None:
        await self.db.delete(c)
        await self.db.flush()


class KrMeasurementRepository(Repo[KrMeasurement]):
    model = KrMeasurement

    async def latest(
        self, key_result_id: uuid.UUID, exclude: uuid.UUID | None = None
    ) -> KrMeasurement | None:
        stmt = self._live().where(KrMeasurement.key_result_id == key_result_id)
        if exclude is not None:
            stmt = stmt.where(KrMeasurement.id != exclude)
        stmt = stmt.order_by(KrMeasurement.measured_at.desc(), KrMeasurement.id.desc()).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def by_check_ins(self, ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, KrMeasurement]:
        if not ids:
            return {}
        rows = await self.where(KrMeasurement.check_in_id.in_(ids))
        return {r.check_in_id: r for r in rows if r.check_in_id is not None}

    async def remove(self, m: KrMeasurement) -> None:
        await self.db.delete(m)
        await self.db.flush()


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

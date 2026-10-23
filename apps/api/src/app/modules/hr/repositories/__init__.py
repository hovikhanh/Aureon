"""HR repositories — only `hr` services use them (DEC-125)."""

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import ColumnElement, and_, func, or_, select

from app.core.base_repository import BaseRepository
from app.core.crypto_columns import decrypted_bigint
from app.modules.hr.models import (
    Department,
    Employee,
    EmployeeAssignment,
    HiringPlan,
    Organization,
    Position,
    SalaryHistory,
)

OPEN_PLAN_STATUSES = ("approved", "in_progress")


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    async def live(self) -> Sequence[Organization]:
        stmt = self._live().order_by(Organization.valid_from, Organization.code)
        return (await self.db.execute(stmt)).scalars().all()


class DepartmentRepository(BaseRepository[Department]):
    model = Department

    async def by_code(self, code: str) -> Department | None:
        """Live department of the current tenant with `code` (05 §2.4 unique live per tenant)."""
        stmt = self._live().where(Department.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()


class PositionRepository(BaseRepository[Position]):
    model = Position

    async def by_title(self, department_id: uuid.UUID, title: str) -> Position | None:
        stmt = (
            self._live()
            .where(Position.department_id == department_id)
            .where(func.lower(Position.title) == title.lower())
            .order_by(Position.created_at)
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def titles(self, ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not ids:
            return {}
        stmt = select(Position.id, Position.title).where(Position.id.in_(set(ids)))
        return {i: t for i, t in (await self.db.execute(stmt)).all()}


def employed_on(day: date) -> ColumnElement[bool]:
    """Employee on the payroll at the end of `day` (hired, not yet left)."""
    return and_(
        Employee.hire_date <= day,
        or_(Employee.termination_date.is_(None), Employee.termination_date > day),
    )


def effective_at(model: type[EmployeeAssignment], as_of: date) -> ColumnElement[bool]:
    """Half-open `[valid_from, valid_to)` contains `as_of` (05 §2.4)."""
    return and_(model.valid_from <= as_of, or_(model.valid_to.is_(None), model.valid_to > as_of))


class AssignmentRepository(BaseRepository[EmployeeAssignment]):
    model = EmployeeAssignment

    async def current(self, employee_id: uuid.UUID) -> EmployeeAssignment | None:
        stmt = self._live().where(
            EmployeeAssignment.employee_id == employee_id, EmployeeAssignment.valid_to.is_(None)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def overlapping(
        self, employee_id: uuid.UUID, start: date, end: date | None, *, exclude: uuid.UUID | None
    ) -> bool:
        """Any live row of the employee intersecting `[start, end)` (other than `exclude`)."""
        stmt = self._live().where(
            EmployeeAssignment.employee_id == employee_id,
            or_(EmployeeAssignment.valid_to.is_(None), EmployeeAssignment.valid_to > start),
        )
        if end is not None:
            stmt = stmt.where(EmployeeAssignment.valid_from < end)
        if exclude is not None:
            stmt = stmt.where(EmployeeAssignment.id != exclude)
        return (await self.db.execute(stmt.limit(1))).first() is not None

    async def history(
        self,
        *,
        employee_id: uuid.UUID | None = None,
        department_id: uuid.UUID | None = None,
        as_of: date | None = None,
        limit: int = 20,
        offset: int = 0,
        order: str = "asc",
        within: set[uuid.UUID] | None = None,
    ) -> tuple[Sequence[EmployeeAssignment], int]:
        where: list[ColumnElement[bool]] = []
        if within is not None:
            where.append(EmployeeAssignment.department_id.in_(within))
        if employee_id is not None:
            where.append(EmployeeAssignment.employee_id == employee_id)
        if department_id is not None:
            where.append(EmployeeAssignment.department_id == department_id)
        if as_of is not None:
            where.append(effective_at(EmployeeAssignment, as_of))
        return await self.list_page(
            limit=limit, offset=offset, sort_by="valid_from", order=order, where=where
        )


class EmployeeRepository(BaseRepository[Employee]):
    model = Employee

    async def lock(self, employee_id: uuid.UUID) -> Employee | None:
        """`SELECT … FOR UPDATE` on the live employee — serialises assignment writes (T-612)."""
        stmt = self._live().where(Employee.id == employee_id).with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def by_email(self, email: str) -> Employee | None:
        stmt = self._live().where(Employee.email == email)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def code_taken(self, code: str, exclude: uuid.UUID | None = None) -> bool:
        stmt = self._live().where(Employee.employee_code == code)
        if exclude is not None:
            stmt = stmt.where(Employee.id != exclude)
        return (await self.db.execute(stmt.limit(1))).first() is not None

    async def manager_of(self, id_: uuid.UUID) -> uuid.UUID | None:
        stmt = select(Employee.manager_id).where(Employee.id == id_)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def roster(
        self, where: Sequence[ColumnElement[bool]] = ()
    ) -> list[tuple[date, date | None, str]]:
        """(hire_date, termination_date, status) of live employees — no PII columns."""
        stmt = select(Employee.hire_date, Employee.termination_date, Employee.status).where(
            Employee.deleted_at.is_(None), *where
        )
        return [(h, t, s) for h, t, s in (await self.db.execute(stmt)).all()]


class SalaryRepository(BaseRepository[SalaryHistory]):
    model = SalaryHistory

    async def exists(self, employee_id: uuid.UUID, effective: date) -> bool:
        stmt = select(SalaryHistory.id).where(
            SalaryHistory.employee_id == employee_id, SalaryHistory.effective_date == effective
        )
        return (await self.db.execute(stmt)).first() is not None

    async def payroll_on(self, day: date, where: Sequence[ColumnElement[bool]] = ()) -> int:
        """Sum of each on-payroll employee's latest `base_salary` effective on `day`."""
        latest = (
            select(SalaryHistory.employee_id, func.max(SalaryHistory.effective_date).label("d"))
            .where(SalaryHistory.effective_date <= day)
            .group_by(SalaryHistory.employee_id)
            .subquery()
        )
        stmt = (
            select(func.coalesce(func.sum(decrypted_bigint(SalaryHistory.base_salary)), 0))
            .join(
                latest,
                and_(
                    latest.c.employee_id == SalaryHistory.employee_id,
                    latest.c.d == SalaryHistory.effective_date,
                ),
            )
            .join(Employee, Employee.id == SalaryHistory.employee_id)
            .where(Employee.deleted_at.is_(None), employed_on(day), *where)
        )
        return int((await self.db.execute(stmt)).scalar_one())


class HiringPlanRepository(BaseRepository[HiringPlan]):
    model = HiringPlan

    async def delayed_candidates(self, cutoff: date) -> Sequence[HiringPlan]:
        """Open plans whose `target_fill_date` < `cutoff`, unfilled, not yet notified."""
        stmt = (
            self._live()
            .where(HiringPlan.status.in_(OPEN_PLAN_STATUSES))
            .where(HiringPlan.filled < HiringPlan.headcount)
            .where(HiringPlan.target_fill_date < cutoff)
            .where(HiringPlan.delayed_notified_at.is_(None))
            .order_by(HiringPlan.target_fill_date, HiringPlan.id)
            .with_for_update(skip_locked=True)
        )
        return (await self.db.execute(stmt)).scalars().all()

    async def late_days(self, today: date, where: Sequence[ColumnElement[bool]] = ()) -> list[int]:
        """Days late of open, unfilled plans past `target_fill_date` (METRIC-HR-04)."""
        stmt = select(HiringPlan.target_fill_date).where(
            HiringPlan.deleted_at.is_(None), HiringPlan.status.in_(OPEN_PLAN_STATUSES),
            HiringPlan.filled < HiringPlan.headcount, HiringPlan.target_fill_date < today, *where,
        )  # fmt: skip
        return [(today - d).days for (d,) in (await self.db.execute(stmt)).all()]

    async def open_positions(self, where: Sequence[ColumnElement[bool]] = ()) -> int:
        stmt = select(func.coalesce(func.sum(HiringPlan.headcount - HiringPlan.filled), 0)).where(
            HiringPlan.deleted_at.is_(None), HiringPlan.status.in_(OPEN_PLAN_STATUSES), *where
        )
        return int((await self.db.execute(stmt)).scalar_one())

"""D01 Organization repositories (M1.2 T-613) — effective-dated reads + child counts.

Every query starts from `_live()` / `_scoped()` (tenant + `deleted_at IS NULL`, R-DEC-21).
"""

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import ColumnElement, and_, func, or_, select

from app.core.base_repository import BaseRepository
from app.modules.hr.models import (
    Department,
    Employee,
    EmployeeAssignment,
    Organization,
    Position,
    Team,
)
from app.modules.hr.repositories import effective_at


def valid_on(model: Any, as_of: date) -> ColumnElement[bool]:
    """`[valid_from, valid_to)` of an effective-dated row contains `as_of`."""
    return and_(model.valid_from <= as_of, or_(model.valid_to.is_(None), model.valid_to > as_of))


class _Dated[ModelT: Organization | Department | Team](BaseRepository[ModelT]):
    async def by_code_live(self, code: str, *, exclude: uuid.UUID | None = None) -> bool:
        stmt = self._live().where(self._col("code") == code)
        if exclude is not None:
            stmt = stmt.where(self._col("id") != exclude)
        return (await self.db.execute(stmt.limit(1))).first() is not None

    async def at(self, as_of: date, **filters: Any) -> Sequence[ModelT]:
        """Rows valid on `as_of` — archived rows included (history), tenant-scoped."""
        stmt = self._scoped(select(self.model)).where(valid_on(self.model, as_of))
        for name, value in filters.items():
            stmt = stmt.where(self._col(name) == value)
        stmt = stmt.order_by(self._col("code"))
        return (await self.db.execute(stmt)).scalars().all()


class OrgRepository(_Dated[Organization]):
    model = Organization

    def search(self, q: str | None) -> list[ColumnElement[bool]]:
        where: list[ColumnElement[bool]] = []
        if q:
            like = f"%{q.lower()}%"
            where.append(or_(func.lower(Organization.name).like(like),
                             func.lower(Organization.code).like(like)))  # fmt: skip
        return where

    async def page(
        self, *, q: str | None, include_archived: bool, limit: int, offset: int, sort_by: str,
        order: str,
    ) -> tuple[Sequence[Organization], int]:  # fmt: skip
        where = self.search(q)
        if not include_archived:
            return await self.list_page(limit=limit, offset=offset, sort_by=sort_by,
                                        order=order, where=where)  # fmt: skip
        stmt = self._scoped(select(Organization))
        for clause in where:
            stmt = stmt.where(clause)
        total = int(await self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        col = getattr(Organization, sort_by)
        stmt = stmt.order_by(col.asc() if order == "asc" else col.desc(), Organization.id)
        rows = (await self.db.execute(stmt.limit(limit).offset(offset))).scalars().all()
        return rows, total

    async def live(self) -> Sequence[Organization]:
        stmt = self._live().order_by(Organization.valid_from, Organization.code)
        return (await self.db.execute(stmt)).scalars().all()

    async def get_any(self, id_: uuid.UUID) -> Organization | None:
        """Live or archived (tree `as_of` in the past)."""
        stmt = self._scoped(select(Organization)).where(Organization.id == id_)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def first_at(self, as_of: date) -> Organization | None:
        rows = await self.at(as_of)
        return min(rows, key=lambda o: (o.valid_from, o.code)) if rows else None

    async def live_departments(self, org_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(
            self._scoped(select(Department.id))
            .where(Department.organization_id == org_id, Department.deleted_at.is_(None))
            .subquery()
        )
        return int(await self.db.scalar(stmt) or 0)


class DeptRepository(_Dated[Department]):
    model = Department

    async def live_children(self, id_: uuid.UUID) -> dict[str, int]:
        """Live sub-departments / teams and current assignments of a department."""
        sub = self._scoped(select(func.count(Department.id))).where(
            Department.parent_id == id_, Department.deleted_at.is_(None)
        )
        teams = BaseRepository(self.db, Team)._live().where(Team.department_id == id_)
        asg = (
            BaseRepository(self.db, EmployeeAssignment)
            ._live()
            .where(EmployeeAssignment.department_id == id_, EmployeeAssignment.valid_to.is_(None))
        )
        n_teams = select(func.count()).select_from(teams.subquery())
        n_asg = select(func.count()).select_from(asg.subquery())
        return {
            "departments": int(await self.db.scalar(sub) or 0),
            "teams": int(await self.db.scalar(n_teams) or 0),
            "assignments": int(await self.db.scalar(n_asg) or 0),
        }

    async def subtree_ids(self, root: uuid.UUID) -> set[uuid.UUID]:
        """`root` + every live descendant (MGR scope: own department + sub-departments)."""
        rows = (
            await self.db.execute(
                self._scoped(select(Department.id, Department.parent_id)).where(
                    Department.deleted_at.is_(None)
                )
            )
        ).all()
        children: dict[uuid.UUID | None, list[uuid.UUID]] = {}
        for i, p in rows:
            children.setdefault(p, []).append(i)
        out, stack = {root}, [root]
        while stack:
            for c in children.get(stack.pop(), []):
                if c not in out:
                    out.add(c)
                    stack.append(c)
        return out


class TeamRepository(_Dated[Team]):
    model = Team

    async def current_assignments(self, id_: uuid.UUID) -> int:
        stmt = (
            BaseRepository(self.db, EmployeeAssignment)
            ._live()
            .where(EmployeeAssignment.team_id == id_, EmployeeAssignment.valid_to.is_(None))
        )
        return int(await self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)


class PositionsRepository(BaseRepository[Position]):
    model = Position

    async def code_taken(self, code: str) -> bool:
        stmt = self._live().where(Position.code == code).limit(1)
        return (await self.db.execute(stmt)).first() is not None

    async def filled(self, ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
        """Current assignments per position (EP-ORG-16 `filled`)."""
        if not ids:
            return {}
        stmt = (
            BaseRepository(self.db, EmployeeAssignment)
            ._scoped(select(EmployeeAssignment.position_id, func.count()))
            .where(
                EmployeeAssignment.position_id.in_(set(ids)),
                EmployeeAssignment.valid_to.is_(None),
                EmployeeAssignment.deleted_at.is_(None),
            )
            .group_by(EmployeeAssignment.position_id)
        )
        return {p: int(n) for p, n in (await self.db.execute(stmt)).all() if p is not None}


class TreeRepository(BaseRepository[EmployeeAssignment]):
    model = EmployeeAssignment

    async def members_at(
        self, as_of: date, department_ids: Sequence[uuid.UUID]
    ) -> list[tuple[EmployeeAssignment, str, str, str | None]]:
        """(assignment, employee_code, full_name, position_title) effective on `as_of`.

        Employees are joined for code + name only (level 1–2; no level 3/4 columns selected).
        """
        if not department_ids:
            return []
        stmt = (
            self._scoped(
                select(
                    EmployeeAssignment, Employee.employee_code, Employee.full_name, Position.title
                )
            )
            .join(Employee, Employee.id == EmployeeAssignment.employee_id)
            .outerjoin(Position, Position.id == EmployeeAssignment.position_id)
            .where(
                EmployeeAssignment.deleted_at.is_(None),
                EmployeeAssignment.department_id.in_(set(department_ids)),
                effective_at(EmployeeAssignment, as_of),
            )
            .order_by(Employee.employee_code)
        )
        return [(a, c, n, t) for a, c, n, t in (await self.db.execute(stmt)).all()]

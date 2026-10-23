"""Effective-dated org placement (M1.2 T-612, FR-ORG-04, 05 §2.4/§6ter).

`OrgService.assign` closes the current assignment and opens a new one in the caller's
transaction, under `SELECT … FOR UPDATE` on the employee, and syncs the cached current columns
on `hr.employees`. Overlap of past ranges is rejected here (no `btree_gist`, OQ-05-07); the
partial unique index backs "≤ 1 current row per employee" at DB level.

Every write emits `hr.org_structure_changed` (R-DEC-35) in the same transaction; HTTP routes
EP-ORG-21..23 live in `routes/org.py` (T-613).
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.base_repository import BaseRepository
from app.core.errors import BusinessRuleError, ConflictStateError, NotFoundError, ScopeDeniedError
from app.core.events.outbox import publish_in_tx
from app.modules.hr.models import Employee, EmployeeAssignment, Position, Team
from app.modules.hr.repositories import (
    AssignmentRepository,
    DepartmentRepository,
    EmployeeRepository,
)
from app.modules.hr.repositories.org import DeptRepository

CACHE_FIELDS = ("department_id", "team_id", "position_id", "manager_id")


@dataclass(frozen=True)
class Placement:
    """Where an employee sits from `valid_from` on (the cached columns of `hr.employees`)."""

    department_id: uuid.UUID
    team_id: uuid.UUID | None = None
    position_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None


def _rule(message: str, reason: str, field: str | None = None) -> BusinessRuleError:
    details = {"reason": reason} | ({"field": field} if field else {})
    return BusinessRuleError(message, details=details)


def _snapshot(a: EmployeeAssignment) -> dict[str, str | None]:
    """Audit payload — reference ids + dates only (no level 3/4 data)."""
    keys = ("employee_id", *CACHE_FIELDS, "valid_from", "valid_to")
    return {k: (str(v) if (v := getattr(a, k)) is not None else None) for k in keys}


def _today() -> date:
    return datetime.now(UTC).date()


class OrgService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.assignments = AssignmentRepository(db)
        self.employees = EmployeeRepository(db)
        self.departments = DepartmentRepository(db)
        self.teams = BaseRepository(db, Team)
        self.positions = BaseRepository(db, Position)

    # ---------- validation ----------
    async def _check_placement(self, employee_id: uuid.UUID, p: Placement) -> None:
        if await self.departments.get(p.department_id) is None:
            raise _rule("department not found", "not_found", "department_id")
        if p.team_id is not None:
            team = await self.teams.get(p.team_id)
            if team is None or team.department_id != p.department_id:
                raise _rule("team not in department", "team_outside_department", "team_id")
        if p.position_id is not None:
            pos = await self.positions.get(p.position_id)
            if pos is None or pos.department_id != p.department_id:
                raise _rule("position not in department", "position_outside_department",
                            "position_id")  # fmt: skip
        if p.manager_id is not None:
            if p.manager_id == employee_id:
                raise _rule("employee cannot manage themself", "manager_self", "manager_id")
            if await self.employees.get(p.manager_id) is None:
                raise _rule("manager not found", "not_found", "manager_id")

    async def _event(self, a: EmployeeAssignment, change: str) -> None:
        payload = {"entity": "employee_assignment", "entity_id": str(a.id), "change": change,
                   "employee_id": str(a.employee_id), "department_id": str(a.department_id),
                   "valid_from": a.valid_from.isoformat()}  # fmt: skip
        await publish_in_tx(self.db, event_type="hr.org_structure_changed", producer="hr",
                            aggregate_schema="hr", aggregate_table="employee_assignments",
                            aggregate_id=a.id, payload=payload)  # fmt: skip

    # ---------- writes ----------
    async def _lock(self, employee_id: uuid.UUID) -> Employee:
        emp = await self.employees.lock(employee_id)
        if emp is None:
            raise _rule("employee not found", "not_found", "employee_id")
        return emp

    async def _flush(self) -> None:
        try:
            async with self.db.begin_nested():
                await self.db.flush()
        except IntegrityError as exc:  # partial unique: a concurrent writer won
            raise ConflictStateError("employee assignment changed concurrently") from exc

    async def assign(
        self,
        employee_id: uuid.UUID,
        placement: Placement,
        valid_from: date,
        *,
        actor: uuid.UUID | None,
        reason: str | None = None,
        source: str = "MANUAL",
    ) -> EmployeeAssignment:
        """Close the current assignment at `valid_from` and open a new one (one transaction)."""
        if valid_from > _today():
            raise _rule("valid_from cannot be in the future", "future", "valid_from")
        emp = await self._lock(employee_id)
        await self._check_placement(employee_id, placement)
        current = await self.assignments.current(employee_id)
        if current is not None:
            if valid_from <= current.valid_from:
                raise _rule("valid_from must be after the current assignment start",
                            "not_after_current", "valid_from")  # fmt: skip
            if await self.assignments.overlapping(employee_id, valid_from, None,
                                                  exclude=current.id):  # fmt: skip
                raise _rule("assignment overlaps another period", "overlap", "valid_from")
            before = _snapshot(current)
            await self.assignments.update(current, valid_to=valid_from, updated_by=actor)
            await record_audit(self.db, action="hr.assignment_close", target_schema="hr",
                               target_table="employee_assignments", target_id=current.id,
                               before=before, after=_snapshot(current))  # fmt: skip
            await self._event(current, "updated")
        elif await self.assignments.overlapping(employee_id, valid_from, None, exclude=None):
            raise _rule("assignment overlaps another period", "overlap", "valid_from")
        new = EmployeeAssignment(
            tenant_id=emp.tenant_id, employee_id=employee_id, valid_from=valid_from,
            reason=reason, source=source, created_by=actor,
            **{f: getattr(placement, f) for f in CACHE_FIELDS},
        )  # fmt: skip
        self.db.add(new)
        await self._flush()
        await self._sync_cache(emp, placement, actor)
        await record_audit(self.db, action="hr.assignment_create", target_schema="hr",
                           target_table="employee_assignments", target_id=new.id,
                           after=_snapshot(new))  # fmt: skip
        await self._event(new, "created")
        return new

    async def close_current(
        self, employee_id: uuid.UUID, valid_to: date, *, actor: uuid.UUID | None
    ) -> EmployeeAssignment | None:
        """End the current assignment (termination / archive). `valid_to` > `valid_from`."""
        await self._lock(employee_id)
        current = await self.assignments.current(employee_id)
        if current is None:
            return None
        end = max(valid_to, current.valid_from + timedelta(days=1))
        before = _snapshot(current)
        await self.assignments.update(current, valid_to=end, updated_by=actor)
        await record_audit(self.db, action="hr.assignment_close", target_schema="hr",
                           target_table="employee_assignments", target_id=current.id,
                           before=before, after=_snapshot(current))  # fmt: skip
        await self._event(current, "updated")
        return current

    async def record_placement(
        self, emp: Employee, effective: date, *, actor: uuid.UUID | None, source: str = "MANUAL"
    ) -> EmployeeAssignment | None:
        """Mirror the cached columns of `emp` (already validated by EP-82) into the history.

        Called by `HrService` after employee create/update: no current row → open one from
        `hire_date`; same placement → no-op; current row starting on/after `effective` → amend
        it in place (same-day correction); otherwise close + open at `effective`.
        """
        placement = Placement(**{f: getattr(emp, f) for f in CACHE_FIELDS})
        await self._lock(emp.id)
        current = await self.assignments.current(emp.id)
        if current is None:
            if emp.status == "terminated":
                return None  # history already closed at termination
            _, past = await self.assignments.history(employee_id=emp.id, limit=1)
            start = effective if past or emp.hire_date > effective else emp.hire_date
            return await self.assign(emp.id, placement, start, actor=actor, source=source)
        if all(getattr(current, f) == getattr(placement, f) for f in CACHE_FIELDS):
            return None
        if current.valid_from >= effective:
            before = _snapshot(current)
            values = {f: getattr(placement, f) for f in CACHE_FIELDS}
            await self.assignments.update(current, updated_by=actor, **values)
            await record_audit(self.db, action="hr.assignment_update", target_schema="hr",
                               target_table="employee_assignments", target_id=current.id,
                               before=before, after=_snapshot(current))  # fmt: skip
            await self._event(current, "updated")
            return current
        return await self.assign(emp.id, placement, effective, actor=actor, source=source)

    async def _sync_cache(self, emp: Employee, p: Placement, actor: uuid.UUID | None) -> None:
        values = {f: getattr(p, f) for f in CACHE_FIELDS}
        if any(getattr(emp, f) != v for f, v in values.items()):
            await self.employees.update(emp, updated_by=actor, **values)

    async def get(self, id_: uuid.UUID) -> EmployeeAssignment:
        a = await self.assignments.get(id_)
        if a is None:
            raise NotFoundError("assignment not found")
        return a

    async def update(
        self, id_: uuid.UUID, data: dict[str, object], expected: int, *, actor: uuid.UUID | None
    ) -> EmployeeAssignment:
        """EP-ORG-23: `reason`, `manager_id`, `valid_to` (close early) only."""
        a = await self.get(id_)
        emp = await self._lock(a.employee_id)
        mgr = data.get("manager_id")
        if isinstance(mgr, uuid.UUID):
            if mgr == a.employee_id:
                raise _rule("employee cannot manage themself", "manager_self", "manager_id")
            if await self.employees.get(mgr) is None:
                raise _rule("manager not found", "not_found", "manager_id")
        if "valid_to" in data:
            end = data["valid_to"]
            if a.valid_to is not None:
                raise _rule("assignment already closed", "already_closed", "valid_to")
            if not isinstance(end, date) or end <= a.valid_from:
                raise _rule("valid_to must be after valid_from", "invalid_range", "valid_to")
        before = _snapshot(a)
        await self.assignments.update(a, expected_version=expected, updated_by=actor, **data)
        if a.valid_to is None and "manager_id" in data and emp.manager_id != a.manager_id:
            await self.employees.update(emp, manager_id=a.manager_id, updated_by=actor)
        await record_audit(self.db, action="hr.assignment_update", target_schema="hr",
                           target_table="employee_assignments", target_id=a.id,
                           before=before, after=_snapshot(a))  # fmt: skip
        await self._event(a, "updated")
        return a

    # ---------- reads ----------
    async def at(self, employee_id: uuid.UUID, as_of: date) -> EmployeeAssignment | None:
        """Assignment in force on `as_of` (half-open range), or None."""
        rows, _ = await self.assignments.history(employee_id=employee_id, as_of=as_of, limit=2)
        return rows[0] if rows else None

    async def list_scoped(
        self, root: uuid.UUID | None, *, employee_id: uuid.UUID | None,
        department_id: uuid.UUID | None, as_of: date | None, limit: int, offset: int,
    ) -> tuple[Sequence[EmployeeAssignment], int]:  # fmt: skip
        """EP-ORG-21: `root` = MGR department (own subtree only), None = whole organisation."""
        within = None if root is None else await DeptRepository(self.db).subtree_ids(root)
        if within is not None and department_id is not None and department_id not in within:
            raise ScopeDeniedError("department outside your scope",
                                   details={"department_id": str(department_id)})  # fmt: skip
        return await self.assignments.history(
            employee_id=employee_id, department_id=department_id, as_of=as_of,
            limit=limit, offset=offset, within=within,
        )  # fmt: skip

    async def history(
        self,
        *,
        employee_id: uuid.UUID | None = None,
        department_id: uuid.UUID | None = None,
        as_of: date | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[EmployeeAssignment], int]:
        return await self.assignments.history(
            employee_id=employee_id, department_id=department_id, as_of=as_of,
            limit=limit, offset=offset,
        )  # fmt: skip

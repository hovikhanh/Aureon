"""ACT-create_department / _team / _position / _employee → `hr` public services (10 §7.2.4, #4).

Order inside a document: department → team → position → employee; `manager_code` is applied in
a second pass (`ctx.post`) once every employee of the roster exists. Structure ACTs require
`hr:admin`; ACT-create_employee any-of `hr:write | hr:admin` (R-DEC-61). Level-4 columns (salary,
national id, …) are written only when the committer may see level 4 — otherwise they are dropped
with a warning (never stored in `document_actions.params`).
"""

from __future__ import annotations

import re
import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import NotFoundError
from app.core.field_policy import sees_level4
from app.modules.hr.schemas import DepartmentCreate, EmployeeCreate, SalaryCreate
from app.modules.hr.schemas.org import PositionCreate, TeamCreate
from app.modules.hr.services.hr_service import HrService
from app.modules.hr.services.structure_service import StructureService
from app.modules.idp.services.actions.registry import (
    ActionContext,
    ActionDef,
    ActionOutcome,
    RowError,
    ref,
    register,
)

_ADMIN = ("hr:admin",)
_LEVEL4 = frozenset({"salary", "date_of_birth", "address", "national_id", "bank_account"})


def _err(field: str, code: str, message: str) -> RowError:
    return {"field": field, "code": code, "message": message}


def _slug(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", text.upper()).strip("-")[:40] or "POS"


async def _department_id(db: AsyncSession, ctx: ActionContext, code: str) -> uuid.UUID | None:
    return ctx.recall("department", code) or await HrService(db).department_id_by_code(code)


async def _require_department(
    db: AsyncSession, ctx: ActionContext, code: str, field: str = "department_code"
) -> list[RowError]:
    if ctx.is_planned("department", code) or await _department_id(db, ctx, code) is not None:
        return []
    return [_err(field, "not_found", f"department {code} not found")]


def _first_id(outcome: ActionOutcome) -> tuple[uuid.UUID, bool]:
    r = outcome.result_refs[0]
    return uuid.UUID(r["id"]), bool(r.get("reused"))


# ---------------------------------------------------------------- department
class DepartmentParams(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    parent_code: str | None = Field(default=None, max_length=50)


async def _dept_validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    errors: list[RowError] = []
    if p.parent_code:
        errors += await _require_department(db, ctx, p.parent_code, "parent_code")
    if await HrService(db).default_organization_id() is None:
        errors.append(_err("organization_id", "not_found", "no live organization"))
    ctx.plan("department", p.code)
    return errors


async def _dept_run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    hr = HrService(db)
    existing = await _department_id(db, ctx, p.code)
    if existing is not None:  # live `code` → reuse, never touched by undo
        ctx.remember("department", p.code, existing)
        return ActionOutcome([ref("hr", "departments", existing, reused=True)])
    parent = await _department_id(db, ctx, p.parent_code) if p.parent_code else None
    org = await hr.default_organization_id()
    if org is None:
        raise NotFoundError("organization not found", details={"field": "organization_id"})
    body = DepartmentCreate(name=p.name, code=p.code, parent_id=parent, organization_id=org)
    out = await hr.create_department(user, body, source=ctx.source)
    ctx.remember("department", p.code, out.id)
    return ActionOutcome([ref("hr", "departments", out.id)], target_version=out.version)


async def _dept_undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    id_, reused = _first_id(outcome)
    if not reused:
        await HrService(db).archive_department(user, id_)


register(ActionDef(
    name="ACT-create_department", module="hr", required_permission=_ADMIN, reversible=True,
    is_finance=False, params_model=DepartmentParams, validate=_dept_validate, run=_dept_run,
    undo=_dept_undo,
))  # fmt: skip


# ---------------------------------------------------------------- team
class TeamParams(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    department_code: str = Field(min_length=1, max_length=50)


async def _team_validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    return await _require_department(db, ctx, p.department_code)


async def _team_run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    svc = StructureService(db)
    dept = await _department_id(db, ctx, p.department_code)
    if dept is None:
        raise NotFoundError("department not found", details={"field": "department_code"})
    existing = await svc.team_id_by_code(dept, p.code)
    if existing is not None:
        return ActionOutcome([ref("hr", "teams", existing, reused=True)])
    out = await svc.create_team(user, TeamCreate(department_id=dept, code=p.code, name=p.name),
                                source=ctx.source)  # fmt: skip
    return ActionOutcome([ref("hr", "teams", out.id)], target_version=out.version)


async def _team_undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    id_, reused = _first_id(outcome)
    if not reused:
        await StructureService(db).archive_team(user, id_)


register(ActionDef(
    name="ACT-create_team", module="hr", required_permission=_ADMIN, reversible=True,
    is_finance=False, params_model=TeamParams, validate=_team_validate, run=_team_run,
    undo=_team_undo,
))  # fmt: skip


# ---------------------------------------------------------------- position
class PositionParams(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    department_code: str = Field(min_length=1, max_length=50)


async def _pos_validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    return await _require_department(db, ctx, p.department_code)


async def _pos_run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    dept = await _department_id(db, ctx, p.department_code)
    if dept is None:
        raise NotFoundError("department not found", details={"field": "department_code"})
    existing = await HrService(db).position_id_by_title(dept, p.title)
    if existing is not None:  # `(department, title)` → reuse
        return ActionOutcome([ref("hr", "positions", existing, reused=True)])
    code = f"{p.department_code.upper()}-{_slug(p.title)}-{uuid.uuid4().hex[:6].upper()}"
    body = PositionCreate(department_id=dept, code=code, title=p.title, headcount_budget=0)
    out = await StructureService(db).create_position(user, body, source=ctx.source)
    return ActionOutcome([ref("hr", "positions", out.id)], target_version=out.version)


async def _pos_undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    id_, reused = _first_id(outcome)
    if not reused:
        await StructureService(db).archive_position(user, id_)


register(ActionDef(
    name="ACT-create_position", module="hr", required_permission=_ADMIN, reversible=True,
    is_finance=False, params_model=PositionParams, validate=_pos_validate, run=_pos_run,
    undo=_pos_undo,
))  # fmt: skip


# ---------------------------------------------------------------- employee
class EmployeeParams(BaseModel):
    employee_code: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    department_code: str = Field(min_length=1, max_length=50)
    manager_code: str | None = Field(default=None, max_length=50)
    hire_date: date
    status: str = "probation"
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=30)
    # level 4 — written only when the committer may see level 4 (else dropped + warning)
    salary: int | None = Field(default=None, gt=0)
    date_of_birth: date | None = None
    address: str | None = Field(default=None, max_length=500)
    national_id: str | None = Field(default=None, max_length=20)
    bank_account: str | None = Field(default=None, max_length=40)


async def _emp_validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    errors = await _require_department(db, ctx, p.department_code)
    if ctx.is_planned("employee", p.employee_code) or await HrService(db).employee_id_by_code(
        p.employee_code
    ):  # upsert of employees is deferred (M2.x) → duplicate row error
        errors.append(_err("employee_code", "DUPLICATE", "employee_code exists"))
    ctx.plan("employee", p.employee_code)
    if p.manager_code:
        manager_code = p.manager_code

        async def _manager_exists() -> list[RowError]:  # the manager may be a later row
            if ctx.is_planned("employee", manager_code) or await HrService(db).employee_id_by_code(
                manager_code
            ):
                return []
            return [_err("manager_code", "not_found", f"employee {manager_code} not found")]

        ctx.deferred.append(_manager_exists)
    return errors


def _level4_allowed(user: Principal) -> bool:
    return sees_level4(user)


async def _emp_run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    hr = HrService(db)
    dept = await _department_id(db, ctx, p.department_code)
    if dept is None:
        raise NotFoundError("department not found", details={"field": "department_code"})
    level4 = {k: getattr(p, k) for k in _LEVEL4 if getattr(p, k) is not None}
    if level4 and not _level4_allowed(user):
        ctx.warnings.append("idp.warn.level4_dropped")
        level4 = {}
    body = EmployeeCreate(
        employee_code=p.employee_code, full_name=p.full_name, title=p.title, email=p.email,
        phone=p.phone, department_id=dept, status=p.status, hire_date=p.hire_date,
        **{k: v for k, v in level4.items() if k != "salary"},
    )  # fmt: skip
    out = await hr.create_employee(user, body, source=ctx.source,
                                   source_document_id=ctx.source_document_id)  # fmt: skip
    ctx.remember("employee", p.employee_code, out.id)
    if "salary" in level4:
        await hr.add_salary(user, out.id, SalaryCreate(effective_date=p.hire_date,
                                                       base_salary=level4["salary"]))  # fmt: skip
    outcome = ActionOutcome([ref("hr", "employees", out.id)], target_version=out.version)
    if p.manager_code:
        manager_code = p.manager_code

        async def _assign_manager() -> None:  # pass 2 — every employee of the doc exists
            mgr = ctx.recall("employee", manager_code) or await hr.employee_id_by_code(manager_code)
            if mgr is None:
                raise NotFoundError("manager not found", details={"field": "manager_code"})
            outcome.target_version = await hr.set_manager(user, out.id, mgr)

        ctx.post.append(_assign_manager)
    return outcome


async def _emp_undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    id_, _ = _first_id(outcome)
    await HrService(db).delete_employee(user, id_)  # soft delete + closes the assignment


register(ActionDef(
    name="ACT-create_employee", module="hr", required_permission=("hr:write", "hr:admin"),
    reversible=True, is_finance=False, params_model=EmployeeParams, validate=_emp_validate,
    run=_emp_run, undo=_emp_undo, level4_params=_LEVEL4,
))  # fmt: skip

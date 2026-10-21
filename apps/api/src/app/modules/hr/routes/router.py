"""HTTP routes for `hr` — EP-80..87 (10 §3.8, §4.8).

One permission per route, `Idem` on create / action POSTs, `IfMatch` + body `version` on
PATCH, `Page` on lists, commit at the end of the request.
"""

import uuid
from typing import Annotated, Any

from fastapi import Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_permission
from app.core.envelope import Page
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.hr.schemas import (
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeOut,
    EmployeeStatus,
    EmployeeUpdate,
    SalaryCreate,
    SalaryOut,
)
from app.modules.hr.services.hr_service import HrService, department_out

router = EnvelopeRouter(tags=["hr"])

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_permission("hr:read"))]
Writer = Annotated[Principal, Depends(require_permission("hr:write"))]


# ---------- EP-81 departments (L C R U) ----------
@router.get("/hr/departments", response_model=list[DepartmentOut])
async def list_departments(
    db: Db, _: Reader,
    page: Annotated[PageParams, Depends(page_params("name", "code"))],
    parent_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    items, total = await HrService(db).list_departments(page, parent_id=parent_id)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/hr/departments", response_model=DepartmentOut, status_code=201)
async def create_department(body: DepartmentCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return DepartmentOut.model_validate(hit)
    out = await HrService(db).create_department(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/hr/departments/{department_id}", response_model=DepartmentOut)
async def get_department(department_id: uuid.UUID, db: Db, _: Reader) -> Any:
    return department_out(await HrService(db).get_department(department_id))


@router.patch("/hr/departments/{department_id}", response_model=DepartmentOut)
async def update_department(
    department_id: uuid.UUID, body: DepartmentUpdate, db: Db, user: Writer,
    if_match: IfMatch = None,
) -> Any:  # fmt: skip
    exp = expected_version(if_match, body.version)
    out = await HrService(db).update_department(user, department_id, body, exp)
    await db.commit()
    return out


# ---------- EP-82 employees (L C R U D) ----------
@router.get("/hr/employees", response_model=list[EmployeeOut])
async def list_employees(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("full_name", "employee_code", "hire_date"))],
    department_id: uuid.UUID | None = None, status: EmployeeStatus | None = None,
    q: str | None = None,
) -> Any:  # fmt: skip
    items, total = await HrService(db).list_employees(
        user, page, department_id=department_id, status=status, q=q
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/hr/employees", response_model=EmployeeOut, status_code=201)
async def create_employee(body: EmployeeCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return EmployeeOut.model_validate(hit)
    out = await HrService(db).create_employee(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/hr/employees/{employee_id}", response_model=EmployeeOut)
async def get_employee(employee_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return await HrService(db).get_employee(user, employee_id)


@router.patch("/hr/employees/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: uuid.UUID, body: EmployeeUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await HrService(db).update_employee(user, employee_id, body, exp)
    await db.commit()
    return out


@router.delete("/hr/employees/{employee_id}", status_code=204, response_class=Response)
async def delete_employee(employee_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await HrService(db).delete_employee(user, employee_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-83 salary history (L C, level 4) ----------
@router.get("/hr/employees/{employee_id}/salary-history", response_model=list[SalaryOut])
async def list_salary_history(
    employee_id: uuid.UUID, db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("effective_date"))],
) -> Any:  # fmt: skip
    items, total = await HrService(db).list_salary(user, employee_id, page)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post(
    "/hr/employees/{employee_id}/salary-history", response_model=SalaryOut, status_code=201
)
async def add_salary_history(
    employee_id: uuid.UUID, body: SalaryCreate, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return SalaryOut.model_validate(hit)
    out = await HrService(db).add_salary(user, employee_id, body)
    await db.commit()
    await idem.remember(out)
    return out

"""HTTP routes for `hr` — EP-80..87 (10 §3.8, §4.8).

One permission per route, `Idem` on create / action POSTs, `IfMatch` + body `version` on
PATCH, `Page` on lists, commit at the end of the request.
"""

import uuid
from typing import Annotated, Any

from fastapi import Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_permission, require_pillar_permission
from app.core.envelope import Page
from app.core.errors import BadRequestError
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.hr.routes.org import AsOf
from app.modules.hr.routes.org import router as org_router
from app.modules.hr.schemas import (
    ApprovalIn,
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeOut,
    EmployeeStatus,
    EmployeeUpdate,
    EmployeeWorkloadOut,
    HiringPlanCreate,
    HiringPlanOut,
    HiringPlanUpdate,
    HiringStatus,
    HrDashboardOut,
    SalaryCreate,
    SalaryOut,
)
from app.modules.hr.services.dashboard_service import HrDashboardService
from app.modules.hr.services.hiring_service import HiringPlanService, plan_out
from app.modules.hr.services.hr_service import HrService, department_out, today
from app.modules.hr.services.metrics import Period, resolve_period

router = EnvelopeRouter(tags=["hr"])
router.include_router(org_router)  # D01 `/org/*` (EP-ORG, M1.2) — same `hr` module (R-DEC-24)

Db = Annotated[AsyncSession, Depends(get_db)]
# Bản ghi con người (O) cô lập theo khối (R-DEC-12a): DIR ngoài khối O → 403.
Reader = Annotated[Principal, Depends(require_pillar_permission("hr:read"))]
Writer = Annotated[Principal, Depends(require_pillar_permission("hr:write"))]
# R-DEC-30: ghi cơ cấu (EP-ORG-07/09/10) = hr:admin (CEO, ADM, DIR khối O).
StructureAdmin = Annotated[Principal, Depends(require_pillar_permission("hr:admin"))]
# hr:approve là cổng ngân sách của Finance-DIR (chỉ CFO nền v2.1 có hr:approve); dependency
# chặn vai không có quyền, service `decide` siết thêm "đúng Finance-DIR (khối F)".
Approver = Annotated[Principal, Depends(require_permission("hr:approve"))]
# Dashboard HR là tổng hợp nhưng chứa quỹ lương (mức 4): mở cho CEO/HR-DIR(O)/Finance-DIR(F),
# service lọc chi tiết; vai query khối khác (Sales/Product/Risk-DIR) không xem → 403 ở service.
Querier = Annotated[Principal, Depends(require_permission("hr:query"))]


async def period_dep(period: str | None = None) -> Period:
    try:
        return resolve_period(period, today())
    except ValueError as exc:
        raise BadRequestError(str(exc), details={"param": "period"}) from exc


PeriodQ = Annotated[Period, Depends(period_dep)]


# ---------- EP-80 dashboard (10 §5) ----------
@router.get("/hr/dashboard", response_model=HrDashboardOut)
async def hr_dashboard(db: Db, user: Querier, period: PeriodQ, response: Response) -> Any:
    out = await HrDashboardService(db).dashboard(user, period, today())
    response.headers["Cache-Control"] = "private, max-age=60"
    response.headers["Vary"] = "Authorization"
    return out


# ---------- EP-87 workload (METRIC-HR-03) ----------
@router.get("/hr/workload", response_model=list[EmployeeWorkloadOut])
async def hr_workload(
    db: Db, user: Querier, period: PeriodQ, department_id: uuid.UUID | None = None
) -> Any:
    as_of = min(period.end, today())
    return await HrDashboardService(db).workload(user, department_id=department_id, as_of=as_of)


# ---------- EP-81 departments (L C R U) ----------
@router.get("/hr/departments", response_model=list[DepartmentOut])
async def list_departments(
    db: Db, _: Reader, as_of: AsOf,
    page: Annotated[PageParams, Depends(page_params("name", "code"))],
    parent_id: uuid.UUID | None = None, organization_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    items, total = await HrService(db).list_departments(
        page, parent_id=parent_id, organization_id=organization_id, as_of=as_of
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/hr/departments", response_model=DepartmentOut, status_code=201)
async def create_department(
    body: DepartmentCreate, db: Db, user: StructureAdmin, idem: Idem
) -> Any:
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
    department_id: uuid.UUID, body: DepartmentUpdate, db: Db, user: StructureAdmin,
    if_match: IfMatch = None,
) -> Any:  # fmt: skip
    exp = expected_version(if_match, body.version)
    out = await HrService(db).update_department(user, department_id, body, exp)
    await db.commit()
    return out


@router.delete("/hr/departments/{department_id}", status_code=204, response_class=Response)
async def archive_department(department_id: uuid.UUID, db: Db, user: StructureAdmin) -> Response:
    await HrService(db).archive_department(user, department_id)
    await db.commit()
    return Response(status_code=204)


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


# ---------- EP-84 hiring plans (L C R U D) ----------
@router.get("/hr/hiring-plans", response_model=list[HiringPlanOut])
async def list_hiring_plans(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("target_date", "priority", "status"))],
    department_id: uuid.UUID | None = None, status: HiringStatus | None = None,
    delayed: bool | None = None,
) -> Any:  # fmt: skip
    items, total = await HiringPlanService(db).list_plans(
        user, page, department_id=department_id, status=status, delayed=delayed, today=today()
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/hr/hiring-plans", response_model=HiringPlanOut, status_code=201)
async def create_hiring_plan(body: HiringPlanCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return HiringPlanOut.model_validate(hit)
    out = await HiringPlanService(db).create(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/hr/hiring-plans/{plan_id}", response_model=HiringPlanOut)
async def get_hiring_plan(plan_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return plan_out(await HiringPlanService(db).get(user, plan_id))


@router.patch("/hr/hiring-plans/{plan_id}", response_model=HiringPlanOut)
async def update_hiring_plan(
    plan_id: uuid.UUID, body: HiringPlanUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await HiringPlanService(db).update(user, plan_id, body, exp)
    await db.commit()
    return out


@router.delete("/hr/hiring-plans/{plan_id}", status_code=204, response_class=Response)
async def delete_hiring_plan(plan_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await HiringPlanService(db).delete(user, plan_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-85 submit ----------
@router.post("/hr/hiring-plans/{plan_id}/submit", response_model=HiringPlanOut)
async def submit_hiring_plan(plan_id: uuid.UUID, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay({"plan_id": str(plan_id)})) is not None:
        return HiringPlanOut.model_validate(hit)
    out = await HiringPlanService(db).submit(user, plan_id)
    await db.commit()
    await idem.remember(out)
    return out


# ---------- EP-86 approve / reject ----------
@router.post("/hr/hiring-plans/{plan_id}/approve", response_model=HiringPlanOut)
async def approve_hiring_plan(
    plan_id: uuid.UUID, body: ApprovalIn, db: Db, user: Approver, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return HiringPlanOut.model_validate(hit)
    out = await HiringPlanService(db).decide(user, plan_id, body)
    await db.commit()
    await idem.remember(out)
    return out

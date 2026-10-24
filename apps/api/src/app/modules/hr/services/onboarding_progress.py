"""`hr` source of the onboarding `progress` (EP-ADM-13, `core/onboarding`) — counts/ids only."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import Department, Employee, Organization
from app.modules.hr.repositories import (
    DepartmentRepository,
    EmployeeRepository,
    OrganizationRepository,
)


async def hr_progress(db: AsyncSession) -> dict[str, Any]:
    orgs = OrganizationRepository(db)
    ready = select(func.count()).select_from(
        orgs._live().where(func.length(func.trim(Organization.name)) > 0).subquery()
    )  # fmt: skip
    depts = DepartmentRepository(db)._live().where(Department.valid_to.is_(None))
    emps = EmployeeRepository(db)._live().where(Employee.status != "terminated")
    ids = set((await db.execute(emps.with_only_columns(Employee.id))).scalars())
    n_depts = select(func.count()).select_from(depts.subquery())
    return {
        "organization_ready": int((await db.execute(ready)).scalar_one()) > 0,
        "departments": int((await db.execute(n_depts)).scalar_one()),
        "employees": len(ids),
        "employee_ids": ids,
    }

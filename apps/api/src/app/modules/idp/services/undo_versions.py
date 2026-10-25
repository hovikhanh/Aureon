"""Current `version` of a committed target row, through its owning module's public service
(EP-DC-24 conflict check, R-DEC-66). `None` = the row is gone or has no version to compare."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import NotFoundError


async def _read(db: AsyncSession, user: Principal, table: str, id_: uuid.UUID) -> Any:
    from app.modules.execution.services.kpi_service import KpiService
    from app.modules.execution.services.okr_service import OkrService
    from app.modules.execution.services.task_service import TaskService
    from app.modules.finance.services.invoice_service import InvoiceService
    from app.modules.hr.services.hr_service import HrService
    from app.modules.hr.services.structure_service import StructureService

    match table:
        case "hr.departments":
            return await HrService(db).get_department(id_)
        case "hr.teams":
            return await StructureService(db).get_team(user, id_)
        case "hr.positions":
            return await StructureService(db).get_position(user, id_)
        case "hr.employees":
            return await HrService(db).get_employee_row(user, id_)
        case "execution.objectives":
            return await OkrService(db).get_objective(user, id_)
        case "execution.key_results":
            return await OkrService(db).get_kr(user, id_)
        case "execution.kpis":
            return await KpiService(db).get_kpi(user, id_)
        case "execution.kpi_targets":
            return await KpiService(db).get_target(user, id_)
        case "execution.tasks":
            return await TaskService(db).get(user, id_)
        case "finance.invoices":
            return await InvoiceService(db).get(id_)
    return None


async def current_version(
    db: AsyncSession, user: Principal, table: str, id_: uuid.UUID
) -> int | None:
    try:
        row = await _read(db, user, table, id_)
    except NotFoundError:
        return None
    version = getattr(row, "version", None)
    return int(version) if version is not None else None

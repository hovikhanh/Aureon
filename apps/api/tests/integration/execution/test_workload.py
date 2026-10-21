"""T-133 — public `workload(db, department_id, as_of)` over real rows (DEC-226)."""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.services.workload import WorkloadRow, workload
from tests.conftest import ApiClient
from tests.integration.execution.helpers import make_task

pytestmark = pytest.mark.integration


async def test_workload_by_department(api: ApiClient, db_session: AsyncSession) -> None:
    dept, emp, other = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    for h in ("30", "20"):
        await make_task(api, department_id=str(dept), assignee_id=str(emp), estimate_hours=h)
    await make_task(api, department_id=str(dept), assignee_id=str(other))
    await make_task(api, department_id=str(dept), assignee_id=str(other), status="cancelled")
    await make_task(api, department_id=str(uuid.uuid4()), assignee_id=str(emp))
    await make_task(api, department_id=str(dept))  # unassigned
    rows = await workload(db_session, dept, date(2037, 1, 15))
    assert rows == [
        WorkloadRow(employee_id=emp, open_tasks=2, estimate_hours=50.0, load_pct=125.0,
                    overloaded=True),
        WorkloadRow(employee_id=other, open_tasks=1, estimate_hours=4.0, load_pct=10.0,
                    overloaded=False),
    ]  # fmt: skip
    everyone = await workload(db_session, None, date(2037, 1, 15))
    mine = next(r for r in everyone if r.employee_id == emp)
    assert mine.open_tasks == 3 and mine.estimate_hours == 54.0

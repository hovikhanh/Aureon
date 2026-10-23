"""T-612 — effective-dated employee assignments (05 §2.4/§6ter, FR-ORG-04).

TC-M12-01 (T-612 part): backfill — one current assignment per live employee, matching the
cached columns. TC-M12-02: ≤ 1 current row, close + open in one transaction, rule violations
→ BusinessRuleError, EP-82 create/update/delete keep the history in sync.
TC-M12-03 (service part): `as_of` lookups on the half-open boundary. HTTP (EP-ORG-21..23) = T-613.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessRuleError
from app.modules.hr.models import Employee, EmployeeAssignment, Team
from app.modules.hr.services.org_service import OrgService, Placement
from app.seed.ids import seed_uuid
from tests.conftest import ApiClient
from tests.integration.hr.helpers import make_department, make_employee

pytestmark = pytest.mark.integration

SAL, SVC = seed_uuid("department", "SAL"), seed_uuid("department", "SVC")
D1, D2 = date(2026, 3, 1), date(2026, 6, 1)


async def _new_employee(db: AsyncSession, hire: date = date(2025, 1, 1)) -> Employee:
    code = f"T612-{uuid.uuid4().hex[:8]}"
    emp = Employee(employee_code=code, full_name="Trần Thị Thử", normalized_name="tran thi thu",
                   department_id=SAL, status="active", hire_date=hire, source="MANUAL")  # fmt: skip
    db.add(emp)
    await db.flush()
    await OrgService(db).assign(emp.id, Placement(SAL), hire, actor=None)
    return emp


async def _rule(coro: object, reason: str) -> None:
    with pytest.raises(BusinessRuleError) as exc:
        await coro  # type: ignore[misc]
    assert exc.value.details["reason"] == reason


async def test_backfill_matches_cached_columns(db_session: AsyncSession) -> None:
    live = select(func.count()).select_from(Employee).where(Employee.deleted_at.is_(None))
    current = (
        select(func.count())
        .select_from(EmployeeAssignment)
        .join(Employee, Employee.id == EmployeeAssignment.employee_id)
        .where(
            EmployeeAssignment.valid_to.is_(None),
            Employee.deleted_at.is_(None),
            Employee.termination_date.is_(None),
        )
    )
    employed = live.where(Employee.termination_date.is_(None))
    assert await db_session.scalar(current) == await db_session.scalar(employed)
    mismatch = text(
        "SELECT count(*) FROM hr.employee_assignments a JOIN hr.employees e "
        "ON e.id = a.employee_id WHERE a.valid_to IS NULL AND a.deleted_at IS NULL "
        "AND (a.department_id <> e.department_id "
        "OR a.team_id IS DISTINCT FROM e.team_id OR a.manager_id IS DISTINCT FROM e.manager_id)"
    )
    assert await db_session.scalar(mismatch) == 0


async def test_transfer_closes_old_opens_new_and_syncs_cache(db_session: AsyncSession) -> None:
    emp = await _new_employee(db_session)
    svc = OrgService(db_session)
    new = await svc.assign(emp.id, Placement(SVC), D2, actor=None, reason="Điều chuyển")
    history, total = await svc.history(employee_id=emp.id)
    assert total == 2
    assert (history[0].department_id, history[0].valid_to) == (SAL, D2)
    assert (history[1].id, history[1].valid_to) == (new.id, None)
    await db_session.refresh(emp)
    assert emp.department_id == SVC
    # TC-M12-03: half-open boundary
    before = await svc.at(emp.id, date(2026, 5, 31))
    on = await svc.at(emp.id, D2)
    assert before is not None and before.department_id == SAL
    assert on is not None and on.department_id == SVC
    assert await svc.at(emp.id, date(2024, 12, 31)) is None


async def test_rule_violations(db_session: AsyncSession) -> None:
    emp = await _new_employee(db_session)
    svc = OrgService(db_session)
    await _rule(svc.assign(emp.id, Placement(SVC), date(2025, 1, 1), actor=None),
                "not_after_current")  # fmt: skip
    await _rule(svc.assign(emp.id, Placement(SVC, manager_id=emp.id), D1, actor=None),
                "manager_self")  # fmt: skip
    sal_team = await db_session.scalar(select(Team.id).where(Team.department_id == SAL).limit(1))
    await _rule(svc.assign(emp.id, Placement(SVC, team_id=sal_team), D1, actor=None),
                "team_outside_department")  # fmt: skip
    await _rule(svc.assign(emp.id, Placement(uuid.uuid4()), D1, actor=None), "not_found")


async def test_overlap_with_closed_history_is_rejected(db_session: AsyncSession) -> None:
    emp = await _new_employee(db_session)
    svc = OrgService(db_session)
    await svc.close_current(emp.id, D2, actor=None)
    await _rule(svc.assign(emp.id, Placement(SVC), D1, actor=None), "overlap")
    reopened = await svc.assign(emp.id, Placement(SVC), D2, actor=None)  # adjacent → ok
    assert reopened.valid_from == D2


async def test_db_allows_one_current_row_only(db_session: AsyncSession) -> None:
    emp = await _new_employee(db_session)
    db_session.add(EmployeeAssignment(employee_id=emp.id, department_id=SVC, valid_from=D2,
                                      source="MANUAL"))  # fmt: skip
    with pytest.raises(IntegrityError, match="uq_employee_assignments_employee_id_current"):
        await db_session.flush()
    await db_session.rollback()


async def test_ep82_keeps_history_in_sync(api: ApiClient, db_session: AsyncSession) -> None:
    d1, d2 = await make_department(api), await make_department(api)
    e = await make_employee(api, d1["id"])
    svc = OrgService(db_session)
    rows, total = await svc.history(employee_id=uuid.UUID(e["id"]))
    assert total == 1 and rows[0].valid_from == date(2025, 1, 15) and rows[0].valid_to is None
    r = await api.call("PATCH", f"/hr/employees/{e['id']}", "HR_MANAGER",
                       json={"department_id": d2["id"], "version": e["version"]})  # fmt: skip
    assert r.status_code == 200, r.text
    rows, total = await svc.history(employee_id=uuid.UUID(e["id"]))
    assert total == 2 and str(rows[1].department_id) == d2["id"] and rows[0].valid_to is not None
    d = await api.call("DELETE", f"/hr/employees/{e['id']}", "HR_MANAGER")
    assert d.status_code == 204, d.text
    assert await svc.assignments.current(uuid.UUID(e["id"])) is None

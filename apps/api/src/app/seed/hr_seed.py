"""HR seed v3 (T-603b, 08 §2.1, R-DEC-23) — company ABC: 7 departments, their teams, ~150
employees with a reporting line (`manager_id`), 3 months of encrypted salary history and 5
hiring plans. Org data comes from `org_data` (pure, script-computed). Idempotent per group
(`source='SEED'`).

Departments reuse `seed_uuid("department", code)` so finance budgets (FIN-06), execution and
the demo users join the same rows. PII is fake (DEC-136); level-4 columns are
pgcrypto-encrypted by the column type (DEC-207).
"""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_repository import BaseRepository
from app.modules.hr.models import Department, Employee, HiringPlan, SalaryHistory, Team
from app.modules.hr.repositories import DepartmentRepository
from app.modules.hr.services.hr_service import normalize_name
from app.seed.ids import seed_uuid
from app.seed.org_data import DEPARTMENTS, PEOPLE

SEED: dict[str, Any] = {"source": "SEED"}
SALARY_MONTHS = (date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1))
# code, dept, title/position, headcount, filled, status, start, target fill date
# T-237 rebalance: exactly ONE plan is late and by ≤ 45 days (HP-2026-07, 40 days at 20/10) →
# METRIC-HR-04 = 1, warning (not critical) → pillar O stays YELLOW, no critical. The others are
# either future-dated (not yet late) or submitted.
PLANS = (
    ("HP-2026-05", "PRD", "Backend developer", 2, 0, "approved", date(2026, 9, 1),
     date(2026, 10, 31)),
    ("HP-2026-06", "SVC", "Kỹ thuật viên", 3, 1, "in_progress", date(2026, 7, 1),
     date(2026, 11, 15)),
    ("HP-2026-07", "SAL", "Sales Hà Nội", 6, 2, "in_progress", date(2026, 6, 15),
     date(2026, 9, 10)),
    ("HP-2026-03", "FIN", "Kế toán tổng hợp", 1, 0, "in_progress", date(2026, 5, 4),
     date(2026, 11, 30)),
    ("HP-2026-08", "SAL", "Account manager", 2, 0, "submitted", date(2026, 10, 1),
     date(2026, 12, 15)),
)  # fmt: skip


def emp_id(code: str) -> uuid.UUID:
    return seed_uuid("employee", code)


async def _has(db: AsyncSession, model: Any) -> bool:
    stmt = select(func.count()).select_from(model).where(model.source == "SEED")
    return int((await db.execute(stmt)).scalar_one()) > 0


def _fake_pii(n: int) -> dict[str, Any]:
    """Synthetic level-4 values (DEC-136) — clearly fake, encrypted at rest."""
    return {"national_id": f"0790{n:08d}", "bank_account": f"9704{n:09d}",
            "date_of_birth": date(1985 + n % 15, 1 + n % 12, 1 + n % 27)}  # fmt: skip


async def seed_org(db: AsyncSession) -> int:
    if await _has(db, Department):
        return 0
    db.add_all([
        Department(id=seed_uuid("department", d.code), code=d.code, name=d.name, aliases=[],
                   **SEED)
        for d in DEPARTMENTS
    ])  # fmt: skip
    await db.flush()
    teams = [(d.code, code, name) for d in DEPARTMENTS for code, name in d.teams]
    db.add_all([
        Team(id=seed_uuid("team", code), department_id=seed_uuid("department", dept), code=code,
             name=name, **SEED)
        for dept, code, name in teams
    ])  # fmt: skip
    return len(DEPARTMENTS) + len(teams)


async def seed_employees(db: AsyncSession) -> int:
    if await _has(db, Employee):
        return 0
    rows = [
        Employee(
            id=emp_id(p.code), employee_code=p.code, full_name=p.name,
            normalized_name=normalize_name(p.name), department_id=seed_uuid("department", p.dept),
            team_id=seed_uuid("team", p.team) if p.team else None,
            manager_id=emp_id(p.manager) if p.manager else None, status=p.status,
            hire_date=p.hired, termination_date=p.left,
            contract_type="probation" if p.status == "probation" else "permanent",
            **_fake_pii(n), **SEED,
        )
        for n, p in enumerate(PEOPLE, start=1)
    ]  # fmt: skip
    db.add_all(rows)
    await db.flush()
    salaries = [
        SalaryHistory(employee_id=emp_id(p.code), base_salary=p.salary_mil * 1_000_000,
                      currency="VND", effective_date=month, reason="Dữ liệu seed lịch sử")
        for p in PEOPLE
        for month in SALARY_MONTHS
        if (p.left is None or p.left >= month) and p.hired <= month
    ]  # fmt: skip
    db.add_all(salaries)
    await db.flush()
    await _set_heads(db)
    return len(rows) + len(salaries)


async def _set_heads(db: AsyncSession) -> None:
    """Department heads / team leads = the `lead` people of `org_data` (reporting line)."""
    depts, teams = DepartmentRepository(db), BaseRepository(db, Team)
    for p in PEOPLE:
        if not p.lead:
            continue
        row = await (teams.get(seed_uuid("team", p.team)) if p.team else
                     depts.get(seed_uuid("department", p.dept)))  # fmt: skip
        if isinstance(row, Team):
            row.lead_employee_id = emp_id(p.code)
        elif isinstance(row, Department):
            row.head_employee_id = emp_id(p.code)


async def seed_hiring_plans(db: AsyncSession, manager: uuid.UUID, approver: uuid.UUID) -> int:
    if await _has(db, HiringPlan):
        return 0
    db.add_all([
        HiringPlan(
            id=seed_uuid("hiring_plan", code), title=f"{code} — {title}",
            department_id=seed_uuid("department", dept), position=title, headcount=hc,
            filled=filled, priority="high", status=status, currency="VND", start_date=start,
            target_fill_date=due, hiring_manager_id=manager,
            approved_by=approver if status != "submitted" else None,
            budget_allocated=hc * 30_000_000, budget_spent=filled * 5_000_000, **SEED,
        )
        for code, dept, title, hc, filled, status, start, due in PLANS
    ])  # fmt: skip
    return len(PLANS)


async def seed_hr(db: AsyncSession, manager: uuid.UUID, approver: uuid.UUID) -> dict[str, int]:
    out = {"org": await seed_org(db)}
    await db.flush()
    out["employees_salaries"] = await seed_employees(db)
    out["hiring_plans"] = await seed_hiring_plans(db, manager, approver)
    await db.flush()
    return out

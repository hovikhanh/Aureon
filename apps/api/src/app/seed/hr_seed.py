"""HR seed (T-236, DEC-208) — 5 departments, 3 teams, 10 employees, 5 hiring plans,
3 months of encrypted salary history. Idempotent per group (`source='SEED'`).

Departments reuse `seed_uuid("department", code)` so finance budgets (FIN-06) join the same
rows. Employees: 5 active · 3 probation · 2 leavers (`terminated` in the last 12 months →
METRIC-HR-02 > 0). Plans: HP-2026-06 (20 days late) and HP-2026-07 (35 days → event) from
08 DOC-06, plus 2 more > 30 days late and 1 on time. PII is fake (DEC-136); level-4 columns
are pgcrypto-encrypted by the column type (DEC-207).
"""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import Department, Employee, HiringPlan, SalaryHistory, Team
from app.modules.hr.services.hr_service import normalize_name
from app.seed.ids import seed_uuid

SEED: dict[str, Any] = {"source": "SEED"}
DEPARTMENTS = (("BOD", "Ban Giám đốc"), ("FIN", "Tài chính – Kế toán"), ("SAL", "Kinh doanh"),
               ("SVC", "Kỹ thuật & Dịch vụ"), ("PRD", "Sản phẩm & Công nghệ"))  # fmt: skip
TEAMS = (("SAL", "SAL-HCM", "Sales TP.HCM"), ("SAL", "SAL-HN", "Sales Hà Nội"),
         ("PRD", "PRD-BE", "Backend ABC Order"))  # fmt: skip
# code, name, dept, team, status, hire, termination, monthly salary (triệu)
EMPLOYEES: tuple[tuple[str, str, str, str | None, str, date, date | None, int], ...] = (
    ("NV-0001", "Nguyễn Văn An", "BOD", None, "active", date(2015, 3, 1), None, 85),
    ("NV-0002", "Trần Thị Minh", "FIN", None, "active", date(2016, 5, 3), None, 60),
    ("NV-0003", "Lê Hoàng Giang", "SAL", "SAL-HCM", "active", date(2017, 1, 9), None, 62),
    ("NV-0004", "Đỗ Quang Huy", "PRD", "PRD-BE", "active", date(2019, 8, 1), None, 58),
    ("NV-0005", "Đặng Văn Khải", "SVC", None, "active", date(2018, 2, 12), None, 40),
    ("NV-0101", "Phan Thị Thu", "SAL", "SAL-HN", "probation", date(2026, 8, 18), None, 16),
    ("NV-0102", "Võ Minh Khang", "PRD", "PRD-BE", "probation", date(2026, 9, 7), None, 30),
    ("NV-0103", "Lý Thị Hồng", "SVC", None, "probation", date(2026, 9, 21), None, 15),
    ("NV-0201", "Trương Văn Bình", "SAL", "SAL-HCM", "terminated", date(2022, 4, 4),
     date(2026, 8, 29), 21),
    ("NV-0202", "Mai Thị Ngọc", "SVC", None, "terminated", date(2021, 6, 14),
     date(2026, 10, 10), 17),
)  # fmt: skip
SALARY_MONTHS = (date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1))
# code, dept, title/position, headcount, filled, status, start, target fill date
PLANS = (
    ("HP-2026-05", "PRD", "Backend developer", 2, 0, "approved", date(2026, 9, 1),
     date(2026, 10, 31)),
    ("HP-2026-06", "SVC", "Kỹ thuật viên", 3, 1, "in_progress", date(2026, 7, 1),
     date(2026, 9, 30)),
    ("HP-2026-07", "SAL", "Sales Hà Nội", 6, 2, "in_progress", date(2026, 6, 15),
     date(2026, 9, 15)),
    ("HP-2026-03", "FIN", "Kế toán tổng hợp", 1, 0, "in_progress", date(2026, 5, 4),
     date(2026, 8, 31)),
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
        Department(id=seed_uuid("department", code), code=code, name=name, aliases=[], **SEED)
        for code, name in DEPARTMENTS
    ])  # fmt: skip
    await db.flush()
    db.add_all([
        Team(id=seed_uuid("team", code), department_id=seed_uuid("department", dept), code=code,
             name=name, **SEED)
        for dept, code, name in TEAMS
    ])  # fmt: skip
    return len(DEPARTMENTS) + len(TEAMS)


async def seed_employees(db: AsyncSession) -> int:
    if await _has(db, Employee):
        return 0
    rows = []
    for n, (code, name, dept, team, status, hired, left, _) in enumerate(EMPLOYEES, start=1):
        rows.append(Employee(
            id=emp_id(code), employee_code=code, full_name=name,
            normalized_name=normalize_name(name), department_id=seed_uuid("department", dept),
            team_id=seed_uuid("team", team) if team else None, status=status, hire_date=hired,
            termination_date=left,
            contract_type="probation" if status == "probation" else "permanent",
            **_fake_pii(n), **SEED,
        ))  # fmt: skip
    db.add_all(rows)
    await db.flush()
    salaries = [
        SalaryHistory(employee_id=emp_id(code), base_salary=mil * 1_000_000, currency="VND",
                      effective_date=month, reason="Dữ liệu seed lịch sử")
        for code, *_, hired, left, mil in EMPLOYEES
        for month in SALARY_MONTHS
        if (left is None or left >= month)
    ]  # fmt: skip
    db.add_all(salaries)
    return len(rows) + len(salaries)


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

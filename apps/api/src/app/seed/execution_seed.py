"""Execution seed (T-236, DEC-208) — reduced 08 §10: 1 company objective, 4 initiatives,
3 projects, 18 tasks for 5 assignees (seeded employees' user-less ids — workload is per id).

October window (due 1–20/10): 10 tasks, 7 done on time → OPS-01 70% (warning); 4 from
meetings, 2 done → OPS-03 50% (warning); 1 of 3 running projects behind plan → OPS-02 33%
(warning); 1 of 5 assignees > 110% two weeks running → HR-03 20% (warning); 2 of 4
initiatives on track → RSK-06 50% (warning). `created_at` is set explicitly so workload
windows are deterministic. Idempotent (`source='SEED'`).
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.models import Initiative, Objective, Project, Task
from app.seed.hr_seed import emp_id
from app.seed.ids import seed_uuid

SEED: dict[str, Any] = {"source": "SEED"}
CREATED = datetime(2026, 9, 25, 2, tzinfo=UTC)
PEOPLE = ("NV-0002", "NV-0003", "NV-0004", "NV-0005", "NV-0101")
# code, name, dept, start, planned end, tasks done / total (progress vs plan)
PROJECTS = (
    ("PRJ-ERP", "Triển khai ERP kho", "FIN", date(2026, 7, 1), date(2026, 11, 30), 1, 6),
    ("PRJ-HN", "Mở rộng chi nhánh Hà Nội", "SAL", date(2026, 9, 1), date(2027, 3, 31), 1, 4),
    ("PRJ-ORD4", "ABC Order 4.0", "PRD", date(2026, 10, 1), date(2027, 6, 30), 0, 2),
)
# code, title, pillar, dept, start, end, progress %, weight %
INITIATIVES = (
    ("INI-01", "Tăng trưởng doanh thu 15%", "C", "SAL", date(2026, 1, 1), date(2026, 12, 31),
     82, 30),
    ("INI-02", "Giảm DSO xuống 45 ngày", "F", "FIN", date(2026, 4, 1), date(2026, 12, 31), 40,
     25),
    ("INI-03", "Ra mắt ABC Insight", "U", "PRD", date(2026, 6, 1), date(2027, 3, 31), 18, 25),
    ("INI-04", "Chuẩn hóa quy trình bảo trì", "O", "SVC", date(2026, 7, 1), date(2026, 12, 31),
     55, 20),
)  # fmt: skip


def _tasks() -> list[dict[str, Any]]:
    """(person, due day in Oct, status, done day, meeting?, hours) — October window first."""
    rows: list[tuple[str, int, str, int | None, bool, int | None]] = [
        ("NV-0002", 3, "done", 2, False, 6), ("NV-0002", 8, "done", 8, True, 4),
        ("NV-0003", 6, "done", 5, False, 8), ("NV-0003", 10, "done", 9, True, 6),
        ("NV-0004", 13, "done", 12, False, 8), ("NV-0004", 15, "done", 15, False, 6),
        ("NV-0005", 17, "done", 16, False, 4), ("NV-0005", 9, "done", 14, False, 4),
        ("NV-0101", 14, "in_progress", None, True, 6), ("NV-0003", 18, "blocked", None, True, 8),
        # beyond the window: open load (NV-0004 overloaded: 46 h + 6 h over the last 2 weeks)
        ("NV-0004", 28, "in_progress", None, False, 24), ("NV-0004", 30, "todo", None, False, 22),
        ("NV-0002", 25, "todo", None, False, 8), ("NV-0101", 27, "todo", None, False, 6),
        ("NV-0005", 31, "todo", None, False, 6), ("NV-0003", 29, "todo", None, False, 8),
    ]  # fmt: skip
    out = []
    for n, (who, due, status, done, meeting, hours) in enumerate(rows, start=1):
        out.append({
            "key": f"T-{n:02d}", "who": who, "due": date(2026, 10, due), "status": status,
            "done": datetime(2026, 10, done, 9, tzinfo=UTC) if done else None,
            "meeting": meeting, "hours": hours,
        })  # fmt: skip
    return out


async def seed_execution(db: AsyncSession, owner: uuid.UUID | None) -> dict[str, int]:
    has = select(func.count()).select_from(Task).where(Task.source == "SEED")
    if owner is None or int((await db.execute(has)).scalar_one()):
        return {"execution": 0}
    obj = seed_uuid("objective", "OBJ-2026")
    db.add(Objective(id=obj, title="Tăng trưởng bền vững 2026", period_key="2026",
                     level="company", okr_type="committed", weight_pct=100, owner_id=owner,
                     status="active", progress_pct=55, **SEED))  # fmt: skip
    await db.flush()
    db.add_all([
        Initiative(id=seed_uuid("initiative", code), code=code, title=title, objective_id=obj,
                   pillar=pillar, owner_id=owner, department_id=seed_uuid("department", dept),
                   start_date=start, planned_end_date=end, status="active",
                   progress_pct=prog, weight_pct=w, currency="VND", **SEED)
        for code, title, pillar, dept, start, end, prog, w in INITIATIVES
    ])  # fmt: skip
    db.add_all([
        Project(id=seed_uuid("project", code), code=code, name=name, owner_id=owner,
                department_id=seed_uuid("department", dept), start_date=start,
                planned_end_date=end, status="active", currency="VND", **SEED)
        for code, name, dept, start, end, _, _ in PROJECTS
    ])  # fmt: skip
    await db.flush()
    tasks = [
        Task(id=seed_uuid("task", t["key"]), title=f"{t['key']} — việc seed", owner_id=owner,
             assignee_id=emp_id(t["who"]), department_id=None, priority="medium",
             status=t["status"], due_date=t["due"], done_at=t["done"],
             blocked_reason="Chờ phê duyệt ngân sách" if t["status"] == "blocked" else None,
             estimate_hours=t["hours"], is_critical=False,
             task_source="meeting" if t["meeting"] else "manual", created_at=CREATED, **SEED)
        for t in _tasks()
    ]  # fmt: skip
    for code, _, dept, *_, done, total in PROJECTS:
        for i in range(total):
            tasks.append(Task(
                id=seed_uuid("task", f"{code}-{i}"), title=f"{code} hạng mục {i + 1}",
                owner_id=owner, department_id=seed_uuid("department", dept),
                project_id=seed_uuid("project", code), priority="medium",
                status="done" if i < done else "todo", is_critical=False, task_source="manual",
                done_at=CREATED - timedelta(days=3) if i < done else None,
                created_at=CREATED - timedelta(days=30), **SEED,
            ))  # fmt: skip
    db.add_all(tasks)
    await db.flush()
    return {"execution": 1 + len(INITIATIVES) + len(PROJECTS) + len(tasks)}

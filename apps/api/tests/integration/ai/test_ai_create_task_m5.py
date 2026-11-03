"""TC-M5-02..04 — "AI Chat tạo task" as the CEO, the ACT path the chat really takes.

Root causes found on the live UI (M5 audit): the model passes the date the user typed
(`30/10/2026`) and `ACT-create_task` only parsed ISO → `ACTION_REJECTED`; the AI branch dropped
`assignee_code` (an "assigned" task came out unassigned) and ignored `project_code`. The AI now
resolves both codes (unknown → a clear `NOT_FOUND`, never a silent drop) and `"me"` maps to the
asker's own employee (R-DEC-41). Runs on the seeded DB inside the rolled-back `db_session`.
"""

import uuid
from datetime import date
from typing import Any

import pytest
from sqlalchemy import select

from app.core.deps import Principal
from app.core.errors import NotFoundError
from app.modules.ai.services.action_service import ActionRejectedError, ActionService
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.execution.models import Project, Task
from app.modules.hr.models import Employee
from app.modules.platform.models import AuditLog

pytestmark = pytest.mark.integration


async def _ceo(db: Any) -> Principal:
    emp = (
        await db.execute(select(Employee).order_by(Employee.employee_code).limit(1))
    ).scalar_one()
    perms = frozenset(ROLE_PERMISSIONS["CEO"])
    return Principal(user_id=uuid.uuid4(), role="CEO", permissions=perms, employee_id=emp.id)


async def _propose(db: Any, user: Principal, **input_data: Any) -> Any:
    return await ActionService(db).propose(
        user, action_name="ACT-create_task", tool_name="TOOL-create_task",
        input_data=input_data, idempotency_key=f"m5-{uuid.uuid4()}",
    )  # fmt: skip


async def _task(db: Any, out: Any) -> Task:
    tid = uuid.UUID(out.result_refs[0]["id"])
    return (await db.execute(select(Task).where(Task.id == tid))).scalar_one()


async def test_vn_date_and_assign_to_me(db_session: Any, ceiling_l3: None) -> None:
    """TC-M5-02 — "giao cho tôi, hạn 30/10/2026" creates a real task assigned to the asker."""
    ceo = await _ceo(db_session)
    out = await _propose(db_session, ceo, title="Chuẩn bị báo cáo doanh thu tháng 10",
                         due_date="30/10/2026", assignee_code="me", priority="high")  # fmt: skip

    assert out.status == "executed"
    t = await _task(db_session, out)
    assert (t.due_date, t.assignee_id, t.priority) == (date(2026, 10, 30), ceo.employee_id, "high")
    assert (t.task_source, t.source_ref["kind"]) == ("ai", "ai_action")
    actions = set((await db_session.execute(
        select(AuditLog.action).where(AuditLog.target_id.in_([t.id, out.id]))
    )).scalars())  # fmt: skip
    assert "execution.task_create" in actions


async def test_real_codes_are_resolved(db_session: Any, ceiling_l3: None) -> None:
    """TC-M5-03 — an employee code and a project code become the task's assignee / project."""
    ceo = await _ceo(db_session)
    emp = (await db_session.execute(
        select(Employee).order_by(Employee.employee_code.desc()).limit(1)
    )).scalar_one()  # fmt: skip
    project = (await db_session.execute(select(Project).limit(1))).scalar_one_or_none()
    args: dict[str, Any] = {"title": "Rà soát hợp đồng", "assignee_code": emp.employee_code}
    if project is not None:
        args["project_code"] = project.code
    out = await _propose(db_session, ceo, **args)

    t = await _task(db_session, out)
    assert t.assignee_id == emp.id
    if project is not None:
        assert t.project_id == project.id


@pytest.mark.parametrize(
    ("field", "value"),
    [("assignee_code", "your_code"), ("project_code", "sales_report"), ("due_date", "tomorrow")],
)
async def test_invented_values_are_refused_not_dropped(
    db_session: Any, ceiling_l3: None, field: str, value: str
) -> None:
    """TC-M5-04 — what the model invented on the live UI is refused with the field named."""
    ceo = await _ceo(db_session)
    before = (await db_session.execute(select(Task.id))).scalars().all()
    with pytest.raises((NotFoundError, ActionRejectedError)) as err:
        await _propose(db_session, ceo, title="x", **{field: value})
    details = err.value.details or {}
    assert details.get("field") == field or any(
        e.get("field") == field for e in details.get("errors", [])
    )
    assert (await db_session.execute(select(Task.id))).scalars().all() == before

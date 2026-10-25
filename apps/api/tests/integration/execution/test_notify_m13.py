"""TC-M13-09 (T-623, R-DEC-46) — notifications written in the same tx as the mutation.

Uses the demo users of the dev DB (`app.seed`): `manager@` (MGR SVC), `employee@` (EMP SVC,
Ngô Thị Lan); everything happens inside the rolled-back test transaction.
"""

import uuid
from datetime import date
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.execution.services.task_service import detect_overdue_tasks
from app.modules.platform.models import Notification
from tests.conftest import ApiClient
from tests.integration.execution.helpers import as_user, patch

pytestmark = pytest.mark.integration


async def _user(db: AsyncSession, email: str) -> User:
    return (await db.execute(select(User).where(User.email == email))).scalar_one()


async def _notes(db: AsyncSession, ref_id: str) -> list[tuple[uuid.UUID, str, str, str | None]]:
    rows = await db.execute(
        select(Notification.recipient_id, Notification.kind, Notification.email_status,
               Notification.link).where(Notification.ref_id == uuid.UUID(ref_id))
    )  # fmt: skip
    return [tuple(r) for r in rows.all()]  # type: ignore[misc]


async def _mgr_creates(api: ApiClient, mgr: User, **body: Any) -> dict[str, Any]:
    r = await as_user(api, "POST", "/work/tasks", "MGR", mgr.id, department_id=mgr.department_id,
                      employee_id=mgr.employee_id,
                      json={"title": "Gọi lại khách", "department_id": str(mgr.department_id),
                            **body})  # fmt: skip
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


async def test_task_assigned_reminder_and_done(api: ApiClient, db_session: AsyncSession) -> None:
    mgr = await _user(db_session, "manager@abc.demo")
    emp = await _user(db_session, "employee@abc.demo")
    t = await _mgr_creates(api, mgr, assignee_id=str(emp.employee_id), owner_id=str(mgr.id),
                           due_date="2037-03-01")  # fmt: skip
    notes = await _notes(db_session, t["id"])
    assert notes == [(emp.id, "task_assigned", "PENDING", f"/work?task={t['id']}")]

    # self-assign → nothing; employee without an account → skipped, no error
    own = await _mgr_creates(api, mgr, assignee_id=str(mgr.employee_id))
    assert await _notes(db_session, own["id"]) == []
    ghost = await _mgr_creates(api, mgr, assignee_id=str(uuid.uuid4()))
    assert await _notes(db_session, ghost["id"]) == []
    moved = await as_user(api, "PATCH", f"/work/tasks/{ghost['id']}", "MGR", mgr.id,
                          department_id=mgr.department_id, employee_id=mgr.employee_id,
                          json={"assignee_id": str(emp.employee_id), "version": 1})  # fmt: skip
    assert moved.status_code == 200
    assert [n[1] for n in await _notes(db_session, ghost["id"])] == ["task_assigned"]

    # overdue job → `reminder` to assignee + owner, once (email off by default)
    await detect_overdue_tasks(db_session, date(2037, 3, 5))
    await detect_overdue_tasks(db_session, date(2037, 3, 5))
    rem = [n for n in await _notes(db_session, t["id"]) if n[1] == "reminder"]
    assert sorted(n[0] for n in rem) == sorted([emp.id, mgr.id])
    assert {n[2] for n in rem} == {"NOT_REQUIRED"}

    # employee completes → owner gets `system`
    done = await as_user(api, "PATCH", f"/work/tasks/{t['id']}", "EMP", emp.id,
                         department_id=emp.department_id, employee_id=emp.employee_id,
                         json={"status": "done", "version": t["version"]})  # fmt: skip
    assert done.status_code == 200, done.text
    assert [n[0] for n in await _notes(db_session, t["id"]) if n[1] == "system"] == [mgr.id]


async def test_approval_notifications(api: ApiClient, db_session: AsyncSession) -> None:
    mgr = await _user(db_session, "manager@abc.demo")
    emp = await _user(db_session, "employee@abc.demo")
    t = await _mgr_creates(api, mgr, assignee_id=str(emp.employee_id))
    r = await as_user(api, "POST", f"/work/tasks/{t['id']}/reassign-requests", "EMP", emp.id,
                      department_id=emp.department_id, employee_id=emp.employee_id,
                      json={"to_assignee_id": str(mgr.employee_id),
                            "reason": "nghỉ phép"})  # fmt: skip
    assert r.status_code == 201, r.text
    rid = r.json()["data"]["id"]
    asked = await _notes(db_session, rid)
    mgrs = {n[0] for n in asked}
    assert mgr.id in mgrs and emp.id not in mgrs
    assert {n[1] for n in asked} == {"approval_requested"}
    assert {n[3] for n in asked} == {f"/work/approvals?id={rid}"}
    ok = await as_user(api, "POST", f"/workflow/approval-requests/{rid}/decide", "MGR", mgr.id,
                       department_id=mgr.department_id, json={"decision": "approve"})  # fmt: skip
    assert ok.status_code == 200, ok.text
    decided = [n for n in await _notes(db_session, rid) if n[1] == "approval_decided"]
    assert [(n[0], n[2]) for n in decided] == [(emp.id, "NOT_REQUIRED")]
    # the reassignment itself notifies the new assignee (the approver is the actor)
    after = {(n[0], n[1]) for n in await _notes(db_session, t["id"])}
    assert (mgr.id, "task_assigned") not in after


async def test_patch_same_assignee_no_notification(
    api: ApiClient, db_session: AsyncSession
) -> None:
    mgr = await _user(db_session, "manager@abc.demo")
    emp = await _user(db_session, "employee@abc.demo")
    t = await _mgr_creates(api, mgr, assignee_id=str(emp.employee_id))
    await patch(api, f"/work/tasks/{t['id']}", 1, title="khác")
    assert len(await _notes(db_session, t["id"])) == 1

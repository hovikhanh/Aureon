"""T-645 — 10 new `TOOL-*` of M1.6 (10 §7.2.5, R-DEC-70).

TC-M16-03: the 4 READ tools run through `ToolExecutor` as the asker (CEO all, MGR own department,
EMP own work; missing permission → `forbidden`); results cite `SourceRef`s and carry no level-3/4
fields (no names, e-mails, salary).
TC-M16-04: the 6 WRITE tools → `ActionService.propose` with the tool's `action_name`; confirm runs
the M1.5 ACT in the transaction (row + audit + outbox); undo within 24h reverses (`update_task`
restores the snapshot, a later human edit → `409`); missing `<domain>:write` / `hr:admin` → `403`;
`create_department` under a parent of another organization → `422`.
"""

import json
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.core.audit import AUDIT_LOGS
from app.core.deps import Principal
from app.core.errors import (
    BusinessRuleError,
    ConflictStateError,
    PermissionDeniedError,
)
from app.core.events.envelope import OUTBOX
from app.modules.ai.services.action_service import ActionService
from app.modules.ai.services.tool_executor import ToolExecutor
from app.modules.ai.tools import get_tool
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.execution.models import Task
from app.modules.execution.schemas.tasks import TaskCreate, TaskUpdate
from app.modules.execution.services.base import today as biz_today
from app.modules.execution.services.task_service import TaskService

pytestmark = pytest.mark.integration

READ_TOOLS = (
    "TOOL-get_org_tree",
    "TOOL-get_okr_status",
    "TOOL-get_overdue_tasks",
    "TOOL-get_project_status",
)
WRITE_TOOLS = {
    "TOOL-update_task": "ACT-update_task",
    "TOOL-assign_task": "ACT-assign_task",
    "TOOL-record_kr_checkin": "ACT-record_kr_checkin",
    "TOOL-upsert_kpi": "ACT-upsert_kpi",
    "TOOL-upsert_objective": "ACT-upsert_objective",
    "TOOL-create_department": "ACT-create_department",
    "TOOL-create_team": "ACT-create_team",
}
FORBIDDEN_KEYS = {
    "full_name",
    "email",
    "phone",
    "salary",
    "national_id",
    "bank_account",
    "date_of_birth",
    "address",
}


def who(role: str, **kw: object) -> Principal:
    return Principal(
        user_id=kw.pop("user_id", None) or uuid.uuid4(),
        role=role,  # type: ignore[arg-type]
        permissions=frozenset(ROLE_PERMISSIONS[role]),
        **kw,
    )  # type: ignore[arg-type]


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


async def _a_department(db) -> uuid.UUID:
    from app.modules.hr.services.hr_service import HrService

    dept = await HrService(db).department_id_by_code("SAL")
    assert dept is not None
    return dept


# ---------------------------------------------------------------- TC-M16-03 READ
def test_registry_maps_new_tools() -> None:
    for name in READ_TOOLS:
        t = get_tool(name)
        assert t is not None and t.kind == "READ" and t.autonomy_max == "L0"
    for name, act in WRITE_TOOLS.items():
        t = get_tool(name)
        assert t is not None and t.kind == "WRITE" and t.action_name == act, name
        assert "ai:write" in t.required_permissions
    assert get_tool("TOOL-create_department").required_permissions == ("ai:write", "hr:admin")  # type: ignore[union-attr]


@pytest.mark.parametrize("tool", READ_TOOLS)
async def test_read_tools_ceo_ok_with_sources_no_pii(db_session, tool: str) -> None:
    res = await ToolExecutor(db_session, who("CEO")).run(tool, {})
    assert res.status == "ok", res.error_code
    assert not (_keys(res.data) & FORBIDDEN_KEYS)
    json.dumps(res.data)  # model summary must be serialisable
    assert all(s.type == "record" and s.id for s in res.sources)


async def test_org_tree_scoped_by_role(db_session) -> None:
    ceo = await ToolExecutor(db_session, who("CEO")).run("TOOL-get_org_tree", {})
    assert ceo.status == "ok" and len(ceo.data["departments"]) >= 2
    dept = await _a_department(db_session)
    mgr = await ToolExecutor(db_session, who("MGR", department_id=dept)).run(
        "TOOL-get_org_tree", {}
    )
    assert mgr.status == "ok"
    assert {s.id for s in mgr.sources} <= {s.id for s in ceo.sources}
    assert str(dept) in {s.id for s in mgr.sources}
    assert len(mgr.sources) < len(ceo.sources)
    emp = await ToolExecutor(db_session, who("EMP")).run("TOOL-get_org_tree", {})
    assert emp.status == "forbidden"  # EMP has hr:read ◑o but no structure scope


async def test_overdue_tasks_scoped(db_session) -> None:
    dept = await _a_department(db_session)
    ceo = who("CEO")
    svc = TaskService(db_session)
    past = biz_today() - timedelta(days=5)
    mine_emp = uuid.uuid4()
    in_dept = await svc.create(ceo, TaskCreate(title="Trễ SAL", due_date=past, department_id=dept))
    own = await svc.create(
        ceo, TaskCreate(title="Trễ của EMP", due_date=past, assignee_id=mine_emp)
    )
    all_ = await ToolExecutor(db_session, ceo).run("TOOL-get_overdue_tasks", {"limit": 50})
    ids = {s.id for s in all_.sources}
    assert all_.data["overdue_total"] >= 2
    mgr = await ToolExecutor(db_session, who("MGR", department_id=dept)).run(
        "TOOL-get_overdue_tasks", {"limit": 50}
    )
    assert str(in_dept.id) in {s.id for s in mgr.sources}
    assert str(own.id) not in {s.id for s in mgr.sources}
    emp = await ToolExecutor(db_session, who("EMP", employee_id=mine_emp)).run(
        "TOOL-get_overdue_tasks", {"limit": 50}
    )
    assert {s.id for s in emp.sources} == {str(own.id)}
    assert str(in_dept.id) in ids or all_.data["overdue_total"] > 50


async def test_okr_and_project_status_scoped(db_session) -> None:
    ceo = await ToolExecutor(db_session, who("CEO")).run("TOOL-get_okr_status", {"limit": 50})
    emp = await ToolExecutor(db_session, who("EMP")).run("TOOL-get_okr_status", {"limit": 50})
    assert ceo.status == emp.status == "ok"
    assert ceo.data["total"] >= 1
    assert {s.id for s in emp.sources} <= {s.id for s in ceo.sources}
    assert emp.data["total"] < ceo.data["total"]
    projects = await ToolExecutor(db_session, who("CEO")).run("TOOL-get_project_status", {})
    assert projects.status == "ok" and projects.data["total"] >= 1
    one = projects.sources[0].id
    detail = await ToolExecutor(db_session, who("CEO")).run(
        "TOOL-get_project_status", {"project_id": one}
    )
    assert detail.data["total"] == 1 and detail.sources[0].id == one
    gone = await ToolExecutor(db_session, who("CEO")).run(
        "TOOL-get_project_status", {"project_id": str(uuid.uuid4())}
    )
    assert (gone.status, gone.error_code) == ("error", "AI_NO_DATA_AVAILABLE")


async def test_read_tool_without_permission_is_forbidden(db_session) -> None:
    rev = who("REV")  # no execution:read
    for tool in ("TOOL-get_okr_status", "TOOL-get_overdue_tasks", "TOOL-get_project_status"):
        res = await ToolExecutor(db_session, rev).run(tool, {})
        assert (res.status, res.error_code) == ("forbidden", "FORBIDDEN_ROLE")


async def test_write_tool_not_run_by_executor(db_session) -> None:
    res = await ToolExecutor(db_session, who("CEO")).run("TOOL-update_task", {})
    assert res.error_code == "AI_WRITE_VIA_ACTION"


# ---------------------------------------------------------------- TC-M16-04 WRITE
async def _propose(db, user: Principal, tool: str, data: dict, key: str | None = None):
    t = get_tool(tool)
    assert t is not None and t.action_name
    return await ActionService(db).propose(
        user,
        action_name=t.action_name,
        tool_name=tool,
        input_data=data,
        idempotency_key=key or f"t645-{uuid.uuid4()}",
    )


async def _audits(db, target_id: uuid.UUID) -> list[str]:
    rows = await db.execute(select(AUDIT_LOGS.c.action).where(AUDIT_LOGS.c.target_id == target_id))
    return [r[0] for r in rows]


async def _events(db, aggregate_id: uuid.UUID) -> list[str]:
    rows = await db.execute(
        select(OUTBOX.c.event_type).where(OUTBOX.c.aggregate_id == aggregate_id)
    )
    return [r[0] for r in rows]


async def test_update_task_confirm_then_undo_restores_snapshot(db_session) -> None:
    ceo = who("CEO")
    task = await TaskService(db_session).create(ceo, TaskCreate(title="Gốc", priority="low"))
    card = await _propose(
        db_session,
        ceo,
        "TOOL-update_task",
        {"task_id": str(task.id), "title": "AI sửa", "priority": "high"},
    )
    assert (card.status, card.autonomy_level, card.action_name) == (
        "proposed",
        "L2",
        "ACT-update_task",
    )
    done = await ActionService(db_session).confirm(ceo, card.id)
    assert done.status == "executed" and done.can_undo
    assert all("_undo" not in r for r in done.result_refs)  # undo state never exposed
    row = (await db_session.execute(select(Task).where(Task.id == task.id))).scalar_one()
    assert (row.title, row.priority) == ("AI sửa", "high")
    assert "execution.task_update" in await _audits(db_session, task.id)
    assert await _events(db_session, task.id)
    undone = await ActionService(db_session).undo(ceo, card.id, reason="sai")
    assert undone.status == "undone"
    await db_session.refresh(row)
    assert (row.title, row.priority) == ("Gốc", "low")


async def test_update_task_undo_conflicts_after_human_edit(db_session) -> None:
    ceo = who("CEO")
    svc = TaskService(db_session)
    task = await svc.create(ceo, TaskCreate(title="Gốc 2"))
    card = await _propose(
        db_session, ceo, "TOOL-update_task", {"task_id": str(task.id), "title": "AI sửa 2"}
    )
    await ActionService(db_session).confirm(ceo, card.id)
    cur = await svc.out(await svc.get(ceo, task.id))
    await svc.update(ceo, task.id, TaskUpdate(title="Người sửa", version=cur.version), cur.version)
    with pytest.raises(ConflictStateError):
        await ActionService(db_session).undo(ceo, card.id, reason="x")


async def test_assign_task_sets_assignee_and_undo_clears(db_session) -> None:
    from app.modules.hr.services.hr_service import HrService

    ceo = who("CEO")
    code = "NV-0001"
    emp_id = await HrService(db_session).employee_id_by_code(code)
    assert emp_id is not None
    task = await TaskService(db_session).create(ceo, TaskCreate(title="Giao việc"))
    card = await _propose(
        db_session, ceo, "TOOL-assign_task", {"task_id": str(task.id), "assignee_code": code}
    )
    assert card.action_name == "ACT-assign_task"
    await ActionService(db_session).confirm(ceo, card.id)
    row = (await db_session.execute(select(Task).where(Task.id == task.id))).scalar_one()
    assert row.assignee_id == emp_id
    await ActionService(db_session).undo(ceo, card.id)
    await db_session.refresh(row)
    assert row.assignee_id is None


async def test_upsert_kpi_and_objective_confirm_undo(db_session) -> None:
    ceo = who("CEO")
    code = f"KPI-T645-{uuid.uuid4().hex[:6]}"
    kpi = await _propose(
        db_session,
        ceo,
        "TOOL-upsert_kpi",
        {"code": code, "name": "KPI AI", "unit": "%", "target": 90, "owner_code": "NV-0001"},
    )
    out = await ActionService(db_session).confirm(ceo, kpi.id)
    assert out.result_refs[0]["table"] == "execution.kpis"
    obj = await _propose(
        db_session,
        ceo,
        "TOOL-upsert_objective",
        {"title": f"OKR AI {code}", "period_key": "2026-Q4", "owner_code": "NV-0001"},
    )
    o = await ActionService(db_session).confirm(ceo, obj.id)
    assert o.result_refs[0]["table"] == "execution.objectives"
    assert (await ActionService(db_session).undo(ceo, o.id)).status == "undone"
    assert (await ActionService(db_session).undo(ceo, out.id)).status == "undone"


async def test_record_kr_checkin_confirm_undo(db_session) -> None:
    from app.modules.execution.models import KeyResult

    kr = (await db_session.execute(select(KeyResult.id).limit(1))).scalar_one()
    ceo = who("CEO")
    card = await _propose(
        db_session,
        ceo,
        "TOOL-record_kr_checkin",
        {"kr_ref": str(kr), "value": 10, "confidence": "MEDIUM"},
    )
    out = await ActionService(db_session).confirm(ceo, card.id)
    assert out.result_refs[0]["table"] == "execution.check_ins"
    assert (await ActionService(db_session).undo(ceo, card.id)).status == "undone"


async def test_structure_tools_need_hr_admin_and_undo(db_session) -> None:
    ceo = who("CEO")
    code = f"D{uuid.uuid4().hex[:6].upper()}"
    card = await _propose(
        db_session, ceo, "TOOL-create_department", {"code": code, "name": "Phòng AI"}
    )
    mgr = who("MGR", user_id=ceo.user_id)  # same person, no hr:admin
    with pytest.raises(PermissionDeniedError):
        await ActionService(db_session).confirm(mgr, card.id)
    out = await ActionService(db_session).confirm(ceo, card.id)
    dept_id = uuid.UUID(out.result_refs[0]["id"])
    assert "hr.department_create" in await _audits(db_session, dept_id)
    team = await _propose(
        db_session,
        ceo,
        "TOOL-create_team",
        {"code": "T1", "name": "Tổ AI", "department_code": code},
    )
    t = await ActionService(db_session).confirm(ceo, team.id)
    assert t.result_refs[0]["table"] == "hr.teams"
    assert (await ActionService(db_session).undo(ceo, team.id)).status == "undone"
    assert (await ActionService(db_session).undo(ceo, card.id)).status == "undone"


async def test_existing_department_is_reused_and_never_undone(db_session) -> None:
    from app.modules.hr.services.hr_service import HrService

    ceo = who("CEO")
    card = await _propose(
        db_session, ceo, "TOOL-create_department", {"code": "SAL", "name": "Kinh doanh"}
    )
    out = await ActionService(db_session).confirm(ceo, card.id)
    assert out.result_refs[0].get("reused") is True
    await ActionService(db_session).undo(ceo, card.id)
    assert await HrService(db_session).department_id_by_code("SAL") is not None


async def test_write_without_domain_write_is_403(db_session) -> None:
    ceo = who("CEO")
    task = await TaskService(db_session).create(ceo, TaskCreate(title="REV không sửa"))
    rev = who("REV", user_id=ceo.user_id)  # ai:write but no execution:write
    card = await _propose(
        db_session, ceo, "TOOL-update_task", {"task_id": str(task.id), "title": "x"}
    )
    with pytest.raises(PermissionDeniedError):
        await ActionService(db_session).confirm(rev, card.id)


async def test_create_department_parent_in_other_organization_is_422(db_session) -> None:
    from app.modules.hr.schemas import DepartmentCreate
    from app.modules.hr.schemas.org import OrganizationCreate
    from app.modules.hr.services.hr_service import HrService
    from app.modules.hr.services.structure_service import StructureService

    ceo = who("CEO")
    other = await StructureService(db_session).create_org(
        ceo,
        OrganizationCreate(
            code=f"ORG{uuid.uuid4().hex[:5]}", name="Công ty khác", valid_from=date(2030, 1, 1)
        ),
    )
    pcode = f"P{uuid.uuid4().hex[:6].upper()}"
    await HrService(db_session).create_department(
        ceo,
        DepartmentCreate(
            name="Phòng ngoài", code=pcode, organization_id=other.id, valid_from=date(2030, 1, 1)
        ),
    )
    card = await _propose(
        db_session,
        ceo,
        "TOOL-create_department",
        {"code": f"C{uuid.uuid4().hex[:6].upper()}", "name": "Con", "parent_code": pcode},
    )
    with pytest.raises(BusinessRuleError) as exc:
        await ActionService(db_session).confirm(ceo, card.id)
    assert exc.value.status_code == 422

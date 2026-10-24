"""TC-M15-07 — Action Registry v2 (10 §7.2.4, R-DEC-60/61/63): validate-all before write, reuse
keys, all-or-nothing on a failing ACT, permission any-of, unknown ACT rejected, level-4 drop."""

import uuid
from typing import Any

import pytest
from sqlalchemy import func, select

from app.core.deps import Principal
from app.core.errors import ActionRejectedError
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.idp.services.actions import ActionContext, action_names, get_action
from app.modules.idp.services.actions.executor import (
    Step,
    build_plan,
    missing_permissions,
    run_all,
)

pytestmark = pytest.mark.integration


def _user(role: str = "DIR", pillars: tuple[str, ...] = ("O",)) -> Principal:
    return Principal(
        user_id=uuid.uuid4(), role=role, permissions=frozenset(ROLE_PERMISSIONS[role]),
        scope_pillars=pillars,
    )  # fmt: skip


def _code(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"


def _step(act_name: str, row: int | None, /, **params: Any) -> Step:
    act = get_action(act_name)
    assert act is not None
    return Step(act, row, params)


def _emp(code: str, dept: str, **kw: Any) -> Step:
    return _step("ACT-create_employee", kw.pop("row", 0), employee_code=code,
                 full_name="Nguyễn Văn Thử", department_code=dept, hire_date="2026-01-05",
                 **kw)  # fmt: skip


async def _count(db: Any, sql_table: str) -> int:
    from sqlalchemy import table

    schema, name = sql_table.split(".")
    return int((await db.execute(select(func.count()).select_from(table(name, schema=schema))))
               .scalar_one())  # fmt: skip


async def test_registry_has_the_twelve_acts() -> None:
    assert len(action_names()) == 12
    assert get_action("ACT-create_employee").required_permission == ("hr:write", "hr:admin")  # type: ignore[union-attr]
    assert get_action("ACT-create_invoice").is_finance  # type: ignore[union-attr]


async def test_unknown_action_is_rejected() -> None:
    with pytest.raises(ActionRejectedError) as exc:
        build_plan(["ACT-nope"], [], [])
    assert exc.value.details["reason"] == "unregistered"


async def test_plan_groups_rows_and_targets() -> None:
    fields = [
        {"name": "dept_code", "group": "row", "target": {"action": "ACT-create_department",
                                                          "param": "code"}},
        {"name": "dept_name", "group": "row", "target": {"action": "ACT-create_department",
                                                          "param": "name"}},
    ]  # fmt: skip
    values = [("dept_code", 1, "B"), ("dept_name", 1, "Bee"), ("dept_code", 0, "A"),
              ("dept_name", 0, "Ay"), ("dept_name", 2, None)]  # fmt: skip
    steps = build_plan(["ACT-create_department"], fields, values)
    assert [(s.row_index, s.params) for s in steps] == [
        (0, {"code": "A", "name": "Ay"}), (1, {"code": "B", "name": "Bee"})
    ]  # fmt: skip


async def test_permission_any_of() -> None:
    steps = [_emp("E1", "D1")]
    assert missing_permissions(_user("ADM", ()), steps) == []  # hr:admin satisfies any-of
    assert missing_permissions(_user("REV", ()), steps) == ["hr:write"]
    inv = [_step("ACT-create_invoice", None, subtotal=1)]
    assert missing_permissions(_user("REV", ()), inv) == ["finance:write"]


async def test_org_chain_reuses_department_and_sets_manager(db_session) -> None:
    from app.modules.hr.services.hr_service import HrService

    dept, boss, staff = _code("D"), _code("E"), _code("E")
    user, ctx = _user(), ActionContext(source="IMPORT")
    steps = [
        _step("ACT-create_department", 0, code=dept, name="Phòng thử ACT"),
        _step("ACT-create_department", 1, code=dept, name="Phòng thử ACT"),  # same code → reuse
        _step("ACT-create_team", 0, code="T1", name="Tổ 1", department_code=dept),
        _step("ACT-create_position", 0, title="Kế toán viên", department_code=dept),
        _emp(staff, dept, row=0, manager_code=boss),  # manager defined later in the file
        _emp(boss, dept, row=1),
    ]
    done = await run_all(db_session, user, steps, ctx)
    refs = [o.result_refs[0] for _, o in done]
    assert refs[0]["reused"] is False and refs[1]["reused"] is True
    assert refs[0]["id"] == refs[1]["id"]
    hr = HrService(db_session)
    staff_id = await hr.employee_id_by_code(staff)
    boss_id = await hr.employee_id_by_code(boss)
    emp = await hr.get_employee(user, staff_id)  # type: ignore[arg-type]
    assert emp.manager_id == boss_id


async def test_validate_errors_reject_before_any_write(db_session) -> None:
    dept = _code("D")
    before = await _count(db_session, "hr.departments")
    steps = [
        _step("ACT-create_department", 0, code=dept, name="Phòng X"),
        _emp(_code("E"), "NO-SUCH-DEPT", row=3),
    ]
    with pytest.raises(ActionRejectedError) as exc:
        await run_all(db_session, _user(), steps, ActionContext(source="IMPORT"))
    assert exc.value.details["action_name"] == "ACT-create_employee"
    assert exc.value.details["row_index"] == 3
    assert exc.value.details["errors"][0]["field"] == "department_code"
    assert await _count(db_session, "hr.departments") == before


async def test_failure_in_run_rolls_back_earlier_acts(db_session) -> None:
    """ACT N fails in `run` (duplicate invoice number) → ACT 1..N-1 rows, audit and outbox
    are all rolled back with it."""
    dept, number = _code("D"), _code("INV")
    tables = ("hr.departments", "finance.invoices", "platform.audit_logs",
              "platform.outbox_events")  # fmt: skip
    counts = [await _count(db_session, t) for t in tables]
    inv = {"invoice_number": number, "issue_date": "2026-10-01", "seller_name": "NCC A",
           "subtotal": "1.000.000", "vat_rate_pct": 10}  # fmt: skip
    steps = [
        _step("ACT-create_department", 0, code=dept, name="Phòng Y"),
        _step("ACT-create_invoice", 1, **inv),
        _step("ACT-create_invoice", 2, **inv),  # same number → DUPLICATE_RESOURCE in run
    ]
    with pytest.raises(ActionRejectedError) as exc:
        await run_all(db_session, _user("DIR", ()), steps, ActionContext(source="IDP"))
    assert exc.value.details["cause_code"] == "DUPLICATE_RESOURCE"
    assert exc.value.details["row_index"] == 2
    assert [await _count(db_session, t) for t in tables] == counts


async def test_level4_dropped_without_permission(db_session) -> None:
    dept, code = _code("D"), _code("E")
    ctx = ActionContext(source="IMPORT")
    adm = _user("ADM", ())  # hr:admin, no level-4 visibility
    steps = [_step("ACT-create_department", 0, code=dept, name="Phòng Z"),
             _emp(code, dept, salary=25_000_000, national_id="079090001234")]  # fmt: skip
    await run_all(db_session, adm, steps, ctx)
    assert "idp.warn.level4_dropped" in ctx.warnings


async def _goals_chain(db: Any, user: Principal) -> tuple[list[Any], dict[str, str]]:
    dept, owner, kpi = _code("D"), _code("E"), _code("K")
    obj = f"Tăng trưởng {kpi}"
    steps = [
        _step("ACT-create_department", 0, code=dept, name="Phòng KPI"),
        _emp(owner, dept),
        _step("ACT-upsert_objective", 0, title=obj, period_key="2026-Q4", owner_code=owner),
        _step("ACT-upsert_key_result", 0, objective_title=obj, period_key="2026-Q4",
              title="Doanh thu", unit="VND", baseline=0, target=100, owner_code=owner),
        _step("ACT-upsert_kpi", 0, code=kpi, name="Doanh thu tháng", unit="VND", target=100,
              owner_code=owner, department_code=dept),
        _step("ACT-upsert_kpi_target", 0, kpi_code=kpi, period_key="2026-11", target=120),
        _step("ACT-record_kpi_measurement", 0, kpi_code=kpi, period_key="2026-10",
              actual_value=90),
        _step("ACT-create_task", 0, title="Gọi khách hàng", assignee_code=owner, kpi_code=kpi),
    ]  # fmt: skip
    done = await run_all(db, user, steps, ActionContext(source="IDP"))
    return done, {"kpi": kpi, "obj": obj, "owner": owner}


async def test_goals_chain_runs_and_upserts(db_session) -> None:
    from app.modules.execution.services.kpi_service import KpiService

    user = _user("CEO", ())
    done, keys = await _goals_chain(db_session, user)
    assert [s.act.name for s, _ in done][-1] == "ACT-create_task"
    kpi_id = await KpiService(db_session).kpi_id_by_code(keys["kpi"])
    assert kpi_id is not None
    # second document: same KPI code → update with a snapshot of the old values
    again = [_step("ACT-upsert_kpi", 0, code=keys["kpi"], name="Doanh thu (sửa)", unit="VND",
                   target=150, owner_code=keys["owner"])]  # fmt: skip
    ((_, outcome),) = await run_all(db_session, user, again, ActionContext(source="IDP"))
    assert outcome.result_refs[0]["id"] == str(kpi_id)
    assert outcome.snapshot["name"] == "Doanh thu tháng"  # type: ignore[index]
    await again[0].act.undo(db_session, user, outcome)  # undo → back to the snapshot
    k = await KpiService(db_session).get_kpi(user, kpi_id)
    assert k.name == "Doanh thu tháng"


async def test_every_act_undo_reverts(db_session) -> None:
    user = _user("CEO", ())
    done, _ = await _goals_chain(db_session, user)
    for step, outcome in reversed(done):  # R-DEC-63: seq DESC
        await step.act.undo(db_session, user, outcome)
    from app.modules.execution.services.kpi_service import KpiService

    assert await KpiService(db_session).kpi_id_by_code(_["kpi"]) is None


@pytest.mark.parametrize(
    ("step", "field"),
    [
        (("ACT-create_department", {"code": "X", "name": "X", "parent_code": "NOPE"}),
         "parent_code"),
        (("ACT-create_team", {"code": "T", "name": "T", "department_code": "NOPE"}),
         "department_code"),
        (("ACT-create_position", {"title": "T", "department_code": "NOPE"}), "department_code"),
        (("ACT-upsert_objective", {"title": "O", "period_key": "2026", "owner_code": "NOPE",
                                   "parent_title": "NOPE"}), "owner_code"),
        (("ACT-upsert_key_result", {"objective_title": "NOPE", "period_key": "2026",
                                    "title": "K", "unit": "%", "baseline": 0, "target": 1,
                                    "owner_code": "NOPE"}), "owner_code"),
        (("ACT-upsert_kpi", {"code": "K", "name": "K", "unit": "%", "target": 1,
                             "owner_code": "NOPE", "department_code": "NOPE"}), "owner_code"),
        (("ACT-upsert_kpi_target", {"kpi_code": "NOPE", "period_key": "2026-10", "target": 1}),
         "kpi_code"),
        (("ACT-record_kpi_measurement", {"kpi_code": "NOPE", "period_key": "2026-10",
                                         "actual_value": 1}), "kpi_code"),
        (("ACT-create_task", {"title": "T", "assignee_code": "NOPE", "kpi_code": "NOPE"}),
         "assignee_code"),
        (("ACT-create_invoice", {"subtotal": "0"}), "subtotal"),
        (("ACT-upsert_kpi", {"code": "K"}), "name"),  # params_model error
    ],
)  # fmt: skip
async def test_validate_reports_row_errors(db_session, step, field) -> None:
    name, params = step
    with pytest.raises(ActionRejectedError) as exc:
        await run_all(db_session, _user("CEO", ()), [_step(name, 7, **params)], ActionContext())
    assert exc.value.details["row_index"] == 7
    assert field in {e.get("field") or e.get("loc", [None])[0] for e in
                     exc.value.details["errors"]}  # fmt: skip


async def test_org_reuse_undo_and_level4_for_ceo(db_session) -> None:
    from app.modules.hr.services.hr_service import HrService

    dept, code = _code("D"), _code("E")
    user, ctx = _user("CEO", ()), ActionContext(source="IMPORT")
    first = [_step("ACT-create_department", 0, code=dept, name="Phòng R"),
             _step("ACT-create_team", 0, code="T1", name="Tổ", department_code=dept),
             _step("ACT-create_position", 0, title="Kỹ sư", department_code=dept),
             _emp(code, dept, salary=30_000_000)]  # fmt: skip
    done = await run_all(db_session, user, first, ctx)
    assert ctx.warnings == []  # CEO sees level 4 → salary kept
    again = await run_all(db_session, user, first[1:3], ActionContext(source="IMPORT"))
    assert all(o.result_refs[0]["reused"] for _, o in again)
    for step, outcome in [*reversed(done), *again]:  # reused rows are left alone
        await step.act.undo(db_session, user, outcome)
    assert await HrService(db_session).employee_id_by_code(code) is None
    with pytest.raises(ActionRejectedError):  # duplicate inside one document
        await run_all(db_session, user, [_emp(code, dept), _emp(code, dept)], ActionContext())


async def test_objective_kr_upsert_and_checkin(db_session) -> None:
    user = _user("CEO", ())
    done, keys = await _goals_chain(db_session, user)
    obj, owner = keys["obj"], keys["owner"]
    kr_id = uuid.UUID(done[3][1].result_refs[0]["id"])
    steps = [
        _step("ACT-upsert_objective", 0, title=obj, period_key="2026-Q4", owner_code=owner,
              level="department"),
        _step("ACT-upsert_objective", 1, title="Con " + obj, period_key="2026-Q4",
              owner_code=owner, parent_title=obj),
        _step("ACT-upsert_key_result", 0, objective_title=obj, period_key="2026-Q4",
              title="Doanh thu", unit="VND", baseline=0, target=200, owner_code=owner),
    ]  # fmt: skip
    checkin = _step("ACT-record_kr_checkin", 0, kr_ref=str(kr_id), value=50, confidence="HIGH")
    with pytest.raises(ActionRejectedError) as exc:  # draft objective → service 409, all-or-nothing
        await run_all(db_session, user, [*steps, checkin], ActionContext(source="IDP"))
    assert exc.value.details["cause_code"] == "CONFLICT_STATE"
    again = await run_all(db_session, user, steps, ActionContext(source="IDP"))
    assert again[0][1].snapshot["level"] == "company"  # type: ignore[index]
    assert again[2][1].snapshot["created"] is False  # type: ignore[index]
    for step, outcome in reversed(again):
        await step.act.undo(db_session, user, outcome)


async def test_kr_checkin_on_active_objective(db_session) -> None:
    from app.modules.execution.schemas.okr import ObjectiveUpdate
    from app.modules.execution.services.okr_service import OkrService

    user = _user("CEO", ())
    done, keys = await _goals_chain(db_session, user)
    obj_id = uuid.UUID(done[2][1].result_refs[0]["id"])
    kr2 = _step("ACT-upsert_key_result", 0, objective_title=keys["obj"], period_key="2026-Q4",
                title="Biên lợi nhuận", unit="%", baseline=0, target=20,
                owner_code=keys["owner"])  # fmt: skip
    await run_all(db_session, user, [kr2], ActionContext(source="IDP"))  # active needs ≥ 2 KR
    svc = OkrService(db_session)
    o = await svc.get_objective(user, obj_id, "write")
    await svc.update_objective(user, obj_id, ObjectiveUpdate(status="active"), int(o.version))
    kr_id = done[3][1].result_refs[0]["id"]
    step = _step("ACT-record_kr_checkin", 0, kr_ref=kr_id, value=50, confidence="HIGH")
    ((_, outcome),) = await run_all(db_session, user, [step], ActionContext(source="IDP"))
    assert outcome.result_refs[0]["table"] == "check_ins"
    await step.act.undo(db_session, user, outcome)

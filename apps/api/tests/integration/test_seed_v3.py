"""TC-M11-06 / TC-M11-07 (T-603b, 08 §2.1 / §4 / §5, R-DEC-23) — seed v3 of company ABC.

The whole seed runs twice inside the rolled-back test transaction (idempotent), then the real
metric providers recompute at 20/10/2026 and the 08 §5 demo statuses are asserted.
"""

import uuid
from collections import Counter
from datetime import date
from typing import Any

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.execution.models import (
    Decision,
    KeyResult,
    Kpi,
    KpiMeasurement,
    Meeting,
    Objective,
    Project,
    Task,
)
from app.modules.hr.models import Department, Employee
from app.modules.platform.models import Metric, MetricValue
from app.modules.platform.services.metric_store import MetricStore, seed_catalog
from app.seed.auth_seed import AI_AGENT, DEMO_USERS, seed_auth
from app.seed.execution_seed import seed_execution
from app.seed.finance_seed import seed_finance
from app.seed.hr_seed import seed_hr
from app.seed.org_data import DEPARTMENTS
from app.seed.product_seed import seed_product
from app.seed.risk_seed import seed_risk
from app.seed.sales_seed import seed_sales
from app.workers.consumers import load_metric_providers
from tests.integration.test_seed import _cfg

pytestmark = pytest.mark.integration
AS_OF = date(2026, 10, 20)
# Empty the business schemas (as demo_reset.sh does) — keeps alembic_version + the roles
# catalog; inside the test transaction, so it is rolled back with it.
TRUNCATE_ALL = text("""DO $$ DECLARE t text; BEGIN
  SELECT string_agg(format('%I.%I', schemaname, tablename), ', ') INTO t FROM pg_tables
   WHERE schemaname IN ('auth', 'platform', 'finance', 'sales', 'hr', 'product', 'risk',
                        'execution', 'ai', 'idp')
     AND tablename NOT IN ('alembic_version', 'roles');
  EXECUTE 'TRUNCATE ' || t || ' CASCADE'; END $$""")


async def _count(db: AsyncSession, model: Any, *where: Any) -> int:
    stmt = select(func.count()).select_from(model).where(model.source == "SEED", *where)
    return int((await db.execute(stmt)).scalar_one())


async def _seed_all(db: AsyncSession) -> None:
    await seed_auth(db, _cfg(demo_password="demo-Pass-123"))
    owner = uuid.uuid4()
    await seed_finance(db, owner)
    await seed_hr(db, owner, owner)
    await seed_sales(db, owner)
    await seed_product(db, owner)
    await seed_risk(db, owner)
    await seed_execution(db, owner)


@pytest.fixture
async def seeded(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> AsyncSession:
    from app.core.config import get_config

    monkeypatch.setattr(get_config(), "demo_reference_date", AS_OF.isoformat())
    await db_session.execute(TRUNCATE_ALL)  # isolate from the dev DB's current seed
    await _seed_all(db_session)
    await _seed_all(db_session)  # second run must add nothing
    return db_session


async def test_tc_m11_06_org_and_demo_users(seeded: AsyncSession) -> None:
    """TC-M11-06: 7 departments sized per 08 §2.1, reporting line, demo users, idempotent."""
    assert await _count(seeded, Department) == 7
    rows = (await seeded.execute(
        select(Department.code, Department.head_employee_id).where(Department.source == "SEED")
    )).all()  # fmt: skip
    assert all(head is not None for _, head in rows)
    emps = (await seeded.execute(select(Employee).where(Employee.source == "SEED"))).scalars()
    people = list(emps)
    current = Counter(e.department_id for e in people if e.status != "terminated")
    dept_rows = (await seeded.execute(select(Department.code, Department.id))).all()
    dept_ids = {code: id_ for code, id_ in dept_rows}
    assert {d.code: current[dept_ids[d.code]] for d in DEPARTMENTS} == {
        d.code: d.size for d in DEPARTMENTS}  # fmt: skip
    assert 140 <= sum(current.values()) <= 160
    ceo = [e for e in people if e.manager_id is None]
    assert len(ceo) == 1  # every other employee has a direct manager
    ids = {e.id for e in people}
    assert all(e.manager_id in ids for e in people if e.manager_id is not None)

    users = {u.email: u for u in (await seeded.execute(select(User))).scalars()}
    for spec in DEMO_USERS:
        u = users[spec.email]
        assert list(u.scope_pillars) == list(spec.scope_pillars)
        assert u.department_id == dept_ids[spec.dept] and u.employee_id in ids
    assert users[AI_AGENT.email].is_service_account is True


async def _metrics(db: AsyncSession) -> dict[str, tuple[float | None, str | None]]:
    await seed_catalog(db)
    load_metric_providers()
    stats = await MetricStore(db).recompute(AS_OF)
    assert stats["failed_providers"] == 0
    rows = (await db.execute(
        select(Metric.code, MetricValue.value, MetricValue.threshold_status)
        .join(MetricValue, MetricValue.metric_id == Metric.id)
        .where(MetricValue.is_current.is_(True), MetricValue.scope_type == "company")
    )).all()  # fmt: skip
    return {c: (None if v is None else float(v), s) for c, v, s in rows}


async def test_tc_m11_07_uc_datasets_and_health_targets(seeded: AsyncSession) -> None:
    """TC-M11-07: minimum UC-01/02/03/04/06/07 data (08 §4) + 08 §5 demo statuses."""
    # UC-02/06 — one meeting with ≥ 3 decisions and ≥ 5 owned, dated action items (tasks).
    assert await _count(seeded, Meeting) == 1 and await _count(seeded, Decision) >= 3
    items = await _count(seeded, Task, Task.meeting_id.is_not(None),
                         Task.assignee_id.is_not(None), Task.due_date.is_not(None))  # fmt: skip
    assert items >= 5
    # UC-03 — a KPI whose latest measurement is below the band floor.
    below = select(func.count()).select_from(KpiMeasurement).where(
        KpiMeasurement.period_key == "2026-09",
        KpiMeasurement.evaluation_band.in_(("BELOW", "CRITICAL")))  # fmt: skip
    latest = int((await seeded.execute(below)).scalar_one())
    assert await _count(seeded, Kpi) >= 12 and latest >= 1
    # UC-04 — Q4 OKRs, ≥ 15 KRs, ≥ 1 low-confidence KR.
    assert await _count(seeded, Objective, Objective.period_key == "2026-Q4") >= 6
    assert await _count(seeded, KeyResult) >= 15
    assert await _count(seeded, KeyResult, KeyResult.confidence == "LOW") >= 1
    # D11 — projects across departments.
    depts = (await seeded.execute(select(func.count(func.distinct(Project.department_id)))
                                  .where(Project.source == "SEED"))).scalar_one()  # fmt: skip
    assert await _count(seeded, Project) == 10 and depts >= 5

    m = await _metrics(seeded)
    assert all(v is not None for v, _ in m.values()) and len(m) == 32
    # 08 §5 — main alert runway 🔴, overload 🟠, coverage 🟠, revenue vs plan 🟠, budget 🟠
    # (FIN-06 ~8 %, human decision 2026-10-23: amber under the catalog thresholds warn 0 / crit 10).
    assert m["METRIC-FIN-03"] == (5.3, "RED")
    assert m["METRIC-HR-03"] == (12.0, "YELLOW")
    assert m["METRIC-CUS-01"] == (2.7, "YELLOW")
    assert m["METRIC-FIN-01"] == (86.4, "YELLOW") and m["METRIC-FIN-06"] == (8.0, "YELLOW")
    # GREEN group: on-time 85 %, late projects 10 %, decisions executed 75 %, SEI 75 %, DQ ~88,
    # win rate stable, burn vs forecast.
    assert m["METRIC-OPS-01"] == (85.0, "GREEN") and m["METRIC-OPS-02"] == (10.0, "GREEN")
    assert m["METRIC-OPS-03"] == (75.0, "GREEN") and m["METRIC-RSK-06"] == (75.0, "GREEN")
    for code in ("METRIC-DQ-01", "METRIC-CUS-02", "METRIC-FIN-07"):
        assert m[code][1] == "GREEN", code


async def test_seed_snapshot_matches_seed(seeded: AsyncSession) -> None:
    """`seed_snapshot.json` (mock FE fixtures) is in sync with the seed — regenerate with
    `python -m app.seed.snapshot` (or `demo_reset.sh`). DQ-01's value depends on wall-clock
    freshness, so metrics are compared on code + status only."""
    import json

    from app.seed.snapshot import SNAPSHOT_PATH, build, metrics, render

    await _metrics(seeded)
    fresh = json.loads(render(build(await metrics(seeded))))
    committed = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    def brief(rows: list[dict[str, Any]]) -> list[tuple[str, str]]:
        return [(r["code"], r["status"]) for r in rows]

    assert brief(committed.pop("metrics")) == brief(fresh.pop("metrics"))
    assert committed == fresh
    assert not any(k in SNAPSHOT_PATH.read_text(encoding="utf-8")
                   for k in ("password", "salary", "national_id"))  # fmt: skip


async def test_tc_m12_17_org_and_assignments(seeded: AsyncSession) -> None:
    """T-617: one organization ABC, every department in it, every live employee has exactly
    one current assignment, ≥ 1 person with a transfer history; the seed ran twice."""
    from app.modules.hr.models import EmployeeAssignment, Organization
    from app.modules.hr.services.structure_service import StructureService
    from app.seed.hr_seed import ORG_ID, TRANSFERS, emp_id

    orgs = (await seeded.execute(select(Organization))).scalars().all()
    assert [o.id for o in orgs] == [ORG_ID] and orgs[0].code == "ABC"
    depts = (await seeded.execute(select(Department.organization_id))).scalars().all()
    assert depts and set(depts) == {ORG_ID}
    live_q = select(Employee).where(
        Employee.deleted_at.is_(None), Employee.termination_date.is_(None)
    )
    live = (await seeded.execute(live_q)).scalars().all()
    current = Counter((await seeded.execute(select(EmployeeAssignment.employee_id).where(
        EmployeeAssignment.valid_to.is_(None),
        EmployeeAssignment.deleted_at.is_(None)))).scalars().all())  # fmt: skip
    assert all(current[e.id] == 1 for e in live) and set(current.values()) == {1}
    by_emp = {e.id: e for e in live}
    for code, dept, _team, _mgr, moved in TRANSFERS:
        rows = (await seeded.execute(select(EmployeeAssignment).where(
            EmployeeAssignment.employee_id == emp_id(code)
        ).order_by(EmployeeAssignment.valid_from))).scalars().all()  # fmt: skip
        assert len(rows) == 2, code  # not duplicated by the second seed run
        old, now = rows
        assert old.valid_to == now.valid_from == moved and now.valid_to is None
        assert old.department_id == seed_uuid_dept(dept)
        assert (old.department_id, old.team_id) != (now.department_id, now.team_id)
        assert now.department_id == by_emp[emp_id(code)].department_id  # cache = current
    # as_of before the move: the person sits in the previous department of the tree
    code, dept, _t, _m, moved = TRANSFERS[0]
    from app.core.deps import Principal

    ceo = Principal(user_id=uuid.uuid4(), role="CEO", permissions=frozenset({"hr:read"}))
    before = await StructureService(seeded).tree(ceo, date(moved.year - 1, 6, 1), ORG_ID)
    after = await StructureService(seeded).tree(ceo, AS_OF, ORG_ID)
    assert _member_dept(before, emp_id(code)) == seed_uuid_dept(dept)
    assert _member_dept(after, emp_id(code)) == by_emp[emp_id(code)].department_id


def seed_uuid_dept(code: str) -> uuid.UUID:
    from app.seed.ids import seed_uuid

    return seed_uuid("department", code)


def _member_dept(tree: Any, employee_id: uuid.UUID) -> uuid.UUID | None:
    for node in tree.departments:  # flat list; members of teams are listed on the department
        if any(m.employee_id == employee_id for m in node.members):
            return node.id
    return None


async def test_tc_m13_11_seed_links_milestones_reassign(seeded: AsyncSession) -> None:
    """T-624: dependencies, sub-task, source_ref, milestones (1 late), PENDING task_reassign —
    added without new tasks so the 08 §5 targets (asserted above) stay; second run adds none."""
    from app.modules.execution.models import Milestone, TaskDependency
    from app.modules.execution.services.project_rules import milestone_late
    from app.modules.platform.models import ApprovalRequest
    from app.modules.platform.services.approval_service import RULE_TASK_REASSIGN
    from app.seed.ids import seed_uuid

    assert await _count(seeded, TaskDependency) >= 3
    assert await _count(seeded, Task, Task.parent_task_id.is_not(None)) >= 1
    refs = (await seeded.execute(select(Task.task_source, Task.source_ref).where(
        Task.source == "SEED", Task.source_ref.is_not(None)))).all()  # fmt: skip
    kinds = Counter(ref["kind"] for _, ref in refs)
    assert kinds["decision"] == 8 and kinds["document"] >= 1
    assert all(src == ("meeting" if ref["kind"] == "decision" else "document")
               for src, ref in refs)  # fmt: skip
    ms = (await seeded.execute(select(Milestone).where(Milestone.source == "SEED"))).scalars()
    per: Counter[uuid.UUID] = Counter()
    late: list[uuid.UUID] = []
    for m in ms:
        assert m.project_id is not None
        per[m.project_id] += 1
        if milestone_late(m.status, m.due_date, AS_OF):
            late.append(m.project_id)
    assert len([p for p, n in per.items() if n >= 2]) >= 3
    assert late == [seed_uuid("project", "PRJ-ERP")]
    reqs = (await seeded.execute(select(ApprovalRequest))).scalars().all()
    assert [(r.target_kind, r.status) for r in reqs] == [("task_reassign", "PENDING")]
    assert reqs[0].department_id == seed_uuid("department", "SVC")
    mgr = (await seeded.execute(select(User).where(User.email == "manager@abc.demo"))).scalar_one()
    assert mgr.department_id == reqs[0].department_id  # → in the SVC MGR's EP-WF-01 inbox
    from app.core.deps import Principal
    from app.core.pagination import PageParams
    from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
    from app.modules.platform.services.approval_service import ApprovalService

    p = Principal(user_id=mgr.id, role="MGR", permissions=frozenset(ROLE_PERMISSIONS["MGR"]),
                  department_id=mgr.department_id)  # fmt: skip
    items, _, pending = await ApprovalService(seeded).inbox(
        p, PageParams(limit=20, offset=0, sort_by="created_at", order="desc"),
        status=None, rule_code=None, target_kind=None,
    )  # fmt: skip
    assert [i.rule_code for i in items] == [RULE_TASK_REASSIGN] and pending == 1

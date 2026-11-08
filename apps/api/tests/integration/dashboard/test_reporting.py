"""TC-M21-04/05/06 — EP-RPT-01..03 Reporting v3 3 cấp (bảo mật scope + shape + cache).

`api` chạy trên app thật + db_session rollback. DB rỗng → service trả shape hợp lệ (count 0),
đủ để kiểm hợp đồng + ma trận quyền (R-DEC-84/85). Số sâu hơn kiểm ở seed snapshot (TC-M21-11).
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.modules.execution.models import CheckIn, KeyResult, Kpi, Objective, Task
from tests.conftest import ApiClient

EXEC = "/reporting/dashboards/executive"
DEPT = "/reporting/dashboards/department"
EMP = "/reporting/dashboards/employee"
DEPT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000d1")


async def _get(api: ApiClient, url: str, role: str, **params: Any) -> Any:
    return await api.call("GET", url, role, params=params or None)


# ---------- EP-RPT-01 executive ----------
async def test_executive_shape_cache_and_sei(api: ApiClient) -> None:
    res = await _get(api, EXEC, "CEO")
    assert res.status_code == 200, res.text
    assert res.headers["cache-control"] == "private, max-age=60"
    assert "Authorization" in res.headers["vary"]
    d = res.json()["data"]
    assert isinstance(d["summary_line"], str)
    assert len(d["tiles"]) <= 4
    for block in ("decisions_waiting", "open_risks", "ai_done"):
        assert d[block]["count"] >= 0 and isinstance(d[block]["items"], list)
    # SEI (METRIC-STR-02) nếu có phải đúng mã nhóm STR (R-DEC-83)
    if d["sei"] is not None:
        assert d["sei"]["metric_code"] == "METRIC-STR-02"


async def test_executive_dir_ok_emp_and_mgr_forbidden(api: ApiClient) -> None:
    assert (await _get(api, EXEC, "CFO")).status_code == 200  # DIR (scope F)
    emp = await _get(api, EXEC, "EMPLOYEE")
    assert emp.status_code == 403
    assert emp.json()["error"]["code"] == "FORBIDDEN_ROLE"
    assert (await _get(api, EXEC, "MANAGER")).status_code == 403


# ---------- EP-RPT-02 department ----------
async def test_department_mgr_dir_ok_emp_forbidden(api: ApiClient) -> None:
    # MGR scope = phòng của mình → token mang department_id (R-DEC-85)
    res = await api.call("GET", DEPT, "MANAGER", department_id=DEPT_ID)
    assert res.status_code == 200, res.text
    d = res.json()["data"]
    # KPI phòng chỉ nhóm thực thi (R-DEC-82): OPS/STR/PPL
    assert all(m["group"] in ("OPS", "STR", "PPL") for m in d["kpis"])
    assert d["workload"]["heatmap_ref"] == "/work/workload"
    assert (await _get(api, DEPT, "CEO")).status_code == 200
    assert (await _get(api, DEPT, "EMPLOYEE")).status_code == 403
    # MGR xin phòng khác → FORBIDDEN_SCOPE (R-DEC-85)
    other = uuid.UUID("00000000-0000-0000-0000-0000000000d2")
    denied = await api.call(
        "GET", DEPT, "MANAGER", department_id=DEPT_ID, params={"department_id": str(other)}
    )
    assert denied.status_code == 403


# ---------- EP-RPT-03 employee ----------
async def test_employee_any_caller_self_scope(api: ApiClient) -> None:
    for role in ("EMPLOYEE", "MANAGER", "CEO"):
        res = await _get(api, EMP, role)
        assert res.status_code == 200, (role, res.text)
        d = res.json()["data"]
        for k in ("overdue", "today", "this_week"):
            assert d["my_tasks"][k] >= 0


# ---------- F6: real numbers, scoped ----------
TODAY = date(2041, 5, 20)  # Monday; Q2 period running


@pytest.fixture
def pinned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_config(), "business_date_override", TODAY)


async def _okr(
    db: AsyncSession, owner: uuid.UUID, dept: uuid.UUID, *, at_risk: bool = False,
    status: str = "active", period: str = "2041-Q2",
) -> KeyResult:  # fmt: skip
    o = Objective(title="O", period_key=period, level="department", okr_type="committed",
                  weight_pct=100, owner_id=owner, department_id=dept, status=status,
                  progress_pct=0, source="MANUAL")  # fmt: skip
    db.add(o)
    await db.flush()
    k = KeyResult(objective_id=o.id, title="KR doanh thu", unit="%", baseline=0, target=100,
                  current_value=0, weight_pct=100, owner_id=owner, status="active",
                  at_risk=at_risk, source="MANUAL")  # fmt: skip
    db.add(k)
    await db.flush()
    return k


async def _task(
    db: AsyncSession, dept: uuid.UUID, due: date, status: str = "todo", **kw: Any
) -> None:
    db.add(Task(title="t", department_id=dept, due_date=due, status=status, priority="medium",
                task_source="manual", is_critical=False, source="MANUAL", **kw))  # fmt: skip
    await db.flush()


async def test_department_counts_are_real_and_scoped(
    api: ApiClient, db_session: AsyncSession, pinned: None
) -> None:
    mine, other = uuid.uuid4(), uuid.uuid4()
    me = uuid.uuid4()
    await _okr(db_session, me, mine, at_risk=True)
    await _okr(db_session, me, mine)
    await _okr(db_session, me, mine, status="draft")  # not current
    await _okr(db_session, me, mine, period="2041-Q1")  # other period
    await _okr(db_session, me, other, at_risk=True)
    await _task(db_session, mine, TODAY - timedelta(days=1))
    await _task(db_session, mine, TODAY)
    await _task(db_session, mine, TODAY + timedelta(days=3))
    await _task(db_session, mine, TODAY + timedelta(days=30))  # beyond the week
    await _task(db_session, mine, TODAY - timedelta(days=1), status="done")  # not open
    await _task(db_session, other, TODAY)
    d = (await api.call("GET", DEPT, "MANAGER", department_id=mine)).json()["data"]
    assert d["okrs"] == {"at_risk_count": 1, "total": 2}
    assert d["due_tasks"] == {"overdue": 1, "today": 1, "this_week": 2}
    company = (await api.call("GET", DEPT, "CEO")).json()["data"]
    assert company["okrs"]["total"] >= 3 and company["okrs"]["at_risk_count"] >= 2


async def test_employee_goals_checkins_workload_are_real(
    api: ApiClient, db_session: AsyncSession, pinned: None
) -> None:
    me, someone = uuid.uuid4(), uuid.uuid4()
    dept = uuid.uuid4()
    open_kr = await _okr(db_session, me, dept)
    done_kr = await _okr(db_session, me, dept)
    await _okr(db_session, someone, dept)  # not mine
    kpi = Kpi(code=uuid.uuid4().hex[:8], name="KPI bán hàng", unit="%", target_value=100,
              direction="HIGHER_IS_BETTER", value_type="percentage", data_source_kind="manual",
              period_type="MONTH", weight_pct=100, owner_id=me, status="active",
              source="MANUAL")  # fmt: skip
    db_session.add(kpi)
    db_session.add(CheckIn(key_result_id=done_kr.id, value=5, confidence="HIGH", user_id=me,
                           checked_in_at=datetime(2041, 5, 20, 3, tzinfo=UTC)))  # fmt: skip
    await db_session.flush()
    await _task(db_session, dept, TODAY, assignee_id=me, estimate_hours=20)
    await db_session.execute(
        update(Task)
        .where(Task.assignee_id == me)
        .values(created_at=datetime(2041, 5, 18, tzinfo=UTC))
    )
    r = await api.http.get(f"/api/v1{EMP}", headers=api.headers("EMPLOYEE", user_id=me))
    d = r.json()["data"]
    assert d["my_goals"] == {"kpis": 1, "krs": 2}
    assert d["workload_week_pct"] == 50.0  # 20 h of 40
    pending = {(p["target_type"], p["target_id"]): p for p in d["pending_checkins"]}
    assert set(pending) == {("key_result", str(open_kr.id)), ("kpi", str(kpi.id))}
    assert pending[("key_result", str(open_kr.id))]["period_key"] == "2041-Q2"
    assert pending[("kpi", str(kpi.id))]["period_key"] == "2041-05"


async def test_employee_without_goals_reads_zero_not_null(api: ApiClient, pinned: None) -> None:
    d = (await api.call("GET", EMP, "EMPLOYEE")).json()["data"]
    assert d["my_goals"] == {"kpis": 0, "krs": 0} and d["pending_checkins"] == []
    assert d["workload_week_pct"] == 0.0


async def test_executive_summary_has_a_code_and_params(api: ApiClient) -> None:
    d = (await api.call("GET", EXEC, "CEO")).json()["data"]
    assert d["summary_key"] == "reporting.executiveSummary"
    assert d["summary_params"]["decisions"] == d["decisions_waiting"]["count"]
    assert d["summary_params"]["risks"] == d["open_risks"]["count"]

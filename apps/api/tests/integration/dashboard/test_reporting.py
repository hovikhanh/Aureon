"""TC-M21-04/05/06 — EP-RPT-01..03 Reporting v3 3 cấp (bảo mật scope + shape + cache).

`api` chạy trên app thật + db_session rollback. DB rỗng → service trả shape hợp lệ (count 0),
đủ để kiểm hợp đồng + ma trận quyền (R-DEC-84/85). Số sâu hơn kiểm ở seed snapshot (TC-M21-11).
"""

import uuid
from typing import Any

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

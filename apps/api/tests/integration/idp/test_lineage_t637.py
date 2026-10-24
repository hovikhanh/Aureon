"""T-637 / TC-M15-09 — lineage on every commit + EP-DC-26 (FR-DATA-04, R-DEC-64)."""

import uuid
from typing import Any

import pytest
from sqlalchemy import select

from app.modules.platform.models import DataLineage
from tests.conftest import ApiClient
from tests.integration.idp.critical_helpers import approve_http
from tests.integration.idp.test_import_c5_t635 import _upload, _xlsx

pytestmark = pytest.mark.integration

ROWS = [  # data starts on Excel row 4 (title, blank, header) → row 7 = 4th row
    ["PB-L1", "Phòng Lineage", "Trưởng phòng", f"L637-0{i}", f"Người {i}", None, "01/02/2024",
     "active", 20000000 + i]
    for i in range(1, 6)
]  # fmt: skip


async def _committed(api: ApiClient, db) -> tuple[uuid.UUID, dict[str, Any]]:
    uid = uuid.uuid4()
    p = (await _upload(api, "CEO", _xlsx(ROWS, tag=uuid.uuid4().hex), user_id=uid)).json()["data"]
    sub = await api.http.post(f"/api/v1/data-capture/imports/{p['batch_id']}/submit",
                              headers=api.headers("CEO", idem=True, user_id=uid),
                              json={"version": p["version"]})  # fmt: skip
    doc_id = sub.json()["data"]["document"]["id"]
    ok = await approve_http(api, db, "HR_MANAGER", doc_id)
    assert ok.status_code == 200, ok.text
    acts = ok.json()["data"]["actions"]
    return uuid.UUID(doc_id), {a["table"]: a["ids"] for a in acts}


async def test_commit_writes_one_link_per_column(api: ApiClient, db_session, idp_store) -> None:
    doc_id, refs = await _committed(api, db_session)
    emp_id = uuid.UUID(refs["hr.employees"][3])  # 4th data row
    links = (await db_session.execute(select(DataLineage).where(
        DataLineage.target_id == emp_id))).scalars().all()  # fmt: skip
    cols = sorted(lk.target_column for lk in links)
    assert {"employee_code", "full_name", "hire_date", "salary"} <= set(cols)
    assert len(cols) == len(set(cols))  # one row per target column
    assert all(lk.link_kind == "RECORD_FROM_FIELD" and lk.row_index == 7 for lk in links)
    assert all(lk.document_action_id and lk.document_page_id for lk in links)
    assert all(lk.source_document_id == doc_id for lk in links)
    dept = (await db_session.execute(select(DataLineage).where(
        DataLineage.target_table == "departments", DataLineage.source_document_id == doc_id,
    ))).scalars().all()  # fmt: skip
    assert {lk.row_index for lk in dept} == {4}  # rows 5..8 reused the department → no link

    r = await api.call("GET", f"/lineage/hr.employees/{emp_id}", "CEO")
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["restricted"] is False and body["entity"] == "hr.employees"
    by_col = {lk["target_column"]: lk for lk in body["links"]}
    assert by_col["full_name"]["sheet_name"] == "Nhân sự" and by_col["full_name"]["row_index"] == 7
    assert by_col["full_name"]["document_type"] == "HR_ROSTER"
    assert by_col["full_name"]["action_name"] == "ACT-create_employee"
    assert by_col["full_name"]["committed_at"] is not None
    assert by_col["salary"]["raw_text"] is None  # level-4 raw text is never stored
    assert by_col["full_name"]["raw_text"] == "Người 4"


async def test_scope_both_sides_and_masking(api: ApiClient, db_session, idp_store) -> None:
    from app.modules.hr.services.hr_service import HrService

    _doc_id, refs = await _committed(api, db_session)
    emp_id = uuid.UUID(refs["hr.employees"][0])
    emp = await HrService(db_session).employees.get(emp_id)
    url = f"/lineage/hr.employees/{emp_id}"
    other = await api.call("GET", url, "EMPLOYEE")  # EMP sees only their own profile
    assert other.json()["data"] == {
        "entity": None,
        "id": None,
        "links": None,
        "restricted": True,
        "reason": "target_out_of_scope",
    }
    mgr = await api.call("GET", url, "MANAGER", department_id=uuid.uuid4())
    assert mgr.json()["data"]["reason"] == "target_out_of_scope"
    rev = await api.call("GET", url, "REVIEWER")
    assert rev.json()["data"]["reason"] == "target_out_of_scope"
    own_mgr = await api.call("GET", url, "MANAGER", department_id=emp.department_id)
    assert own_mgr.json()["data"] == {
        **own_mgr.json()["data"],
        "restricted": True,
        "reason": "source_out_of_scope",
    }  # doc of another dept
    bad = await api.call("GET", f"/lineage/hr.salaries/{emp_id}", "CEO")
    assert bad.status_code == 422
    empty = await api.call("GET", f"/lineage/execution.tasks/{uuid.uuid4()}", "CEO")
    assert empty.json()["data"]["reason"] == "target_out_of_scope"  # 404 → restricted
    other_tenant = await api.call("GET", url, "CEO", tenant_id=uuid.uuid4())
    assert other_tenant.status_code in (200, 401, 403, 404)
    if other_tenant.status_code == 200:
        assert other_tenant.json()["data"]["restricted"] is True
    dept_id = uuid.UUID(refs["hr.departments"][0])
    d = await api.call("GET", f"/lineage/hr.departments/{dept_id}", "CEO")
    assert {lk["target_column"] for lk in d.json()["data"]["links"]} == {"code", "name"}


async def test_level4_raw_text_masked(api: ApiClient, db_session, idp_store) -> None:
    from sqlalchemy import update

    from app.modules.hr.services.hr_service import HrService
    from app.modules.idp.models import ExtractedField, SourceDocument

    doc_id, refs = await _committed(api, db_session)
    emp_id = uuid.UUID(refs["hr.employees"][0])
    emp = await HrService(db_session).employees.get(emp_id)
    await db_session.execute(update(SourceDocument).where(SourceDocument.id == doc_id)
                             .values(department_id=emp.department_id))  # fmt: skip
    link = (
        await db_session.execute(
            select(DataLineage).where(
                DataLineage.target_id == emp_id, DataLineage.target_column == "salary"
            )
        )
    ).scalar_one()
    await db_session.execute(
        update(ExtractedField)
        .where(ExtractedField.id == link.extracted_field_id)
        .values(raw_text="20.000.001")
    )  # C3-like
    await db_session.flush()
    url = f"/lineage/hr.employees/{emp_id}"
    mgr = await api.call("GET", url, "MANAGER", department_id=emp.department_id)
    body = mgr.json()["data"]
    assert body["restricted"] is False
    sal = next(lk for lk in body["links"] if lk["target_column"] == "salary")
    assert sal["raw_text"] == {"masked": True}
    ceo = await api.call("GET", url, "CEO")
    sal = next(lk for lk in ceo.json()["data"]["links"] if lk["target_column"] == "salary")
    assert sal["raw_text"] == "20.000.001"


async def test_execution_entities_and_c1(api: ApiClient, db_session, idp_store) -> None:
    from tests.integration.idp.test_manual_c1_t635 import _task_type

    await _task_type(db_session)
    r = await api.call(
        "POST",
        "/data-capture/manual",
        "CEO",
        json={
            "document_type": "TEST_TASK",
            "schema_version": 1,
            "rows": [{"title": "Lineage task"}],
        },
    )
    task_id = r.json()["data"]["actions"][0]["ids"][0]
    t = await api.call("GET", f"/lineage/execution.tasks/{task_id}", "CEO")
    links = t.json()["data"]["links"]
    assert [(lk["target_column"], lk["row_index"], lk["page_number"]) for lk in links] == [
        ("title", 1, None)
    ]
    body = {"document_type": "PLAN_KPI_OKR", "schema_version": 1, "rows": [{
        "period_key": "2026-10", "owner_code": "NV-0002", "objective_title": "Tăng trưởng L",
        "kr_title": "KR L", "kpi_code": "KPI-L637", "kpi_name": "Doanh thu L", "unit": "VND",
        "target": "100", "baseline": "0", "kpi_period_target": "100"}]}  # fmt: skip
    p = await api.call("POST", "/data-capture/manual", "CEO", json=body)
    assert p.status_code == 201, p.text
    acts = {a["table"]: a["ids"][0] for a in p.json()["data"]["actions"]}
    for entity in (
        "execution.objectives",
        "execution.key_results",
        "execution.kpis",
        "execution.kpi_targets",
    ):
        got = await api.call("GET", f"/lineage/{entity}/{acts[entity]}", "CEO")
        assert got.json()["data"]["links"], entity
    for entity in (
        "execution.kpi_measurements",
        "execution.check_ins",
        "hr.teams",
        "hr.positions",
        "finance.invoices",
    ):
        miss = await api.call("GET", f"/lineage/{entity}/{uuid.uuid4()}", "CEO")
        assert miss.json()["data"]["reason"] == "target_out_of_scope", entity

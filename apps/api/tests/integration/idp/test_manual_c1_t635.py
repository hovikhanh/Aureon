"""T-635 / TC-M15-04 — C1 manual form + submit (EP-DC-15/16, R-DEC-65).

A test-only doc type `TEST_TASK` (published schema → `ACT-create_task`) is inserted inside the
rolled-back test transaction so the "EMP creates own task" path runs without seed changes.
"""

import uuid
from datetime import date, timedelta
from typing import Any

import pytest
from sqlalchemy import select

from app.modules.idp.models import (
    DocumentAction,
    DocumentType,
    ExtractedField,
    ExtractionSchema,
    ReviewAssignment,
    SourceDocument,
)
from app.modules.platform.models import AuditLog, OutboxEvent
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration


async def _task_type(db: Any) -> None:
    dt = DocumentType(code="TEST_TASK", name_vi="Việc", name_en="Task", pillars=["O"],
                      sensitivity_level=2, retention_years=1, classifier_keywords=[])  # fmt: skip
    db.add(dt)
    await db.flush()
    s = ExtractionSchema(
        document_type_id=dt.id, schema_version=1, status="published", thresholds={},
        action_names=["ACT-create_task"],
        fields=[
            {"name": "title", "label_key": "idp.field.title", "value_type": "text",
             "required": True, "is_critical": False, "sensitivity_level": 2, "group": "row",
             "target": {"action": "ACT-create_task", "param": "title"}},
            {"name": "due_date", "label_key": "idp.field.due_date", "value_type": "date",
             "required": False, "is_critical": False, "sensitivity_level": 2, "group": "row",
             "target": {"action": "ACT-create_task", "param": "due_date"}},
        ],
    )  # fmt: skip
    db.add(s)
    await db.flush()
    dt.current_schema_id = s.id
    await db.flush()


async def test_form_follows_published_schema(api: ApiClient, db_session) -> None:
    r = await api.call("GET", "/data-capture/forms/HR_ROSTER", "HR_MANAGER")
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    names = [f["name"] for f in body["fields"]]
    assert names[:2] == ["department_code", "department_name"] and "salary" in names
    salary = next(f for f in body["fields"] if f["name"] == "salary")
    assert salary["is_critical"] and salary["sensitivity_level"] == 4
    assert body["schema_version"] == 1 and body["permitted"] is True
    assert body["required_permissions"] == ["hr:admin", "hr:write"]
    emp = await api.call("GET", "/data-capture/forms/HR_ROSTER", "EMPLOYEE")
    assert emp.status_code == 200 and emp.json()["data"]["permitted"] is False
    missing = await api.call("GET", "/data-capture/forms/NOPE", "CEO")
    assert missing.status_code == 404


async def _audits(db: Any, doc_id: uuid.UUID, action: str) -> int:
    rows = await db.execute(select(AuditLog).where(AuditLog.action == action,
                                                   AuditLog.target_id == doc_id))  # fmt: skip
    return len(rows.scalars().all())


async def test_validation_error_creates_nothing(api: ApiClient, db_session) -> None:
    await _task_type(db_session)
    before = len((await db_session.execute(select(SourceDocument.id))).all())
    body = {"document_type": "TEST_TASK", "schema_version": 1,
            "rows": [{"title": ""}, {"title": "ok", "due_date": "31/02/2026"}]}  # fmt: skip
    r = await api.call("POST", "/data-capture/manual", "EMPLOYEE", json=body)
    assert r.status_code == 422, r.text
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    got = {(f["row_index"], f["field"], f["rule_code"]) for f in err["details"]["fields"]}
    assert got == {(1, "title", "REQUIRED"), (2, "due_date", "DATE_FORMAT")}
    assert len((await db_session.execute(select(SourceDocument.id))).all()) == before
    stale = await api.call("POST", "/data-capture/manual", "EMPLOYEE",
                           json={**body, "schema_version": 9})  # fmt: skip
    assert stale.status_code == 409


async def test_emp_commits_own_task_in_one_transaction(api: ApiClient, db_session) -> None:
    await _task_type(db_session)
    due = (date.today() + timedelta(days=3)).strftime("%d/%m/%Y")
    body = {"document_type": "TEST_TASK", "schema_version": 1,
            "rows": [{"title": "Gọi khách hàng", "due_date": due}]}  # fmt: skip
    h = api.headers("EMPLOYEE", idem=True)
    r = await api.http.post("/api/v1/data-capture/manual", headers=h, json=body)
    assert r.status_code == 201, r.text
    out = r.json()["data"]
    assert out["status"] == "COMMITTED" and out["undo_deadline"] is not None
    assert out["actions"][0]["table"] == "execution.tasks"
    assert out["document"]["document_type"] == "TEST_TASK" and out["document"]["can_undo"]
    doc_id = uuid.UUID(out["document"]["id"])
    doc = (await db_session.execute(select(SourceDocument).where(
        SourceDocument.id == doc_id))).scalar_one()  # fmt: skip
    assert (doc.kind, doc.channel, doc.source, doc.type_preselected) == (
        "MANUAL",
        "C1",
        "MANUAL",
        True,
    )
    fields = (await db_session.execute(select(ExtractedField).where(
        ExtractedField.source_location["kind"].astext == "manual"))).scalars().all()  # fmt: skip
    assert {(f.field_name, float(f.confidence)) for f in fields} >= {("title", 1.0)}
    acts = (await db_session.execute(select(DocumentAction).where(
        DocumentAction.source_document_id == doc_id))).scalars().all()  # fmt: skip
    assert [a.action_name for a in acts] == ["ACT-create_task"]
    ev = (await db_session.execute(select(OutboxEvent).where(
        OutboxEvent.event_type == "idp.document_committed",
        OutboxEvent.aggregate_id == doc_id))).scalars().all()  # fmt: skip
    assert len(ev) == 1 and await _audits(db_session, doc_id, "idp.manual_submit") == 1
    replay = await api.http.post("/api/v1/data-capture/manual", headers=h, json=body)
    assert replay.status_code == 201 and replay.json()["data"]["document"]["id"] == str(doc_id)
    no_key = await api.http.post("/api/v1/data-capture/manual",
                                 headers=api.headers("EMPLOYEE"), json=body)  # fmt: skip
    assert no_key.status_code == 400


async def _queued(db: Any, out: dict[str, Any]) -> SourceDocument:
    doc_id = uuid.UUID(out["document"]["id"])
    doc = (await db.execute(select(SourceDocument).where(SourceDocument.id == doc_id))).scalar_one()
    ra = (await db.execute(select(ReviewAssignment).where(
        ReviewAssignment.source_document_id == doc_id,
        ReviewAssignment.is_current.is_(True)))).scalar_one()  # fmt: skip
    assert ra.to_role_code == "REV" and out["actions"] == [] and out["undo_deadline"] is None
    acts = (await db.execute(select(DocumentAction).where(
        DocumentAction.source_document_id == doc_id))).scalars().all()  # fmt: skip
    assert acts == []
    return doc


async def test_emp_department_kpi_goes_to_review(api: ApiClient, db_session) -> None:
    body = {"document_type": "PLAN_KPI_OKR", "schema_version": 1, "rows": [{
        "period_key": "2026-Q4", "owner_code": "NV-0002", "kpi_code": "KPI-T635-EMP",
        "kpi_name": "Doanh thu phòng", "unit": "VND", "target": "1.000.000",
        "kpi_period_target": "1.000.000"}]}  # fmt: skip
    r = await api.call("POST", "/data-capture/manual", "EMPLOYEE", json=body)
    assert r.status_code == 201, r.text
    out = r.json()["data"]
    assert out["status"] == "NEEDS_REVIEW"
    doc = await _queued(db_session, out)
    assert doc.routing_reason == "MISSING_TARGET_PERMISSION"


async def test_reviewer_without_target_permission_queues(api: ApiClient, db_session) -> None:
    row = {
        "department_code": "PB-T635",
        "department_name": "Phòng thử",
        "employee_code": "NV-T635",
        "full_name": "Nguyễn Văn Thử",
        "hire_date": "01/03/2025",
        "salary": "15.000.000",
    }
    body = {"document_type": "HR_ROSTER", "schema_version": 1, "rows": [row]}
    r = await api.call("POST", "/data-capture/manual", "REVIEWER", json=body)
    assert r.status_code == 201, r.text
    doc = await _queued(db_session, r.json()["data"])
    assert doc.manual_payload["rows"][0]["salary"] == {"masked": True}  # level 4 not in clear
    sal = (await db_session.execute(select(ExtractedField).where(
        ExtractedField.field_name == "salary",
        ExtractedField.source_location["kind"].astext == "manual"))).scalars().all()  # fmt: skip
    assert sal and sal[-1].value == 15000000 and sal[-1].raw_text is None
    assert sal[-1].is_critical


async def test_department_override_needs_wide_scope(api: ApiClient, db_session) -> None:
    await _task_type(db_session)
    body = {"document_type": "TEST_TASK", "schema_version": 1, "rows": [{"title": "x"}],
            "department_id": str(uuid.uuid4())}  # fmt: skip
    r = await api.call("POST", "/data-capture/manual", "EMPLOYEE", json=body,
                       department_id=uuid.uuid4())  # fmt: skip
    assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    unknown = await api.call(
        "POST",
        "/data-capture/manual",
        "EMPLOYEE",
        json={"document_type": "TEST_TASK", "schema_version": 1, "rows": [{"title": "x", "zz": 1}]},
    )
    assert unknown.status_code == 422

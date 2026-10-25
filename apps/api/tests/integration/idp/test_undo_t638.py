"""T-638 / TC-M15-10 — undo a committed document within 7 days (EP-DC-24/25, R-DEC-66)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.modules.idp.models import CaptureIncident, SourceDocument
from app.modules.platform.models import AuditLog, DataLineage, OutboxEvent
from tests.conftest import ApiClient
from tests.integration.idp.test_lineage_t637 import ROWS, _committed
from tests.integration.idp.test_manual_c1_t635 import _task_type

pytestmark = pytest.mark.integration
UNDO = "/data-capture/documents/{}/undo"
BODY = {"reason": "nhập nhầm", "reason_code": "mistake"}


async def _manual_task(api: ApiClient, db, uid: uuid.UUID) -> tuple[str, str]:
    await _task_type(db)
    r = await api.http.post("/api/v1/data-capture/manual", headers=api.headers(
        "CEO", idem=True, user_id=uid), json={"document_type": "TEST_TASK", "schema_version": 1,
        "rows": [{"title": "Undo me"}]})  # fmt: skip
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    return data["document"]["id"], data["actions"][0]["ids"][0]


async def _undo(api: ApiClient, role: str, doc_id: str, uid: uuid.UUID, **body) -> object:
    return await api.http.post(f"/api/v1{UNDO.format(doc_id)}", json={**BODY, **body},
                               headers=api.headers(role, idem=True, user_id=uid))  # fmt: skip


async def test_undo_manual_task_reverses_and_logs(api: ApiClient, db_session) -> None:
    uid = uuid.uuid4()
    doc_id, task_id = await _manual_task(api, db_session, uid)
    acts = await api.call("GET", f"/data-capture/documents/{doc_id}/actions", "CEO")
    assert [a["status"] for a in acts.json()["data"]] == ["applied"]
    r = await _undo(api, "CEO", doc_id, uid)
    assert r.status_code == 200, r.text
    out = r.json()["data"]
    assert out["document"]["status"] == "ROLLED_BACK" and out["document"]["can_undo"] is False
    assert out["reverted_actions"] == [{"action_name": "ACT-create_task", "ids": [task_id],
                                        "table": "execution.tasks"}]  # fmt: skip
    gone = await api.call("GET", f"/execution/tasks/{task_id}", "CEO")
    assert gone.status_code == 404
    acts = (await api.call("GET", f"/data-capture/documents/{doc_id}/actions", "CEO")).json()
    assert acts["data"][0]["status"] == "reverted" and acts["data"][0]["reverted_at"]
    links = (await db_session.execute(select(DataLineage).where(
        DataLineage.source_document_id == uuid.UUID(doc_id)))).scalars().all()  # fmt: skip
    assert links and all(lk.revoked_at is not None for lk in links)
    audit = (await db_session.execute(select(AuditLog.action).where(
        AuditLog.target_id == uuid.UUID(doc_id)))).scalars().all()  # fmt: skip
    assert "idp.document_rollback" in audit
    evt = (await db_session.execute(select(OutboxEvent).where(
        OutboxEvent.event_type == "idp.document_rolled_back",
        OutboxEvent.aggregate_id == uuid.UUID(doc_id)))).scalar_one()  # fmt: skip
    assert evt.payload["reason_code"] == "mistake" and "reason" not in evt.payload
    assert evt.payload["target_tables"] == ["execution.tasks"]
    again = await _undo(api, "CEO", doc_id, uid)
    assert again.status_code == 409 and again.json()["error"]["code"] == "CONFLICT_STATE"


async def test_undo_guards_expired_forbidden_conflict(api: ApiClient, db_session) -> None:
    from app.modules.execution.models import Task

    uid = uuid.uuid4()
    doc_id, task_id = await _manual_task(api, db_session, uid)
    other = await _undo(api, "MANAGER", doc_id, uuid.uuid4())  # not involved, not scoped
    assert other.status_code in (403, 404)
    rev = await _undo(api, "REVIEWER", doc_id, uid)  # submitter id, lacks execution:write
    assert rev.status_code == 403, rev.text
    assert rev.json()["error"]["details"]["missing"] == ["execution:write"]
    await db_session.execute(update(Task).where(Task.id == uuid.UUID(task_id))
                             .values(version=Task.version + 1))  # fmt: skip
    await db_session.commit()
    c = await _undo(api, "CEO", doc_id, uid)
    assert c.status_code == 409, c.text
    assert c.json()["error"]["details"]["conflicts"] == [
        {"table": "execution.tasks", "id": task_id}]  # fmt: skip
    await db_session.execute(update(SourceDocument).where(
        SourceDocument.id == uuid.UUID(doc_id)).values(
        undo_deadline=datetime.now(UTC) - timedelta(minutes=1)))  # fmt: skip
    await db_session.commit()
    e = await _undo(api, "CEO", doc_id, uid)
    assert e.status_code == 410 and e.json()["error"]["code"] == "UNDO_EXPIRED"


async def test_undo_hr_import_reverses_all_and_opens_incidents(api: ApiClient, db_session) -> None:
    from app.modules.hr.services.hr_service import HrService

    doc_id, refs = await _committed(api, db_session)
    assert refs["hr.employees"]
    tree = (await api.call("GET", "/org/tree", "CEO")).json()["data"]
    assert "PB-L1" in {d["code"] for d in tree["departments"]}
    acts = (await api.call("GET", f"/data-capture/documents/{doc_id}/actions",
                           "HR_MANAGER")).json()["data"]  # fmt: skip
    assert [a["seq"] for a in acts] == sorted(a["seq"] for a in acts) and len(acts) >= 2
    r = await _undo(api, "HR_MANAGER", str(doc_id), uuid.uuid4(),
                    reason_code="critical_field_wrong")  # fmt: skip
    assert r.status_code == 200, r.text
    hr = HrService(db_session)
    assert await hr.employee_id_by_code("L637-04") is None  # soft-deleted by the undo
    # created + archived the same day (`valid_to` = today + 1): gone from today's tree
    tree = (await api.call("GET", "/org/tree", "CEO")).json()["data"]
    assert "PB-L1" not in {d["code"] for d in tree["departments"]}
    assert not {m["employee_code"] for d in tree["departments"] for m in d["members"]
                if m["employee_code"].startswith("L637-")}  # fmt: skip
    incs = (await db_session.execute(select(CaptureIncident).where(
        CaptureIncident.source_document_id == doc_id))).scalars().all()  # fmt: skip
    assert incs and all(i.detected_by == "undo" and i.undetected and i.is_critical
                        for i in incs)  # fmt: skip
    assert len({i.field_name for i in incs}) == len(incs)


TABLES = [
    "hr.departments", "hr.teams", "hr.positions", "hr.employees", "execution.objectives",
    "execution.key_results", "execution.kpis", "execution.kpi_targets", "execution.tasks",
    "finance.invoices", "other.table",
]  # fmt: skip


@pytest.mark.parametrize("table", TABLES)
async def test_current_version_missing_row_is_none(db_session, table: str) -> None:
    from app.core.deps import Principal
    from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
    from app.modules.idp.services.undo_versions import current_version

    ceo = Principal(user_id=uuid.uuid4(), role="CEO",
                    permissions=frozenset(ROLE_PERMISSIONS["CEO"]))  # fmt: skip
    assert await current_version(db_session, ceo, table, uuid.uuid4()) is None


async def test_authorize_submitter_committer_approver(db_session, monkeypatch) -> None:
    from app.core.deps import Principal
    from app.core.errors import PermissionDeniedError
    from app.modules.idp.services import undo_service
    from app.modules.idp.services.undo_service import UndoService

    def mgr() -> Principal:
        return Principal(
            user_id=uuid.uuid4(), role="MGR", permissions=frozenset(), department_id=uuid.uuid4()
        )

    doc = SourceDocument(id=uuid.uuid4(), submitted_by=uuid.uuid4(), committed_by=uuid.uuid4())
    svc = UndoService(db_session)
    committer = mgr()
    doc.committed_by = committer.user_id
    await svc._authorize(committer, doc)
    with pytest.raises(PermissionDeniedError):
        await svc._authorize(mgr(), doc)
    approver = mgr()

    async def _approvers(_db: object, _doc_id: uuid.UUID) -> set[uuid.UUID]:
        return {approver.user_id}

    monkeypatch.setattr(undo_service, "approvers_of", _approvers)
    await svc._authorize(approver, doc)  # approvers_of lookup


async def test_approvers_of_reads_approved_reviews(api: ApiClient, db_session) -> None:
    from app.modules.idp.repositories import approvers_of

    doc_id, _ = await _committed(api, db_session)
    assert len(await approvers_of(db_session, doc_id)) == 1
    assert await approvers_of(db_session, uuid.uuid4()) == set()


async def test_undo_keeps_reused_department(api: ApiClient, db_session) -> None:
    """Second import re-uses PB-L1 (`reused=true`) → undoing it must leave PB-L1 in place."""
    from app.modules.hr.services.hr_service import HrService

    tag = uuid.uuid4().hex[:6]
    first = [[*r[:3], f"R{tag}-{i}", *r[4:]] for i, r in enumerate(ROWS)]
    await _committed(api, db_session, first)  # PB-L1 exists after this one
    second, _ = await _committed(api, db_session, [[*r[:3], f"S{tag}-{i}", *r[4:]]
                                                  for i, r in enumerate(ROWS)])  # fmt: skip
    acts = (await api.call("GET", f"/data-capture/documents/{second}/actions",
                           "HR_MANAGER")).json()["data"]  # fmt: skip
    dept = [a for a in acts if a["action_name"] == "ACT-create_department"]
    assert dept and all(r["reused"] for a in dept for r in a["result_refs"])
    r = await _undo(api, "HR_MANAGER", str(second), uuid.uuid4())
    assert r.status_code == 200, r.text
    assert await HrService(db_session).department_id_by_code("PB-L1") is not None

"""M1.5 review — `/data-capture/*` GET-by-id follows the inbox row scope (10 §7.2.4 scope table).

Before the fix EP-DC-18..21/24/25 used the v2.1 `document_visible` (same department), so an EMP
could read the import rows (level 3) / action log of a colleague's document, and ADM
(`idp:admin` ⇒ all departments) could read action logs of any doc type outside #4. EP-DC-37
listed every incident regardless of scope.
"""

import uuid
from typing import Any

import pytest

from app.modules.idp.models import CaptureIncident
from tests.conftest import ApiClient
from tests.integration.idp.test_import_c5_t635 import GOOD, _upload, _xlsx
from tests.integration.idp.test_inbox_t635 import _doc

pytestmark = pytest.mark.integration


async def _get(api: ApiClient, path: str, role: str, **kw: Any) -> Any:
    return await api.http.get(f"/api/v1{path}", headers=api.headers(role, **kw))


async def test_emp_cannot_read_colleague_import(api: ApiClient, db_session, idp_store) -> None:
    dept, owner, peer = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    r = await _upload(api, "EMPLOYEE", _xlsx(GOOD, tag=uuid.uuid4().hex), user_id=owner,
                      department_id=dept)  # fmt: skip
    assert r.status_code == 201, r.text
    bid = r.json()["data"]["batch_id"]
    for path in (f"/data-capture/imports/{bid}", f"/data-capture/imports/{bid}/rows"):
        mine = await _get(api, path, "EMPLOYEE", user_id=owner, department_id=dept)
        assert mine.status_code == 200, mine.text
        other = await _get(api, path, "EMPLOYEE", user_id=peer, department_id=dept)
        assert other.status_code == 404, (path, other.text)
    mgr = await api.call("GET", f"/data-capture/imports/{bid}", "MANAGER", department_id=dept)
    assert mgr.status_code == 200  # MGR: own department


async def test_actions_log_scope(api: ApiClient, db_session) -> None:
    dept, owner = uuid.uuid4(), uuid.uuid4()
    doc = await _doc(db_session, owner, "COMMITTED", dept=dept, type_code="INVOICE")
    await db_session.commit()
    path = f"/data-capture/documents/{doc.id}/actions"
    assert (await _get(api, path, "EMPLOYEE", user_id=owner,
                       department_id=dept)).status_code == 200  # fmt: skip
    assert (await _get(api, path, "EMPLOYEE", user_id=uuid.uuid4(),
                       department_id=dept)).status_code == 404  # fmt: skip
    assert (await api.call("GET", path, "ADMIN")).status_code == 404  # R-DEC-76: not #4
    undo = await api.http.post(
        f"/api/v1/data-capture/documents/{doc.id}/undo",
        json={"reason": "x", "reason_code": "mistake"},
        headers=api.headers("EMPLOYEE", idem=True, user_id=uuid.uuid4(), department_id=dept),
    )
    assert undo.status_code == 404


async def test_incident_list_scoped(api: ApiClient, db_session) -> None:
    dept_a, dept_b = uuid.uuid4(), uuid.uuid4()
    doc_a = await _doc(db_session, uuid.uuid4(), "COMMITTED", dept=dept_a)
    doc_b = await _doc(db_session, uuid.uuid4(), "COMMITTED", dept=dept_b)
    reporter = uuid.uuid4()
    for d in (doc_a, doc_b):
        db_session.add(CaptureIncident(
            source_document_id=d.id, field_name="vat_amount", is_critical=True,
            detected_by="post_commit", undetected=True, description="x",
            reported_by=reporter, source="MANUAL",
        ))  # fmt: skip
    await db_session.commit()

    async def _ids(role: str, **kw: Any) -> set[uuid.UUID]:
        r = await api.http.get(
            "/api/v1/data-capture/incidents", params={"limit": 100}, headers=api.headers(role, **kw)
        )
        assert r.status_code == 200, r.text
        return {uuid.UUID(i["source_document_id"]) for i in r.json()["data"]}

    mgr = await _ids("MANAGER", department_id=dept_a)
    assert doc_a.id in mgr and doc_b.id not in mgr
    assert {doc_a.id, doc_b.id} <= await _ids("HR_MANAGER", scope_pillars=())  # DIR, all khối
    assert {doc_a.id, doc_b.id} <= await _ids("MANAGER", user_id=reporter)  # own reports

"""TC-M6-01 — a DIR reviews / opens the documents of its khối, as the inbox lists them (10 §7.2.4).

Found on the live stack (M6, CFO): the inbox (EP-DC-13) scoped a DIR by khối (`scope_pillars` ∩
document `pillars`), but review detail (EP-DC-05) and document detail (EP-25) still used the v2.1
department rule, so F invoices filed by other departments were listed and then `404` on "Review".
Out-of-khối documents stay `404` (existence hidden); the department rule still applies.
"""

import uuid
from typing import Any

import pytest

from tests.conftest import ApiClient
from tests.integration.idp.test_inbox_t635 import _doc

pytestmark = pytest.mark.integration


async def _get(api: ApiClient, path: str, **kw: Any) -> Any:
    return await api.http.get(f"/api/v1{path}", headers=api.headers("DIR", **kw))


async def test_dir_opens_review_of_khoi_document_from_another_department(
    api: ApiClient, db_session: Any
) -> None:
    other_dept, cfo_dept = uuid.uuid4(), uuid.uuid4()
    doc = await _doc(db_session, uuid.uuid4(), "NEEDS_REVIEW", dept=other_dept, pillars=["F"],
                     type_code="INVOICE")  # fmt: skip
    await db_session.commit()
    cfo = {"department_id": cfo_dept, "scope_pillars": ("F",)}
    inbox = await _get(api, "/data-capture/inbox?limit=100", **cfo)
    assert str(doc.id) in {it["document"]["id"] for it in inbox.json()["data"]}
    for path in (f"/idp/documents/{doc.id}/review", f"/idp/documents/{doc.id}"):
        r = await _get(api, path, **cfo)
        assert r.status_code == 200, (path, r.text)


async def test_out_of_khoi_document_stays_hidden_but_department_rule_still_holds(
    api: ApiClient, db_session: Any
) -> None:
    dept = uuid.uuid4()
    f_doc = await _doc(db_session, uuid.uuid4(), "NEEDS_REVIEW", dept=uuid.uuid4(), pillars=["F"],
                       type_code="INVOICE")  # fmt: skip
    own_dept = await _doc(db_session, uuid.uuid4(), "NEEDS_REVIEW", dept=dept, pillars=["F"],
                          type_code="INVOICE")  # fmt: skip
    await db_session.commit()
    sales = {"department_id": dept, "scope_pillars": ("C",)}
    for path in (f"/idp/documents/{f_doc.id}/review", f"/idp/documents/{f_doc.id}"):
        r = await _get(api, path, **sales)
        assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND", path
    r = await _get(api, f"/idp/documents/{own_dept.id}/review", **sales)
    assert r.status_code == 200, r.text  # same department (v2.1 rule) — unchanged

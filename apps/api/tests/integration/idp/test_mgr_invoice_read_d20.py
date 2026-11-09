"""TC-V4-18 — D-20 / R-DEC-199: a Manager reads (list + detail) the invoices they created, including
an invoice committed through the IDP review (the committer is `Invoice.created_by`).

Company invoices created by others stay `403 FORBIDDEN_SCOPE` for the MGR; the MGR still cannot
update / delete / pay a company invoice (its own included); the REV keeps no general finance read.
"""

import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.finance.models import Invoice
from app.modules.idp.services.commit_service import CommitService
from tests.conftest import ApiClient
from tests.integration.idp.critical_helpers import confirm_critical
from tests.integration.idp.test_review_workflow import _ingest_invoice

pytestmark = pytest.mark.integration


def _mgr(uid: uuid.UUID, dept: uuid.UUID) -> Principal:
    return Principal(user_id=uid, role="MGR", permissions=frozenset(ROLE_PERMISSIONS["MGR"]),
                     department_id=dept)  # fmt: skip


def _denied(r: Any) -> bool:
    return r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_SCOPE"


async def _as(
    api: ApiClient, method: str, url: str, role: str, uid: uuid.UUID | None = None,
    dept: uuid.UUID | None = None, **kw: Any,
) -> Any:  # fmt: skip
    h = api.headers(role, user_id=uid, department_id=dept, idem=method == "POST")
    return await api.http.request(method, f"/api/v1{url}", headers=h, **kw)


async def _all_ids(api: ApiClient, role: str, uid: uuid.UUID, dept: uuid.UUID) -> set[str]:
    r = await _as(api, "GET", "/finance/invoices", role, uid, dept, params={"limit": 100})
    assert r.status_code == 200, r.text
    assert not r.json()["meta"]["pagination"]["has_next"]
    return {x["id"] for x in r.json()["data"]}


async def test_manager_reads_own_idp_committed_invoice_only(
    api: ApiClient, db_session: AsyncSession, idp_store: None
) -> None:
    uid, dept = uuid.uuid4(), uuid.uuid4()
    mgr = _mgr(uid, dept)
    doc_id = await _ingest_invoice(db_session, mgr)  # MGR files the supplier invoice …
    await confirm_critical(db_session, mgr, doc_id)
    out = (await CommitService(db_session).approve(mgr, doc_id, comment="ok")).out  # … commits
    assert out.actions[0].action_name == "ACT-create_invoice"
    own_id = out.actions[0].ids[0]
    row = await db_session.get(Invoice, uuid.UUID(own_id))
    assert row is not None and row.created_by == uid  # the committer is the creator

    other = await api.call("POST", "/finance/invoices", "CFO", json={
        "client_id": str(uuid.uuid4()), "client_name": "Cty khác", "number": uuid.uuid4().hex[:8],
        "issued_on": "2043-01-05", "due_date": "2043-02-05", "status": "sent",
        "lines": [{"description": "x", "quantity": 1, "unit_price": 100}]})  # fmt: skip
    assert other.status_code == 201, other.text
    other_id = other.json()["data"]["id"]

    # list: exactly the MGR's own invoices (the seed and the CFO's invoice are not there)
    assert await _all_ids(api, "MGR", uid, dept) == {own_id}
    got = await _as(api, "GET", f"/finance/invoices/{own_id}", "MGR", uid, dept)
    assert got.status_code == 200 and got.json()["data"]["number"] == "0001234"
    assert _denied(await _as(api, "GET", f"/finance/invoices/{other_id}", "MGR", uid, dept))

    # another manager of the same department does not see it
    peer = uuid.uuid4()
    assert own_id not in await _all_ids(api, "MGR", peer, dept)
    assert _denied(await _as(api, "GET", f"/finance/invoices/{own_id}", "MGR", peer, dept))

    # writes on company invoices stay denied, own invoice included
    url = f"/finance/invoices/{own_id}"
    assert _denied(await _as(api, "PATCH", url, "MGR", uid, dept,
                             json={"notes": "x", "version": 1}))  # fmt: skip
    assert _denied(await _as(api, "DELETE", url, "MGR", uid, dept))
    pay = {"amount_paid": 10, "paid_at": "2043-01-20T00:00:00Z"}
    assert _denied(await _as(api, "POST", f"{url}/pay", "MGR", uid, dept, json=pay))

    # REV: still no general finance read
    assert _denied(await _as(api, "GET", "/finance/invoices", "REV"))
    assert _denied(await _as(api, "GET", url, "REV"))
    # unscoped roles keep the company view
    ceo = await api.call("GET", "/finance/invoices", "CEO", params={"limit": 100})
    assert ceo.json()["meta"]["pagination"]["total"] >= 2

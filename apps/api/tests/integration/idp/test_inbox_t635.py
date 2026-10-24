"""T-635 / TC-M15-18 — Data Inbox EP-DC-13 (groups, `meta.counts`, 7-role scope; ADM per
R-DEC-76) + EP-DC-14 source view (presigned 5 min, MANUAL → 422)."""

import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import select

from app.core.storage import verify_presigned
from app.modules.idp.models import DocumentType, ReviewAssignment, SourceDocument
from app.modules.platform.models import AuditLog
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration

DEPT_A, DEPT_B = uuid.uuid4(), uuid.uuid4()
U_EMP, U_MGR, U_REV, U_DIR, U_ADM = (uuid.uuid4() for _ in range(5))


async def _doc(
    db: Any, by: uuid.UUID, status: str, *, dept: uuid.UUID | None = None,
    pillars: list[str] | None = None, type_code: str | None = None,
    kind: str = "FILE", level: int = 2, name: str = "f.pdf",
) -> SourceDocument:  # fmt: skip
    type_id = None
    if type_code:
        type_id = (await db.execute(select(DocumentType.id).where(
            DocumentType.code == type_code))).scalar_one()  # fmt: skip
    d = SourceDocument(
        channel="C3" if kind == "FILE" else "C1", kind=kind, original_filename=name,
        mime_type="application/pdf", storage_key="idp/x/" + uuid.uuid4().hex if kind == "FILE"
        else None, scan_status="CLEAN", pillars=pillars or [], status=status,
        sensitivity_level=level, source="IDP", data_classification="INTERNAL", submitted_by=by,
        submitted_at=datetime.now(UTC), department_id=dept, document_type_id=type_id,
        page_count=2,
    )  # fmt: skip
    db.add(d)
    await db.flush()
    return d


async def _world(db: Any) -> dict[str, SourceDocument]:
    w = {
        "emp_review": await _doc(db, U_EMP, "NEEDS_REVIEW", dept=DEPT_A, name="hoa-don-emp.pdf"),
        "emp_fail": await _doc(db, U_EMP, "FAILED", dept=DEPT_A),
        "b_commit": await _doc(db, uuid.uuid4(), "COMMITTED", dept=DEPT_B, pillars=["F"]),
        "a_proc": await _doc(db, uuid.uuid4(), "EXTRACTING", dept=DEPT_A, pillars=["C"]),
        "assigned": await _doc(db, uuid.uuid4(), "NEEDS_REVIEW", dept=DEPT_B, pillars=["U"]),
        "adm_hr": await _doc(db, U_ADM, "VALIDATING", type_code="HR_ROSTER"),
        "adm_other": await _doc(db, U_ADM, "VALIDATING"),
    }
    db.add(ReviewAssignment(
        source_document_id=w["assigned"].id, kind="ASSIGN", to_user_id=U_REV,
        due_at=datetime.now(UTC), is_current=True,
    ))  # fmt: skip
    await db.flush()
    return w


async def _ids(api: ApiClient, role: str, **kw: Any) -> tuple[set[str], dict[str, int]]:
    params = kw.pop("params", {"limit": 100})
    h = api.headers(role, **kw)
    r = await api.http.get("/api/v1/data-capture/inbox", headers=h, params=params)
    assert r.status_code == 200, r.text
    body = r.json()
    return {x["document"]["id"] for x in body["data"]}, body["meta"]["counts"]


def _set(w: dict[str, SourceDocument], *keys: str) -> set[str]:
    return {str(w[k].id) for k in keys}


async def test_scope_by_role(api: ApiClient, db_session, idp_store) -> None:
    w = await _world(db_session)
    everything = set(_set(w, *w))
    ceo, counts = await _ids(api, "CEO")
    assert ceo == everything
    assert counts["needs_review"] == 2 and counts["processing"] == 3 and counts["failed"] == 1
    assert counts["committed"] == 1 and counts["rolled_back"] == 0
    emp, _ = await _ids(api, "EMPLOYEE", user_id=U_EMP, department_id=DEPT_A)
    assert emp == _set(w, "emp_review", "emp_fail")
    mgr, _ = await _ids(api, "MANAGER", user_id=U_MGR, department_id=DEPT_A)
    assert mgr == _set(w, "emp_review", "emp_fail", "a_proc")
    rev, _ = await _ids(api, "REVIEWER", user_id=U_REV, department_id=DEPT_A)
    assert rev == _set(w, "assigned")
    dir_f, _ = await _ids(api, "DIR", user_id=U_DIR, department_id=DEPT_A, scope_pillars=("F",))
    assert dir_f == _set(w, "b_commit")
    adm, _ = await _ids(api, "ADMIN", user_id=U_ADM)
    assert adm == _set(w, "adm_hr")  # R-DEC-76: own #4 only, no 403


async def test_filters_groups_and_counts(api: ApiClient, db_session, idp_store) -> None:
    w = await _world(db_session)
    got, counts = await _ids(api, "CEO", params={"group": "needs_review"})
    assert got == _set(w, "emp_review", "assigned")
    assert counts["failed"] == 1  # counts ignore `group`
    q, _ = await _ids(api, "CEO", params={"q": "HOA-DON"})
    assert q == _set(w, "emp_review")
    mine, _ = await _ids(api, "CEO", user_id=U_EMP, params={"mine": "true"})
    assert mine == _set(w, "emp_review", "emp_fail")
    hr, _ = await _ids(api, "CEO", params={"document_type": "HR_ROSTER", "channel": "C3"})
    assert hr == _set(w, "adm_hr")
    day = datetime.now(UTC).date().isoformat()
    dated, _ = await _ids(
        api,
        "CEO",
        params={
            "date_from": day,
            "date_to": day,
            "limit": 100,
            "sort_by": "committed_at",
            "order": "asc",
        },
    )
    assert dated == set(_set(w, *w))
    future, _ = await _ids(api, "CEO", params={"date_from": "2999-01-01"})
    assert future == set()
    bad = await api.call("GET", "/data-capture/inbox", "CEO", params={"date_from": "x"})
    assert bad.status_code == 400
    item = await api.call(
        "GET",
        "/data-capture/inbox",
        "CEO",
        params={"group": "processing", "document_type": "HR_ROSTER"},
    )
    row = item.json()["data"][0]
    assert row["document_type"] == "HR_ROSTER" and row["channel"] == "C3"
    assert row["can_undo"] is False and row["batch_id"] is None


async def test_source_view(api: ApiClient, db_session, idp_store) -> None:
    w = await _world(db_session)
    secret = await _doc(db_session, U_EMP, "COMMITTED", dept=DEPT_A, level=3)
    r = await api.call("GET", f"/data-capture/documents/{secret.id}/source", "EMPLOYEE",
                       params={"page": 2}, department_id=DEPT_B)  # fmt: skip
    assert r.status_code == 404  # another EMP of another department → not visible
    h = api.headers("EMPLOYEE", user_id=U_EMP, department_id=DEPT_A)
    ok = await api.http.get(f"/api/v1/data-capture/documents/{secret.id}/source", headers=h,
                            params={"page": 2})  # fmt: skip
    assert ok.status_code == 200, ok.text
    out = ok.json()["data"]
    assert (out["page"], out["page_count"], out["mime_type"]) == (2, 2, "application/pdf")
    url = urlparse(out["url"])
    qs = parse_qs(url.query)
    key = url.path.removeprefix("/files/")
    assert key == secret.storage_key
    assert verify_presigned(key, int(qs["expires"][0]), qs["signature"][0])
    exp = int(qs["expires"][0])
    assert not verify_presigned(key, exp, qs["signature"][0], now=exp + 1)  # 5-min TTL
    audits = (
        (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.action == "idp.source_view", AuditLog.target_id == secret.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(audits) == 1
    over = await api.http.get(f"/api/v1/data-capture/documents/{secret.id}/source", headers=h,
                              params={"page": 3})  # fmt: skip
    assert over.status_code == 400
    manual = await _doc(db_session, U_EMP, "COMMITTED", dept=DEPT_A, kind="MANUAL")
    m = await api.http.get(f"/api/v1/data-capture/documents/{manual.id}/source", headers=h)
    assert m.status_code == 422 and m.json()["error"]["details"]["reason"] == "no_file"
    rev = api.headers("REVIEWER", user_id=U_REV, department_id=DEPT_A)
    a = await api.http.get(f"/api/v1/data-capture/documents/{w['assigned'].id}/source",
                           headers=rev)  # fmt: skip
    assert a.status_code == 200  # assigned reviewer
    adm = await api.call("GET", f"/data-capture/documents/{w['adm_other'].id}/source", "ADMIN")
    assert adm.status_code == 404

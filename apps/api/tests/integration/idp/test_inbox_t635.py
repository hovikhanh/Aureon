"""T-635 / TC-M15-18 — Data Inbox EP-DC-13 (groups, `meta.counts`, 7-role scope; ADM per
R-DEC-76) + EP-DC-14 source view (presigned 5 min, MANUAL → 422).

EP-DC-14b `/files/{storage_key}` serving route (R-DEC-80, TC-SRC-01..08): signature + expiry,
invalid key / out-of-scope / cross-tenant → not served; role matrix (idp:read in scope, never
idp:approve); correct Content-Type / inline disposition / no-store / nosniff headers."""

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
        mime_type="application/pdf", storage_key=f"documents/{uuid.uuid4()}" if kind == "FILE"
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
    assert out["filename"] == secret.original_filename
    url = urlparse(out["url"])
    qs = parse_qs(url.query)
    # R-DEC-80: BFF-reachable prefix so the browser can load it through the Next proxy.
    assert url.path.startswith("/api/backend/files/")
    key = url.path.removeprefix("/api/backend/files/")
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


# ---- EP-DC-14b `/files/{storage_key}` serving route (R-DEC-80) ----------------------------
def _signed(key: str) -> str:
    """Build the BFF-reachable signed path for `key` and return the FastAPI-relative URL."""
    from app.core.storage import presign_get

    url = presign_get(key)
    return "/api/v1/files/" + url.split("/api/backend/files/", 1)[1]


async def test_serve_file_happy_path_and_headers(api, db_session, idp_store) -> None:
    import app.core.storage as storage

    _ = await _world(db_session)
    doc = await _doc(db_session, U_EMP, "COMMITTED", dept=DEPT_A, level=3, name="q3.pdf")
    # write a real file under the document's storage_key into the test's temp store
    store = storage.get_object_store()
    assert doc.storage_key is not None
    bucket, obj = doc.storage_key.split("/", 1)
    (store.root / bucket).mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]
    (store.root / bucket / obj).write_bytes(b"%PDF-1.4 fake pdf bytes")  # type: ignore[attr-defined]

    h = api.headers("EMPLOYEE", user_id=U_EMP, department_id=DEPT_A)
    r = await api.http.get(_signed(doc.storage_key), headers=h)
    assert r.status_code == 200, r.text
    assert r.content == b"%PDF-1.4 fake pdf bytes"
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.headers["content-disposition"].startswith("inline")
    assert r.headers["cache-control"] == "private, no-store"
    assert r.headers["x-content-type-options"] == "nosniff"
    # CSP sandbox keeps active content (scripts/plugins/forms/popups) blocked but allows
    # same-origin so the browser's native PDF viewer can render the file inline (not just images).
    assert r.headers["content-security-policy"] == "default-src 'none'; sandbox allow-same-origin"
    # level-3 → audited on serve as well (idempotent concept with EP-DC-14)
    audits = (
        (await db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "idp.source_view", AuditLog.target_id == doc.id
            )
        )).scalars().all()
    )  # fmt: skip
    assert len(audits) >= 1


async def test_serve_file_signature_and_expiry(api, db_session, idp_store) -> None:
    doc = await _doc(db_session, U_EMP, "COMMITTED", dept=DEPT_A, name="x.pdf")
    assert doc.storage_key is not None
    h = api.headers("EMPLOYEE", user_id=U_EMP, department_id=DEPT_A)
    signed = _signed(doc.storage_key)
    # tampered signature → 403
    bad_sig = await api.http.get(signed.split("&signature=")[0] + "&signature=deadbeef", headers=h)
    assert bad_sig.status_code == 403
    assert bad_sig.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    # expired link (expires in the past) → 403, even with a valid signature for that expiry
    from app.core.storage import presign_get

    past = presign_get(doc.storage_key, ttl=-10)
    expired = "/api/v1/files/" + past.split("/api/backend/files/", 1)[1]
    assert (await api.http.get(expired, headers=h)).status_code == 403


async def test_serve_file_invalid_key_and_scope(api, db_session, idp_store) -> None:
    w = await _world(db_session)
    h = api.headers("EMPLOYEE", user_id=U_EMP, department_id=DEPT_A)
    # traversal / malformed key → 404 (never reaches the store)
    from app.core.storage import _signature

    bogus = "documents/not-a-uuid"
    exp = 9999999999
    trav = f"/api/v1/files/{bogus}?expires={exp}&signature={_signature(bogus, exp)}"
    assert (await api.http.get(trav, headers=h)).status_code == 404
    # out-of-scope document (another department, EMP) → 404, existence not leaked
    other = w["b_commit"]
    assert other.storage_key is not None
    assert (await api.http.get(_signed(other.storage_key), headers=h)).status_code == 404


async def test_serve_file_cross_tenant(api, db_session, idp_store) -> None:
    doc = await _doc(db_session, U_EMP, "COMMITTED", dept=DEPT_A, name="t.pdf")
    assert doc.storage_key is not None
    # a correctly signed URL requested under another tenant resolves to nothing → 404
    other_tenant = uuid.UUID("00000000-0000-0000-0000-0000000000b2")
    h = api.headers("CEO", tenant_id=other_tenant)
    assert (await api.http.get(_signed(doc.storage_key), headers=h)).status_code == 404


async def test_serve_file_role_matrix(api, db_session, idp_store) -> None:
    """idp:read roles in scope can view; the route never checks idp:approve (R-DEC-80)."""
    import app.core.storage as storage

    doc = await _doc(
        db_session, uuid.uuid4(), "COMMITTED", dept=DEPT_A, pillars=["F"], name="m.pdf"
    )
    store = storage.get_object_store()
    assert doc.storage_key is not None
    bucket, obj = doc.storage_key.split("/", 1)
    (store.root / bucket).mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]
    (store.root / bucket / obj).write_bytes(b"data")  # type: ignore[attr-defined]
    signed = _signed(doc.storage_key)
    # CEO (no idp:approve) sees everything → 200
    assert (await api.http.get(signed, headers=api.headers("CEO"))).status_code == 200
    # Finance DIR in scope (F pillar) → 200
    dir_h = api.headers("DIR", user_id=U_DIR, department_id=DEPT_A, scope_pillars=("F",))
    assert (await api.http.get(signed, headers=dir_h)).status_code == 200
    # ADM (idp:read scope `s`, not this doc type) → 404, out of scope
    assert (await api.http.get(signed, headers=api.headers("ADMIN"))).status_code == 404

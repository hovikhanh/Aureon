"""HTTP-level EP-20 upload + EP-25/EP-26 read (10 §3.3). Exercises the multipart route, the
202 envelope, permission guard, and the query service with the pipeline run in-process."""

from __future__ import annotations

import uuid

import pytest

from app.modules.idp.services.pipeline import Pipeline
from tests.integration.idp import sample_docs as s
from tests.integration.idp.test_upload_and_pipeline import _InvoiceGateway

pytestmark = pytest.mark.integration


async def test_ep20_upload_returns_202_envelope(api, idp_store) -> None:
    h = api.headers("CFO", idem=True)
    resp = await api.http.post(
        "/api/v1/idp/documents",
        files=[("files", ("invoice.pdf", s.invoice_pdf(), "application/pdf"))],
        headers=h,
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert "data" in body
    assert len(body["data"]["document_ids"]) == 1
    assert len(body["data"]["job_ids"]) == 1


async def test_ep20_requires_idempotency_key(api, idp_store) -> None:
    h = api.headers("CFO")  # no Idempotency-Key
    resp = await api.http.post(
        "/api/v1/idp/documents",
        files=[("files", ("a.pdf", s.invoice_pdf(), "application/pdf"))],
        headers=h,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_REQUEST"


async def test_ep20_forbidden_without_idp_write(api, idp_store) -> None:
    # REVIEWER has idp:read + approve but not write? assert guard rejects a role lacking write.
    from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

    role = next(r for r, perms in ROLE_PERMISSIONS.items() if "idp:write" not in perms)
    h = api.headers(role, idem=True)
    resp = await api.http.post(
        "/api/v1/idp/documents",
        files=[("files", ("a.pdf", s.invoice_pdf(), "application/pdf"))],
        headers=h,
    )
    assert resp.status_code == 403


async def test_ep25_and_ep26_expose_pipeline_results(api, db_session, idp_store) -> None:
    uid = uuid.uuid4()
    h = api.headers("CFO", user_id=uid, idem=True)
    up = await api.http.post(
        "/api/v1/idp/documents",
        files=[("files", ("invoice.pdf", s.invoice_pdf(), "application/pdf"))],
        headers=h,
    )
    doc_id = up.json()["data"]["document_ids"][0]

    # run the pipeline in-process against the same rolled-back session
    await Pipeline(db_session, _InvoiceGateway()).run(uuid.UUID(doc_id))
    await db_session.flush()

    detail = await api.http.get(
        f"/api/v1/idp/documents/{doc_id}", headers=api.headers("CFO", user_id=uid)
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == "NEEDS_REVIEW"

    extraction = await api.http.get(
        f"/api/v1/idp/documents/{doc_id}/extraction", headers=api.headers("CFO", user_id=uid)
    )
    assert extraction.status_code == 200
    data = extraction.json()["data"]
    assert data["routing_decision"] == "REVIEW"
    assert len(data["fields"]) == 8


async def test_ep25_not_found(api, idp_store) -> None:
    resp = await api.http.get(f"/api/v1/idp/documents/{uuid.uuid4()}", headers=api.headers("CFO"))
    assert resp.status_code == 404


async def test_ep_dc_01_document_type_preselect(api, idp_store, db_session) -> None:
    """T-635: `document_type` preselects the type (classifier skipped); unknown → 422."""
    from sqlalchemy import select

    from app.modules.idp.models import DocumentType, SourceDocument

    h = api.headers("CFO", idem=True)
    resp = await api.http.post(
        "/api/v1/idp/documents", headers=h, data={"document_type": "PERIOD_REPORT"},
        files=[("files", ("inv-pre.pdf", s.invoice_pdf() + b"%pre", "application/pdf"))],
    )  # fmt: skip
    assert resp.status_code == 202, resp.text
    doc_id = uuid.UUID(resp.json()["data"]["document_ids"][0])
    doc = (await db_session.execute(select(SourceDocument).where(
        SourceDocument.id == doc_id))).scalar_one()  # fmt: skip
    inv = (await db_session.execute(select(DocumentType.id).where(
        DocumentType.code == "PERIOD_REPORT"))).scalar_one()  # fmt: skip
    assert doc.type_preselected is True and doc.document_type_id == inv
    bad = await api.http.post(
        "/api/v1/idp/documents", headers=api.headers("CFO", idem=True),
        data={"document_type": "NOPE"},
        files=[("files", ("x.pdf", s.invoice_pdf(), "application/pdf"))],
    )  # fmt: skip
    assert bad.status_code == 422
    assert bad.json()["error"]["details"]["fields"] == ["document_type"]

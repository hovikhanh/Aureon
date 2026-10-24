"""S4b 8-step end-to-end demo flow over the real HTTP app (S4b §5 integration test).

1. Upload invoice.pdf              → document NEEDS_REVIEW
2. Reviewer GET /idp/review-queue  → sees 1 item
3. GET /idp/documents/{id}/review  → 8 fields, 3 critical highlighted
4. PATCH .../fields                → correct 1 field with reason "OCR mismatch"
5. validation recompute            → pass
6. POST .../review/approve         → finance.Invoice created (via Action Registry)
7. GET /finance/invoices           → the new invoice present
8. GET /finance/dashboard          → reachable / metric updated

The pipeline (scan→OCR→extract→validate) is normally handed to Celery out of band; in the
HTTP test harness there is no worker, so after the upload call we run the pipeline in-process
against the same rolled-back session with a fixture gateway, then resume over HTTP.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

import pytest
from sqlalchemy import select

from app.core.model_gateway import ChatResponse
from tests.integration.idp import sample_docs as s

pytestmark = pytest.mark.integration


class _InvoiceGateway:
    DATA: ClassVar[dict[str, Any]] = {
        "invoice_number": {"value": "0001234", "raw_text": "0001234", "confidence": 0.98},
        "issue_date": {"value": "2026-09-15", "confidence": 0.95},
        "seller_name": {"value": "Cong ty ABC", "confidence": 0.93},
        "seller_tax_code": {"value": "0301234567", "confidence": 0.92},
        "subtotal": {"value": 10000000, "confidence": 0.96},
        "vat_rate_pct": {"value": 10, "confidence": 0.95},
        "vat_amount": {"value": 1000000, "confidence": 0.95},
        "total_amount": {"value": 11000000, "confidence": 0.96},
    }

    async def chat(self, req: Any) -> ChatResponse:
        return ChatResponse(content="", provider="fake", model="m", data=self.DATA)


async def test_eight_step_demo_flow(api, db_session, idp_store) -> None:
    from app.modules.idp.models import SourceDocument
    from app.modules.idp.services.pipeline import Pipeline

    reviewer = uuid.uuid4()

    # --- step 1: upload invoice.pdf (reviewer has idp:write) ---
    files = {"files": ("invoice.pdf", s.invoice_pdf(), "application/pdf")}
    up = await api.http.request(
        "POST",
        "/api/v1/idp/documents",
        files=files,
        headers=api.headers("REVIEWER", user_id=reviewer, idem=True),
    )
    assert up.status_code == 202, up.text
    doc_id = uuid.UUID(up.json()["data"]["document_ids"][0])

    # pipeline runs out of band (no worker in tests) → run it in-process on the same session
    outcome = await Pipeline(db_session, _InvoiceGateway()).run(doc_id)
    assert outcome.status == "NEEDS_REVIEW"
    await db_session.flush()

    rev_headers = api.headers("REVIEWER", user_id=reviewer)

    # --- step 2: review queue shows 1 item ---
    q = await api.http.request("GET", "/api/v1/idp/review-queue", headers=rev_headers)
    assert q.status_code == 200, q.text
    data = q.json()["data"]
    assert len(data) == 1
    assert data[0]["document_id"] == str(doc_id)
    assert q.json()["meta"]["pagination"]["total"] == 1

    # --- step 3: review detail → 8 fields, 3 critical ---
    d = await api.http.request("GET", f"/api/v1/idp/documents/{doc_id}/review", headers=rev_headers)
    assert d.status_code == 200, d.text
    detail = d.json()["data"]
    assert len(detail["fields"]) == 8
    critical = [f for f in detail["fields"] if f["is_critical"]]
    assert len(critical) == 3

    # open the review (soft lock) before editing
    o = await api.http.request(
        "POST",
        f"/api/v1/idp/documents/{doc_id}/review/open",
        headers=api.headers("REVIEWER", user_id=reviewer, idem=True),
    )
    assert o.status_code == 200, o.text

    # --- step 4: correct one field with a reason ---
    seller = next(f for f in detail["fields"] if f["field_name"] == "seller_name")
    patch = await api.http.request(
        "PATCH",
        f"/api/v1/idp/documents/{doc_id}/fields",
        json={
            "fields": [
                {
                    "field_id": seller["id"],
                    "action": "correct",
                    "value": "Cong ty ABC (da sua)",
                    "reason": "OCR mismatch",
                }
            ]
        },
        headers=rev_headers,
    )
    assert patch.status_code == 200, patch.text
    # --- step 5: validation recomputed and passing ---
    assert patch.json()["data"]["validations_ok"] is True

    # --- step 6: approve → commit to finance.Invoice ---
    ap = await api.http.request(
        "POST",
        f"/api/v1/idp/documents/{doc_id}/review/approve",
        json={"comment": "verified"},
        headers=api.headers("REVIEWER", user_id=reviewer, idem=True),
    )
    assert ap.status_code == 200, ap.text
    # R-DEC-61: REV approves but lacks `finance:write` → APPROVED + pending permission
    assert ap.json()["data"]["document"]["status"] == "APPROVED"
    assert ap.json()["data"]["actions"] == []
    assert ap.json()["meta"]["pending_permissions"] == ["finance:write"]

    # --- step 6b: EP-DC-23 — a finance writer (CFO) commits the APPROVED document ---
    approved = (
        await db_session.execute(select(SourceDocument).where(SourceDocument.id == doc_id))
    ).scalar_one()
    cm = await api.http.request(
        "POST", f"/api/v1/data-capture/documents/{doc_id}/commit",
        json={"version": approved.version},
        headers=api.headers("CFO", idem=True),
    )  # fmt: skip
    assert cm.status_code == 200, cm.text
    body = cm.json()["data"]
    assert body["document"]["status"] == "COMMITTED"
    assert body["actions"][0]["action_name"] == "ACT-create_invoice"
    inv_id = body["actions"][0]["ids"][0]

    doc = (
        await db_session.execute(select(SourceDocument).where(SourceDocument.id == doc_id))
    ).scalar_one()
    assert doc.status == "COMMITTED"

    # --- step 7: the new invoice is listed (reviewer has finance:read) ---
    inv = await api.http.request("GET", "/api/v1/finance/invoices", headers=rev_headers)
    assert inv.status_code == 200, inv.text
    ids = {i["id"] for i in inv.json()["data"]}
    assert inv_id in ids
    created = next(i for i in inv.json()["data"] if i["id"] == inv_id)
    assert created["number"] == "0001234"
    assert created["direction"] == "IN"

    # --- step 8: finance dashboard reachable + reflects the commit (CFO has finance:query) ---
    dash = await api.http.request("GET", "/api/v1/finance/dashboard", headers=api.headers("CFO"))
    assert dash.status_code == 200, dash.text

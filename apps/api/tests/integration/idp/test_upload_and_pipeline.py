"""EP-20 upload + end-to-end IDP pipeline (T-401..T-405, S4a exit criteria).

- upload accepts the four core types, rejects oversize / unsupported / too-many files;
- duplicate SHA-256 → DUPLICATE linked to the original;
- malware (EICAR) → document FAILED (status_reason=MALWARE), file quarantined;
- a clean invoice runs scan → OCR/text → extract → validate and ends NEEDS_REVIEW
  (critical fields force review), with field results persisted.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

import pytest

from app.core.model_gateway import ChatResponse
from app.modules.idp.models import DocumentPage, ExtractedField, SourceDocument
from app.modules.idp.services.pipeline import Pipeline
from app.modules.idp.services.upload_service import UploadFile, UploadService
from tests.integration.idp import sample_docs as s

pytestmark = pytest.mark.integration


def _principal(dept: uuid.UUID | None = None):
    from app.core.deps import Principal
    from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

    return Principal(
        user_id=uuid.uuid4(),
        role="DIR",
        permissions=frozenset(ROLE_PERMISSIONS["DIR"]),
        department_id=dept,
        scope_pillars=frozenset({"F"}),
    )


def _file(name: str, mime: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, content_type=mime, chunks=iter([data]))


class _InvoiceGateway:
    """Returns a full high-confidence invoice extraction for the extract task."""

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

    async def chat(self, req):
        return ChatResponse(content="", provider="fake", model="m", data=self.DATA)


# ---------------- T-401 upload ----------------
async def test_upload_four_types_creates_documents_and_jobs(db_session, idp_store) -> None:
    files = [
        _file("invoice.pdf", "application/pdf", s.invoice_pdf()),
        _file("contract.docx", "application/octet-stream", s.contract_docx()),
        _file("expenses.xlsx", "application/octet-stream", s.expenses_xlsx()),
        _file("logo.png", "image/png", s.png_image()),
    ]
    result = await UploadService(db_session).upload(_principal(), files)
    assert len(result.document_ids) == 4
    assert len(result.job_ids) == 4
    assert result.batch_id is not None  # multi-file → batch


async def test_upload_rejects_unsupported_type(db_session, idp_store) -> None:
    from app.core.errors import AppError

    with pytest.raises(AppError) as ei:
        await UploadService(db_session).upload(
            _principal(), [_file("a.exe", "application/x-dosexec", b"MZ\x90\x00bad")]
        )
    assert ei.value.code == "UNSUPPORTED_MEDIA_TYPE"


async def test_upload_rejects_oversize(db_session, idp_store, monkeypatch) -> None:
    from app.core.errors import AppError

    svc = UploadService(db_session)
    monkeypatch.setattr(svc.cfg, "idp_max_file_size_mb", 0.000001, raising=False)
    big = b"%PDF-1.4\n" + b"x" * 4096
    with pytest.raises(AppError) as ei:
        await svc.upload(_principal(), [_file("big.pdf", "application/pdf", big)])
    assert ei.value.code == "FILE_TOO_LARGE"


async def test_upload_rejects_too_many_files(db_session, idp_store, monkeypatch) -> None:
    from app.core.errors import AppError

    svc = UploadService(db_session)
    monkeypatch.setattr(svc.cfg, "idp_max_files_per_upload", 1, raising=False)
    files = [
        _file("a.pdf", "application/pdf", s.invoice_pdf()),
        _file("b.pdf", "application/pdf", s.invoice_pdf()),
    ]
    with pytest.raises(AppError) as ei:
        await svc.upload(_principal(), files)
    assert ei.value.code == "FILE_TOO_LARGE"


async def test_upload_duplicate_sha256_marks_duplicate(db_session, idp_store) -> None:
    user = _principal()
    svc = UploadService(db_session)
    r1 = await svc.upload(user, [_file("a.pdf", "application/pdf", s.invoice_pdf())])
    r2 = await svc.upload(user, [_file("a.pdf", "application/pdf", s.invoice_pdf())])
    dup = (
        (
            await db_session.execute(
                SourceDocument.__table__.select().where(SourceDocument.id == r2.document_ids[0])
            )
        )
        .mappings()
        .one()
    )
    assert dup["status"] == "DUPLICATE"
    assert dup["duplicate_of_id"] == r1.document_ids[0]
    assert r2.document_ids[0] in r2.duplicates


# ---------------- T-402 malware ----------------
async def test_pipeline_quarantines_malware(db_session, idp_store) -> None:
    user = _principal()
    r = await UploadService(db_session).upload(
        user, [_file("bad.pdf", "application/pdf", s.eicar_txt())]
    )
    outcome = await Pipeline(db_session, _InvoiceGateway()).run(r.document_ids[0])
    assert outcome.status == "FAILED"
    doc = await db_session.get(SourceDocument, r.document_ids[0])
    assert doc.scan_status == "INFECTED"
    assert doc.status_reason == "MALWARE"
    assert doc.storage_key.startswith("quarantine/")


# ---------------- T-403/404/405 full pipeline ----------------
async def test_pipeline_invoice_ends_needs_review(db_session, idp_store) -> None:
    user = _principal()
    r = await UploadService(db_session).upload(
        user, [_file("invoice.pdf", "application/pdf", s.invoice_pdf())]
    )
    outcome = await Pipeline(db_session, _InvoiceGateway()).run(r.document_ids[0])

    # critical fields (subtotal/vat/total) always force review (04 §7.3 / FR-DC-16)
    assert outcome.status == "NEEDS_REVIEW"
    assert outcome.routing_decision == "REVIEW"
    assert "CRITICAL_FIELD" in outcome.routing_reasons
    assert outcome.validation_errors == []

    pages = (
        (
            await db_session.execute(
                DocumentPage.__table__.select().where(
                    DocumentPage.source_document_id == r.document_ids[0]
                )
            )
        )
        .mappings()
        .all()
    )
    assert pages and pages[0]["text_layer_exists"]

    fields = (
        (
            await db_session.execute(
                ExtractedField.__table__.select().where(
                    ExtractedField.extraction_job_id == outcome.job_id
                )
            )
        )
        .mappings()
        .all()
    )
    by = {f["field_name"]: f for f in fields}
    assert len(by) == 8
    assert by["subtotal"]["confidence_band"] == "HIGH"
    assert by["subtotal"]["is_critical"] is True


async def test_pipeline_rejects_invalid_invoice(db_session, idp_store) -> None:
    class _BadGateway:
        async def chat(self, req):
            data = dict(_InvoiceGateway.DATA)
            data["issue_date"] = {"value": "2030-01-01", "confidence": 0.95}  # future
            data["subtotal"] = {"value": -1, "confidence": 0.95}  # ≤ 0
            return ChatResponse(content="", provider="fake", model="m", data=data)

    user = _principal()
    r = await UploadService(db_session).upload(
        user, [_file("invoice.pdf", "application/pdf", s.invoice_pdf())]
    )
    outcome = await Pipeline(db_session, _BadGateway()).run(r.document_ids[0])
    assert outcome.status == "NEEDS_REVIEW"
    codes = {e["rule"] for e in outcome.validation_errors}
    assert {"VR-INV-02", "VR-INV-SUB"} <= codes
    assert "VALIDATION_FAILED" in outcome.routing_reasons

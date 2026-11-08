"""D-11 (F-C1, F-M2) — documents are CONFIDENTIAL until classified, the type only raises the
level before extraction, and "no model may answer" is a manual-review state, not an HTTP 500."""

import io
import uuid
from typing import Any

import pytest
from sqlalchemy import select

from app.core.deps import Principal
from app.core.model_gateway import ChatRequest, ChatResponse, ModelGateway, NullSink
from app.core.model_gateway.errors import TemplateRequired
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.idp.models import ExtractedField, ExtractionJob, SourceDocument
from app.modules.idp.schemas.capture import NaturalLanguageIn
from app.modules.idp.services.natural_language import NaturalLanguageService
from app.modules.idp.services.pipeline import (
    MANUAL_LEVEL4_NO_LLM,
    MANUAL_NO_MODEL,
    MANUAL_NO_TEXT,
    Pipeline,
)
from app.modules.idp.services.upload_service import UploadFile, UploadService
from tests.integration.idp.sample_docs import invoice_pdf

pytestmark = pytest.mark.integration

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ROSTER = ["Mã NV", "Họ và tên", "Chức danh", "Mã phòng ban", "Phòng ban", "Ngày vào làm", "Lương"]


class _Gw:
    """Records every request; answers `data`, or raises `exc`."""

    def __init__(self, data: Any = None, exc: Exception | None = None) -> None:
        self.data, self.exc, self.reqs = data or {}, exc, []

    async def chat(self, req: ChatRequest) -> ChatResponse:
        self.reqs.append(req)
        if self.exc:
            raise self.exc
        return ChatResponse(content="", provider="fake", model="m", data=self.data)


def _ceo() -> Principal:
    return Principal(user_id=uuid.uuid4(), role="CEO",
                     permissions=frozenset(ROLE_PERMISSIONS["CEO"]))  # fmt: skip


def _roster_xlsx() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(ROSTER)
    ws.append(["E001", "Nguyễn Văn Thử", "Kế toán", "KT", "Kế toán", "2026-01-05", 15000000])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def _upload(db, name: str, mime: str, data: bytes, **kw: Any) -> uuid.UUID:
    up = await UploadService(db).upload(
        _ceo(), [UploadFile(filename=name, content_type=mime, chunks=iter([data]))], **kw
    )
    return up.document_ids[0]


async def _doc(db, doc_id: uuid.UUID) -> SourceDocument:
    stmt = select(SourceDocument).where(SourceDocument.id == doc_id)
    return (await db.execute(stmt)).scalar_one()


async def _job(db, doc_id: uuid.UUID) -> ExtractionJob:
    return (await db.execute(
        select(ExtractionJob).where(ExtractionJob.source_document_id == doc_id)
    )).scalar_one()  # fmt: skip


async def test_upload_defaults_to_confidential(db_session, idp_store) -> None:
    doc = await _doc(db_session, await _upload(db_session, "a.pdf", "application/pdf",
                                               invoice_pdf()))  # fmt: skip
    assert doc.sensitivity_level == 3
    assert doc.data_classification == "CONFIDENTIAL"


async def test_low_level_type_never_lowers_and_every_model_call_is_confidential(
    db_session, idp_store
) -> None:
    gw = _Gw({"invoice_number": {"value": "1", "confidence": 0.9}})
    doc_id = await _upload(db_session, "a.pdf", "application/pdf", invoice_pdf())
    out = await Pipeline(db_session, gw).run(doc_id)
    doc = await _doc(db_session, doc_id)
    assert out.document_type == "INVOICE"  # doc type level 2 …
    assert doc.sensitivity_level == 3  # … does not lower the default
    assert gw.reqs, "extraction ran"
    assert {r.classification for r in gw.reqs} == {"CONFIDENTIAL"}


async def test_legacy_level_2_document_is_raised_before_any_call(db_session, idp_store) -> None:
    gw = _Gw()
    doc_id = await _upload(db_session, "a.pdf", "application/pdf", invoice_pdf())
    doc = await _doc(db_session, doc_id)
    doc.sensitivity_level, doc.data_classification = 2, "INTERNAL"
    await db_session.flush()
    await Pipeline(db_session, gw).run(doc_id)
    assert {r.classification for r in gw.reqs} == {"CONFIDENTIAL"}


async def test_roster_is_raised_to_secret_and_no_model_reads_it(db_session, idp_store) -> None:
    sink = NullSink()
    gw = ModelGateway(sink)  # the real gateway: SECRET is decided before any provider
    doc_id = await _upload(db_session, "ds.xlsx", XLSX, _roster_xlsx())
    out = await Pipeline(db_session, gw).run(doc_id)
    doc = await _doc(db_session, doc_id)
    job = await _job(db_session, doc_id)
    assert doc.sensitivity_level == 4 and doc.data_classification == "SECRET"
    assert out.status == "NEEDS_REVIEW" and out.routing_decision == "REVIEW"
    assert MANUAL_LEVEL4_NO_LLM in out.routing_reasons
    assert job.model_provider is None
    assert [r.status for r in sink.records] == ["forbidden"]
    assert sink.records[0].task_kind == "extract"
    fields = (await db_session.execute(
        select(ExtractedField).where(ExtractedField.extraction_job_id == job.id)
    )).scalars().all()  # fmt: skip
    assert fields, "one empty field per spec, for the reviewer to fill in"
    assert all(f.value is None and float(f.confidence) == 0 for f in fields)


async def test_local_model_down_goes_to_manual_review_not_500(db_session, idp_store) -> None:
    gw = _Gw(exc=TemplateRequired("CONFIDENTIAL", "no local LLM available"))
    doc_id = await _upload(db_session, "a.pdf", "application/pdf", invoice_pdf())
    out = await Pipeline(db_session, gw).run(doc_id)
    doc = await _doc(db_session, doc_id)
    assert out.status == doc.status == "NEEDS_REVIEW"
    assert MANUAL_NO_MODEL in out.routing_reasons
    assert doc.routing_reason and MANUAL_NO_MODEL in doc.routing_reason


async def test_natural_language_survives_template_required(db_session, idp_store) -> None:
    gw = _Gw(exc=TemplateRequired("CONFIDENTIAL", "no local LLM available"))
    svc = NaturalLanguageService(db_session)
    from unittest.mock import patch

    with patch("app.modules.idp.services.natural_language.pipeline_gateway", return_value=gw):
        out = await svc.submit(_ceo(), NaturalLanguageIn(text="Chi 5 triệu mua văn phòng phẩm"))
    assert out.status == "NEEDS_REVIEW"
    assert out.document.sensitivity_level == 3


async def test_document_without_text_does_not_call_the_model(db_session, idp_store) -> None:
    gw = _Gw()
    doc_id = await _upload(db_session, "s.csv", "text/csv", b"\n")
    out = await Pipeline(db_session, gw).run(doc_id)
    assert gw.reqs == []
    assert out.status == "NEEDS_REVIEW" and MANUAL_NO_TEXT in out.routing_reasons


async def test_classification_tier_is_recorded_with_its_meaning(db_session, idp_store) -> None:
    gw = _Gw()
    doc_id = await _upload(db_session, "a.pdf", "application/pdf", invoice_pdf())
    await Pipeline(db_session, gw).run(doc_id)
    info = (await _job(db_session, doc_id)).xd_results["classification"]
    assert info["tier"] == "keyword" and info["confidence_kind"] == "heuristic"

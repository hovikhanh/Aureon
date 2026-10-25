"""TC-M15-03 — 4-tier classifier (R-DEC-65): preselected → C5 header → keywords → LLM
(`task=classify`, content in `<<<DATA…DATA>>>`, answer limited to the active set) → OTHER."""

from typing import Any

import pytest

from app.core.model_gateway import ChatRequest, ChatResponse
from app.core.model_gateway.errors import FixtureMissingError
from app.modules.idp.services.classifier import Classifier, fold, header_score
from app.modules.idp.services.schema_registry import ensure_invoice_schema

pytestmark = pytest.mark.integration

ROSTER = ["Mã NV", "Họ và tên", "Chức danh", "Mã phòng ban", "Phòng ban", "Ngày vào làm", "Lương"]
PLAN = ["Kỳ", "Người phụ trách", "Mục tiêu", "Kết quả then chốt", "Mã KPI", "Target"]


class _Gw:
    def __init__(self, data: Any = None, exc: Exception | None = None) -> None:
        self.data, self.exc, self.reqs = data, exc, []

    async def chat(self, req: ChatRequest) -> ChatResponse:
        self.reqs.append(req)
        if self.exc:
            raise self.exc
        return ChatResponse(content="", provider="fake", model="m", data=self.data)


def test_fold_and_header_score() -> None:
    assert fold("  Mã  PHÒNG ban ") == "ma phong ban"
    fields = ({"name": "a", "required": True, "header_aliases": ["Mã NV"]},
              {"name": "b", "required": True, "header_aliases": []},
              {"name": "c", "required": False, "header_aliases": ["x"]})  # fmt: skip
    assert header_score(["ma nv", "x"], fields) == 0.5
    assert header_score([], fields) == 0.0


async def test_preselected_skips_classification(db_session) -> None:
    gw = _Gw()
    r = await Classifier(db_session, gw).classify("hóa đơn GTGT", preselected="HR_ROSTER")
    assert (r.code, r.confidence, r.tier) == ("HR_ROSTER", 1.0, "preselected")
    assert gw.reqs == []


async def test_header_heuristic_routes_c5_sheets(db_session) -> None:
    c = Classifier(db_session)
    roster = await c.classify("\t".join(ROSTER), headers=ROSTER)
    assert (roster.code, roster.tier) == ("HR_ROSTER", "header") and roster.confidence >= 0.95
    plan = await c.classify("\t".join(PLAN), headers=PLAN)
    assert (plan.code, plan.tier) == ("PLAN_KPI_OKR", "header")


async def test_keywords_then_llm(db_session) -> None:
    text = "BÁO CÁO KẾT QUẢ tháng 10 — kết quả kỳ: doanh thu thực hiện 12 tỷ"
    plain = await Classifier(db_session).classify(text)
    assert (plain.code, plain.tier) == ("PERIOD_REPORT", "keyword") and plain.confidence < 0.95
    gw = _Gw({"code": "PERIOD_REPORT", "confidence": 0.97})
    llm = await Classifier(db_session, gw).classify(text)
    assert (llm.code, llm.confidence, llm.tier) == ("PERIOD_REPORT", 0.97, "llm")
    req = gw.reqs[0]
    assert req.task == "classify" and "<<<DATA" in req.messages[1].content
    assert "PERIOD_REPORT" in req.json_schema["properties"]["code"]["enum"]


async def test_llm_out_of_set_or_missing_fixture_degrades(db_session) -> None:
    text = "Ghi chú nội bộ không rõ loại"
    bogus = await Classifier(db_session, _Gw({"code": "PAYSLIP", "confidence": 0.99})).classify(
        text
    )
    assert (bogus.code, bogus.tier) == ("OTHER", "fallback") and bogus.confidence < 0.95
    gw = _Gw(exc=FixtureMissingError("no fixture"))
    missing = await Classifier(db_session, gw).classify(text)
    assert missing.code == "OTHER"
    secret = _Gw({"code": "HR_ROSTER", "confidence": 0.99})
    out = await Classifier(db_session, secret).classify(text, classification="SECRET")
    assert out.code == "OTHER" and secret.reqs == []  # Secret → no LLM


async def test_invoice_hints_still_work(db_session) -> None:
    await ensure_invoice_schema(db_session)
    r = await Classifier(db_session).classify("HÓA ĐƠN GTGT — MST 0301234567, tiền thuế VAT")
    assert r.code == "INVOICE" and r.confidence >= 0.95


async def test_pipeline_classifies_roster_sheet(db_session, idp_store) -> None:
    import io
    import uuid

    from openpyxl import Workbook
    from sqlalchemy import select

    from app.core.deps import Principal
    from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
    from app.modules.idp.models import DocumentType, SourceDocument
    from app.modules.idp.services.pipeline import Pipeline
    from app.modules.idp.services.upload_service import UploadFile, UploadService

    wb = Workbook()
    ws = wb.active
    ws.append(ROSTER)
    ws.append(["E001", "Nguyễn Văn Thử", "Kế toán", "KT", "Kế toán", "2026-01-05", 1])
    buf = io.BytesIO()
    wb.save(buf)
    user = Principal(user_id=uuid.uuid4(), role="CEO",
                     permissions=frozenset(ROLE_PERMISSIONS["CEO"]))  # fmt: skip
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    up = await UploadService(db_session).upload(
        user, [UploadFile(filename="ds.xlsx", content_type=mime, chunks=iter([buf.getvalue()]))]
    )
    out = await Pipeline(db_session, _Gw({})).run(up.document_ids[0])
    doc = (await db_session.execute(select(SourceDocument).where(
        SourceDocument.id == up.document_ids[0]))).scalar_one()  # fmt: skip
    code = (await db_session.execute(select(DocumentType.code).where(
        DocumentType.id == doc.document_type_id))).scalar_one()  # fmt: skip
    assert code == "HR_ROSTER" and float(doc.classification_confidence) >= 0.95
    assert out.status == "NEEDS_REVIEW"  # level-4/critical columns → people review


async def test_pipeline_unclear_text_goes_to_review_as_other(db_session, idp_store) -> None:
    import uuid

    from app.core.deps import Principal
    from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
    from app.modules.idp.services.pipeline import Pipeline
    from app.modules.idp.services.upload_service import UploadFile, UploadService

    user = Principal(user_id=uuid.uuid4(), role="CEO",
                     permissions=frozenset(ROLE_PERMISSIONS["CEO"]))  # fmt: skip
    from tests.integration.idp.sample_docs import contract_docx

    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    up = await UploadService(db_session).upload(
        user, [UploadFile(filename="hd.docx", content_type=mime, chunks=iter([contract_docx()]))]
    )
    out = await Pipeline(db_session, _Gw({})).run(up.document_ids[0])
    assert out.status == "NEEDS_REVIEW"
    assert "LOW_CLASSIFICATION_CONFIDENCE" in out.routing_reasons

"""Tests for Document Classification, Schema Extraction, EP-26, and EP-50 (T-207).

Implements:
- TC-IDP-009: Classification of 7 sample doc types, low-confidence routing, and EP-30.
- TC-IDP-011: Strict schema field output (value=null when missing, no hallucination;
  schema failure -> IDP-E07).
- TC-IDP-020: EP-26 GET /documents/{id}/extraction with role-based salary masking (DS3).
- TC-IDP-037: EP-50 GET /extraction-schemas permissions and field masking.
"""

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.main import app
from app.modules.auth.models import Role, User
from app.modules.auth.token import create_access_token
from app.modules.idp.enums import (
    DocType,
    DocumentKind,
    DocumentStatus,
    InputChannel,
    JobStatus,
)
from app.modules.idp.extraction import (
    classify_document,
    extract_document_fields,
)
from app.modules.idp.models import DocumentPage, ExtractedField, SourceDocument


@pytest.fixture
def app_client(db_session: Session) -> Generator[TestClient, None, None]:
    from app.db.session import get_db

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def seed_test_users(db_session: Session) -> dict[str, tuple[User, str]]:
    cfg = get_config()
    role_configs = [
        ("ROLE-01", ["FIN", "CUS", "OPS", "HR"]),
        ("ROLE-02", ["FIN"]),
        ("ROLE-03", ["CUS"]),
        ("ROLE-04", ["HR"]),
        ("ROLE-05", ["FIN", "CUS", "OPS", "HR"]),
    ]
    result: dict[str, tuple[User, str]] = {}
    for role_code, pillars in role_configs:
        email = f"{role_code.lower()}_t207@abc.demo"
        user = db_session.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        ).scalar_one_or_none()
        if not user:
            role = db_session.execute(
                select(Role).where(Role.code == role_code)
            ).scalar_one_or_none()
            if not role:
                role = Role(
                    code=role_code,
                    name_i18n_key=f"shell.roles.{role_code}",
                    pillar_scope=pillars,
                    pillar_agg_scope=[],
                    review_pillars=pillars,
                    home_route="/dashboard",
                )
                db_session.add(role)
                db_session.flush()
            user = User(
                email=email,
                password_hash="$fake_hash",
                full_name=f"User {role_code}",
                salutation="anh",
                role_id=role.id,
                is_demo_account=True,
            )
            db_session.add(user)
            db_session.flush()

        token, _ = create_access_token(user, cfg)
        result[role_code] = (user, token)

    return result


def create_document_with_text(
    db: Session,
    uploader_id: Any,
    text_content: str,
    filename: str = "test.pdf",
    doc_type: DocType | None = None,
    pillars: list[str] | None = None,
) -> SourceDocument:
    doc = SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename=filename,
        mime_type="application/pdf",
        size_bytes=len(text_content.encode("utf-8")),
        page_count=1,
        doc_type=doc_type,
        pillars=pillars or ["FIN"],
        status=DocumentStatus.CLASSIFYING,
        uploaded_by_id=uploader_id,
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    db.flush()

    page = DocumentPage(
        id=uuid4(),
        source_document_id=doc.id,
        page_number=1,
        text_layer_exists=True,
        text_layer_quality=1.0,
        ocr_used=False,
        text_content=text_content,
        width_px=800,
        height_px=1100,
    )
    db.add(page)
    db.commit()
    db.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# TC-IDP-009: Classification of 7 doc types + Confidence routing + EP-30
# ---------------------------------------------------------------------------


def test_tc_idp_009_classify_7_sample_documents(
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-009 Part 1: Correctly classifies all 7 sample documents with confidence >= 0.80."""
    uploader, _ = seed_test_users["ROLE-01"]

    samples = [
        (
            DocType.FINANCIAL_REPORT,
            "BÁO CÁO TÀI CHÍNH QUÝ 3/2026 - Công ty TNHH TM&DV ABC. "
            "Bảng cân đối kế toán, kết quả kinh doanh. Doanh thu thuần 24.500.000.000 đ",
            "bctc_q3.pdf",
        ),
        (
            DocType.INVOICE,
            "HÓA ĐƠN GIÁ TRỊ GIA TĂNG (VAT INVOICE) Số 0012345. "
            "Thuế suất 10%, tiền thuế GTGT 2.500.000 đ, tổng tiền thanh toán 27.500.000 đ",
            "invoice_t9.pdf",
        ),
        (
            DocType.SALES_REPORT,
            "BÁO CÁO SALES THÁNG 9/2026 - Pipeline coverage 0.77x. "
            "Deals won: 12, deals lost: 38. Doanh thu theo khách hàng. NPS score +32",
            "sales_report.pdf",
        ),
        (
            DocType.CONTRACT,
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM. HỢP ĐỒNG KINH TẾ Số HD-2026-001. "
            "Bên A: Công ty ABC. Bên B: Công ty Giáo dục VN. Giá trị hợp đồng: 5.000.000.000 đ",
            "contract_001.pdf",
        ),
        (
            DocType.MEETING_MINUTES,
            "BIÊN BẢN HỌP GIAO BAN TUẦN 1 T9/2026. "
            "Chủ trì: Ông Nguyễn Văn An. Action items và kết luận cuộc họp",
            "minutes_w1.docx",
        ),
        (
            DocType.EMPLOYEE_LIST,
            "DANH SÁCH NHÂN SỰ VÀ BẢNG LƯƠNG CÔNG TY ABC T9/2026. "
            "Mã nhân viên NV001, họ và tên Trần Thị Minh, chức danh CFO, lương cơ bản 45.000.000 đ",
            "employee_list.xlsx",
        ),
        (
            DocType.KPI_OKR,
            "KẾ HOẠCH MỤC TIÊU KPI/OKR QUÝ 4/2026. "
            "Chỉ số đo lường METRIC-FIN-01, target value 27.000.000.000 đ. Key result",
            "kpi_okr_q4.docx",
        ),
    ]

    for expected_type, text_cue, filename in samples:
        doc = create_document_with_text(db_session, uploader.id, text_cue, filename=filename)
        detected_type, confidence = classify_document(db_session, doc.id)

        assert detected_type == expected_type, f"Failed on {filename}"
        assert confidence >= 0.80, f"Confidence too low: {confidence}"
        assert doc.status == DocumentStatus.EXTRACTING


def test_tc_idp_009_low_confidence_routes_to_needs_review(
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-009 Part 2: Low confidence (< 0.80) routes document to NEEDS_REVIEW."""
    uploader, _ = seed_test_users["ROLE-01"]
    ambiguous_text = "Văn bản chung chung mơ hồ ambiguous không rõ nội dung gì cụ thể cả."

    doc = create_document_with_text(db_session, uploader.id, ambiguous_text, filename="vague.pdf")
    _detected_type, confidence = classify_document(db_session, doc.id)

    assert confidence < 0.80
    assert doc.status == DocumentStatus.NEEDS_REVIEW
    assert doc.status_reason is not None
    assert "< 0.80" in doc.status_reason


def test_tc_idp_009_ep30_change_doc_type_and_reextract(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-009 Part 3: EP-30 changes doc_type and re-extracts schema fields."""
    reviewer, token_reviewer = seed_test_users["ROLE-05"]

    # Create an initial document classified as CONTRACT
    initial_text = "Hợp đồng số HD-001. Công ty ABC và khách hàng Minh Phát."
    doc = create_document_with_text(
        db_session, reviewer.id, initial_text, filename="change_type.pdf"
    )
    classify_document(db_session, doc.id)
    extract_document_fields(db_session, doc.id)

    # Verify initial fields belong to CONTRACT
    stmt = select(ExtractedField).where(ExtractedField.source_document_id == doc.id)
    fields = db_session.execute(stmt).scalars().all()
    keys = {f.field_key for f in fields}
    assert "contract_number" in keys

    # Call EP-30 to change doc_type to INVOICE
    response = app_client.patch(
        f"/api/v1/documents/{doc.id}/fields",
        headers={
            "Authorization": f"Bearer {token_reviewer}",
            "Idempotency-Key": str(uuid4()),
        },
        json={"doc_type": "INVOICE"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    assert data["document"]["doc_type"] == "INVOICE"
    field_keys = {f["field_key"] for f in data["fields"]}
    assert "invoice_number" in field_keys
    assert "contract_number" not in field_keys


# ---------------------------------------------------------------------------
# TC-IDP-011: Strict schema extraction & Schema violation failure
# ---------------------------------------------------------------------------


def test_tc_idp_011_extraction_returns_every_field_and_null_when_missing(
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-011 Part 1: All schema fields returned; absent fields have value=null."""
    uploader, _ = seed_test_users["ROLE-01"]
    partial_text = "HÓA ĐƠN GTGT Số HD-778899. Tổng tiền thanh toán: 15.000.000 đ"
    doc = create_document_with_text(
        db_session, uploader.id, partial_text, filename="partial_inv.pdf", doc_type=DocType.INVOICE
    )

    job = extract_document_fields(db_session, doc.id)
    assert job.status == JobStatus.SUCCEEDED

    stmt = select(ExtractedField).where(ExtractedField.extraction_job_id == job.id)
    fields = db_session.execute(stmt).scalars().all()
    field_map = {f.field_key: f for f in fields}

    # Present fields
    assert "invoice_number" in field_map
    assert field_map["invoice_number"].value == "HD-778899"
    assert field_map["invoice_number"].confidence >= 0.90
    assert field_map["invoice_number"].source_location["kind"] == "pdf_region"

    # Absent fields must be None, NOT hallucinated
    assert "seller_tax_code" in field_map
    assert field_map["seller_tax_code"].value is None
    assert field_map["seller_tax_code"].raw_text is None
    assert field_map["seller_tax_code"].confidence == 0.50
    assert field_map["seller_tax_code"].source_location["kind"] == "pdf_region"


def test_tc_idp_011_schema_violation_failure_idp_e07(
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-011 Part 2: Simulated corrupted model output fails with IDP-E07 after retry."""
    uploader, _ = seed_test_users["ROLE-01"]
    doc = create_document_with_text(
        db_session,
        uploader.id,
        "Corrupted content",
        filename="corrupted.pdf",
        doc_type=DocType.INVOICE,
    )

    job = extract_document_fields(db_session, doc.id, simulate_schema_error=True)
    assert job.status == JobStatus.FAILED
    assert job.error_code == "IDP-E07"
    assert doc.status == DocumentStatus.FAILED
    assert "IDP-E07" in (doc.status_reason or "")


# ---------------------------------------------------------------------------
# TC-IDP-020: EP-26 Extraction Results & Salary Masking (DS3)
# ---------------------------------------------------------------------------


def test_tc_idp_020_ep26_conflict_state_when_no_job(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-020 Part 1: Calling EP-26 before SUCCEEDED job returns 409 CONFLICT_STATE."""
    reviewer, token_reviewer = seed_test_users["ROLE-05"]
    doc = create_document_with_text(db_session, reviewer.id, "Empty doc", filename="no_job.pdf")

    res = app_client.get(
        f"/api/v1/documents/{doc.id}/extraction",
        headers={"Authorization": f"Bearer {token_reviewer}"},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "CONFLICT_STATE"


def test_tc_idp_020_ep26_role_forbidden(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-020 Part 2: ROLE-03 (Sales Director) is forbidden from calling EP-26 (403)."""
    _, token_sales = seed_test_users["ROLE-03"]
    uploader, _ = seed_test_users["ROLE-01"]
    doc = create_document_with_text(
        db_session, uploader.id, "Content", filename="doc_sales.pdf", doc_type=DocType.INVOICE
    )
    extract_document_fields(db_session, doc.id)

    res = app_client.get(
        f"/api/v1/documents/{doc.id}/extraction",
        headers={"Authorization": f"Bearer {token_sales}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_tc_idp_020_ep26_salary_masking_rules(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-020 Part 3: Salary masking per role on EMPLOYEE_LIST (DS3).

    - ROLE-04 (HR) sees full salary.
    - ROLE-01 (CEO) sees masked salary (masked: true, value=null).
    - ROLE-05 (Reviewer) sees masked salary when NOT locked in review.
    - ROLE-05 sees full salary when actively locked in review.
    """
    reviewer, token_reviewer = seed_test_users["ROLE-05"]
    _hr, token_hr = seed_test_users["ROLE-04"]
    _, token_ceo = seed_test_users["ROLE-01"]

    emp_text = "DANH SÁCH NHÂN SỰ T9/2026. Mã NV: NV001, Họ tên: Trần Thị Minh, Lương: 45.000.000 đ"
    doc = create_document_with_text(
        db_session,
        reviewer.id,
        emp_text,
        filename="staff.xlsx",
        doc_type=DocType.EMPLOYEE_LIST,
        pillars=["HR"],
    )
    extract_document_fields(db_session, doc.id)

    # 1. HR Manager (ROLE-04) sees full salary
    res_hr = app_client.get(
        f"/api/v1/documents/{doc.id}/extraction",
        headers={"Authorization": f"Bearer {token_hr}"},
    )
    assert res_hr.status_code == 200, res_hr.text
    fields_hr = {f["field_key"]: f for f in res_hr.json()["data"]["fields"]}
    assert fields_hr["salary"]["masked"] is False
    assert fields_hr["salary"]["value"] == 45000000

    # 2. CEO (ROLE-01) sees masked salary
    res_ceo = app_client.get(
        f"/api/v1/documents/{doc.id}/extraction",
        headers={"Authorization": f"Bearer {token_ceo}"},
    )
    assert res_ceo.status_code == 200, res_ceo.text
    fields_ceo = {f["field_key"]: f for f in res_ceo.json()["data"]["fields"]}
    assert fields_ceo["salary"]["masked"] is True
    assert fields_ceo["salary"]["value"] is None
    assert fields_ceo["salary"]["raw_text"] is None
    assert fields_ceo["salary"]["source_location"] is None

    # 3. Reviewer (ROLE-05) when NOT in review lock sees masked salary
    res_rev_unlocked = app_client.get(
        f"/api/v1/documents/{doc.id}/extraction",
        headers={"Authorization": f"Bearer {token_reviewer}"},
    )
    assert res_rev_unlocked.status_code == 200
    fields_rev = {f["field_key"]: f for f in res_rev_unlocked.json()["data"]["fields"]}
    assert fields_rev["salary"]["masked"] is True
    assert fields_rev["salary"]["value"] is None

    # 4. Reviewer (ROLE-05) when document is IN_REVIEW locked by reviewer sees full salary
    doc.status = DocumentStatus.IN_REVIEW
    doc.locked_by_id = reviewer.id
    db_session.commit()

    res_rev_locked = app_client.get(
        f"/api/v1/documents/{doc.id}/extraction",
        headers={"Authorization": f"Bearer {token_reviewer}"},
    )
    assert res_rev_locked.status_code == 200
    fields_rev_locked = {f["field_key"]: f for f in res_rev_locked.json()["data"]["fields"]}
    assert fields_rev_locked["salary"]["masked"] is False
    assert fields_rev_locked["salary"]["value"] == 45000000


# ---------------------------------------------------------------------------
# TC-IDP-037: EP-50 Extraction Schema Access Control
# ---------------------------------------------------------------------------


def test_tc_idp_037_ep50_schema_permissions_and_masking(
    app_client: TestClient,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-037: EP-50 schema query rules and field filtering.

    - ROLE-05 without doc_type returns all 7 schemas with salary included.
    - ROLE-01..04 without doc_type returns 400 BAD_REQUEST.
    - ROLE-01..04 with doc_type=EMPLOYEE_LIST filters out sensitivity=SALARY field.
    """
    _, token_ceo = seed_test_users["ROLE-01"]
    _, token_cfo = seed_test_users["ROLE-02"]
    _, token_reviewer = seed_test_users["ROLE-05"]

    # 1. ROLE-05 without doc_type -> all 7 schemas
    res_rev = app_client.get(
        "/api/v1/extraction-schemas",
        headers={"Authorization": f"Bearer {token_reviewer}"},
    )
    assert res_rev.status_code == 200
    schemas = res_rev.json()["data"]
    assert len(schemas) == 7
    # Verify salary exists in EMPLOYEE_LIST for reviewer
    emp_schema = next(s for s in schemas if s["doc_type"] == "EMPLOYEE_LIST")
    emp_keys = [f["field_key"] for f in emp_schema["fields"]]
    assert "salary" in emp_keys

    # 2. ROLE-01 and ROLE-02 without doc_type -> 400 BAD_REQUEST
    res_bad = app_client.get(
        "/api/v1/extraction-schemas",
        headers={"Authorization": f"Bearer {token_ceo}"},
    )
    assert res_bad.status_code == 400
    assert res_bad.json()["error"]["code"] == "BAD_REQUEST"

    res_cfo_bad = app_client.get(
        "/api/v1/extraction-schemas",
        headers={"Authorization": f"Bearer {token_cfo}"},
    )
    assert res_cfo_bad.status_code == 400

    # 3. ROLE-01 with doc_type=EMPLOYEE_LIST -> salary field is excluded/hidden
    res_ceo_emp = app_client.get(
        "/api/v1/extraction-schemas?doc_type=EMPLOYEE_LIST",
        headers={"Authorization": f"Bearer {token_ceo}"},
    )
    assert res_ceo_emp.status_code == 200
    ceo_emp_data = res_ceo_emp.json()["data"]
    assert len(ceo_emp_data) == 1
    assert ceo_emp_data[0]["field_set_version"] == "1.0.0"
    ceo_keys = [f["field_key"] for f in ceo_emp_data[0]["fields"]]
    assert "salary" not in ceo_keys
    assert "employee_code" in ceo_keys

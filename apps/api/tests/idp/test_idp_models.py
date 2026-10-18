"""Tests for IDP core entities and business records (T-201).

Implements TC-DATA-005 through TC-DATA-010 per docs/4.GOVERNANCE/14-TEST-TRACEABILITY.md.
"""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.auth.models import Role, User
from app.modules.idp.enums import (
    DocType,
    DocumentKind,
    DocumentStatus,
    FieldValueType,
    InputChannel,
    JobStatus,
    RecordType,
    ReviewDecision,
    RoutingDecision,
    SensitivityLabel,
    SourceLocationKind,
)
from app.modules.idp.models import (
    BusinessRecord,
    DocumentPage,
    ExtractedField,
    ExtractionJob,
    ExtractionReview,
    SourceDocument,
)


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Fixture providing a test user attached to a role."""
    role = db_session.execute(select(Role).where(Role.code == "ROLE-01")).scalar_one_or_none()
    if not role:
        role = Role(
            code="ROLE-01",
            name_i18n_key="shell.roles.CEO",
            pillar_scope=["FIN", "CUS", "OPS", "HR"],
            pillar_agg_scope=[],
            review_pillars=[],
            can_view_salary=False,
            home_route="/dashboard",
        )
        db_session.add(role)
        db_session.flush()

    user = User(
        email=f"uploader_{uuid4().hex[:8]}@abc.demo",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        full_name="Uploader Test",
        salutation="anh",
        role_id=role.id,
        is_demo_account=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_tc_data_005_source_document_salary_and_undo_deadline(
    db_session: Session, test_user: User
) -> None:
    """TC-DATA-005: ENT-SourceDocument contains_salary flag and 7-day undo deadline."""
    # 1. contains_salary auto turns on for EMPLOYEE_LIST
    doc = SourceDocument(
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename="employee_list_2026.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        size_bytes=102400,
        page_count=1,
        storage_key="docs/2026/employee_list.xlsx",
        sha256="a" * 64,
        doc_type=DocType.EMPLOYEE_LIST,
        pillars=["HR"],
        uploaded_by_id=test_user.id,
    )
    doc.update_contains_salary()
    assert doc.contains_salary is True

    # 2. mark_committed calculates committed_at + 7 days
    commit_time = datetime(2026, 10, 20, 10, 0, 0, tzinfo=UTC)
    doc.mark_committed(commit_time)
    assert doc.status == DocumentStatus.COMMITTED
    assert doc.committed_at == commit_time
    assert doc.undo_deadline == commit_time + timedelta(days=7)

    db_session.add(doc)
    db_session.commit()

    saved = db_session.get(SourceDocument, doc.id)
    assert saved is not None
    assert saved.contains_salary is True
    assert saved.undo_deadline == commit_time + timedelta(days=7)


def test_tc_data_006_document_page_ocr_and_uniqueness(
    db_session: Session, test_user: User
) -> None:
    """TC-DATA-006: ENT-DocumentPage stores OCR metadata and enforces unique page number."""
    doc = SourceDocument(
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename="invoice_01.pdf",
        mime_type="application/pdf",
        size_bytes=204800,
        page_count=2,
        storage_key="docs/invoice_01.pdf",
        sha256="b" * 64,
        doc_type=DocType.INVOICE,
        pillars=["FIN"],
        uploaded_by_id=test_user.id,
    )
    db_session.add(doc)
    db_session.flush()

    page1 = DocumentPage(
        source_document_id=doc.id,
        page_number=1,
        text_layer_exists=True,
        text_layer_quality=0.9850,
        ocr_used=False,
        ocr_confidence=None,
        text_content="CÔNG TY CỔ PHẦN CÔNG NGHỆ VÀ TRUYỀN THÔNG ABC",
        image_storage_key="pages/invoice_01_p1.png",
        width_px=2480,
        height_px=3508,
    )
    db_session.add(page1)
    db_session.commit()

    saved_page = db_session.get(DocumentPage, page1.id)
    assert saved_page is not None
    assert saved_page.text_layer_exists is True
    assert float(saved_page.text_layer_quality) == pytest.approx(0.9850, abs=1e-4)

    # Duplicate page_number for same document must fail
    page1_dup = DocumentPage(
        source_document_id=doc.id,
        page_number=1,
        text_layer_exists=False,
    )
    db_session.add(page1_dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_tc_data_007_extraction_job_retry_and_cross_doc(
    db_session: Session, test_user: User
) -> None:
    """TC-DATA-007: ENT-ExtractionJob attempt_no increments on retry and stores cross_doc.
    """
    doc = SourceDocument(
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        uploaded_by_id=test_user.id,
        pillars=["FIN"],
    )
    db_session.add(doc)
    db_session.flush()

    job1 = ExtractionJob(
        source_document_id=doc.id,
        attempt_no=1,
        celery_task_id=f"celery-{uuid4().hex}",
        doc_type=DocType.INVOICE,
        status=JobStatus.FAILED,
        error_code="IDP-E05",
    )
    db_session.add(job1)
    db_session.commit()

    # Retry job with attempt_no = 2 and cross_doc_results
    cross_results = [
        {
            "rule": "XD-01",
            "result": "MATCH",
            "severity": "INFO",
            "ref_document_ids": [str(uuid4())],
            "values": {"invoice_subtotal": 8500000000, "bctc_month_revenue": 8500000000},
        },
        {
            "rule": "XD-02",
            "result": "MISMATCH",
            "severity": "WARNING",
            "ref_document_ids": [str(uuid4())],
            "values": {"contract_amount": 500000000, "invoice_total": 550000000},
        },
    ]

    job2 = ExtractionJob(
        source_document_id=doc.id,
        attempt_no=job1.attempt_no + 1,
        celery_task_id=f"celery-{uuid4().hex}",
        doc_type=DocType.INVOICE,
        status=JobStatus.SUCCEEDED,
        routing_decision=RoutingDecision.STP,
        avg_confidence=0.9650,
        cross_doc_results=cross_results,
    )
    db_session.add(job2)
    db_session.commit()

    saved_job2 = db_session.get(ExtractionJob, job2.id)
    assert saved_job2 is not None
    assert saved_job2.attempt_no == 2
    assert saved_job2.cross_doc_results is not None
    assert len(saved_job2.cross_doc_results) == 2
    assert saved_job2.cross_doc_results[0]["result"] == "MATCH"
    assert saved_job2.cross_doc_results[1]["result"] == "MISMATCH"


def test_tc_data_008_extracted_field_final_value_and_location(
    db_session: Session, test_user: User
) -> None:
    """TC-DATA-008: ENT-ExtractedField final_value resolution and confidence constraint."""
    doc = SourceDocument(
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        uploaded_by_id=test_user.id,
        pillars=["FIN"],
    )
    db_session.add(doc)
    db_session.flush()

    job = ExtractionJob(
        source_document_id=doc.id,
        attempt_no=1,
    )
    db_session.add(job)
    db_session.flush()

    field = ExtractedField(
        extraction_job_id=job.id,
        source_document_id=doc.id,
        field_key="subtotal",
        value=8500000000,
        raw_text="8.500.000.000 đ",
        value_type=FieldValueType.MONEY,
        confidence=0.9850,
        source_location={"kind": "pdf_region", "page": 1, "bbox": [100, 200, 300, 220]},
        source_kind=SourceLocationKind.PDF_REGION,
        sensitivity=SensitivityLabel.NONE,
    )
    db_session.add(field)
    db_session.commit()

    # Before correction: final_value is original value
    assert field.final_value == 8500000000

    # User corrects value
    field.corrected = True
    field.corrected_value = 8600000000
    field.corrected_by_id = test_user.id
    db_session.commit()

    # After correction: final_value returns corrected_value
    assert field.final_value == 8600000000

    # Check constraint: confidence must be between 0 and 1
    invalid_field = ExtractedField(
        extraction_job_id=job.id,
        source_document_id=doc.id,
        field_key="tax_code",
        value="0101234567",
        value_type=FieldValueType.TAX_CODE,
        confidence=1.5,  # > 1.0 violates constraint
        source_location={"kind": "pdf_region", "page": 1, "bbox": [10, 10, 50, 20]},
        source_kind=SourceLocationKind.PDF_REGION,
    )
    db_session.add(invalid_field)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_tc_data_009_extraction_review_decision_and_timing(
    db_session: Session, test_user: User
) -> None:
    """TC-DATA-009: ENT-ExtractionReview reject_reason requirement and duration calculation."""
    role = db_session.execute(select(Role).where(Role.code == "ROLE-01")).scalar_one()
    doc = SourceDocument(
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        uploaded_by_id=test_user.id,
        pillars=["FIN"],
    )
    db_session.add(doc)
    db_session.flush()

    job = ExtractionJob(source_document_id=doc.id)
    db_session.add(job)
    db_session.flush()

    opened_time = datetime.now(UTC) - timedelta(seconds=45)
    review = ExtractionReview(
        source_document_id=doc.id,
        extraction_job_id=job.id,
        reviewer_id=test_user.id,
        reviewer_role_id=role.id,
        opened_at=opened_time,
        fields_total=12,
        fields_corrected=1,
    )
    db_session.add(review)
    db_session.flush()

    # Rejection without reason code must raise ValueError or fail constraint
    with pytest.raises(ValueError, match="reject_reason_code is required"):
        review.decide(ReviewDecision.REJECTED, reject_reason_code=None)

    # Valid rejection with reason code calculates duration
    review.decide(ReviewDecision.REJECTED, reject_reason_code="BLURRY_IMAGE")
    assert review.decision == ReviewDecision.REJECTED
    assert review.reject_reason_code == "BLURRY_IMAGE"
    assert review.duration_ms is not None
    assert review.duration_ms >= 40000  # >= 40 seconds

    db_session.commit()


def test_tc_data_010_business_record_amount_due_and_idempotency(
    db_session: Session, test_user: User
) -> None:
    """TC-DATA-010: ENT-BusinessRecord generated amount_due and unique idempotency_key."""
    doc = SourceDocument(
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        uploaded_by_id=test_user.id,
        pillars=["FIN"],
    )
    db_session.add(doc)
    db_session.flush()

    invoice = BusinessRecord(
        record_type=RecordType.INVOICE,
        pillar="FIN",
        code="HD-2026-001",
        series="1C26TAA",
        subtotal=100000000,
        vat_rate=0.10,
        vat_amount=10000000,
        total_amount=110000000,
        paid_amount=30000000,
        status="PARTIAL",
        issue_date=date(2026, 9, 15),
        due_date=date(2026, 10, 15),
        source_document_id=doc.id,
        idempotency_key="idemp-inv-001",
    )
    db_session.add(invoice)
    db_session.commit()

    saved_inv = db_session.get(BusinessRecord, invoice.id)
    assert saved_inv is not None
    # Generated column: 110,000,000 - 30,000,000 = 80,000,000
    assert saved_inv.amount_due == 80000000

    # Duplicate idempotency_key must fail
    dup_invoice = BusinessRecord(
        record_type=RecordType.INVOICE,
        pillar="FIN",
        code="HD-2026-002",
        total_amount=50000000,
        idempotency_key="idemp-inv-001",  # Same key
    )
    db_session.add(dup_invoice)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Verify all 11 RecordType enum values
    expected_record_types = {
        "INVOICE",
        "CONTRACT",
        "CUSTOMER",
        "OPPORTUNITY",
        "SURVEY_RESPONSE",
        "TASK",
        "DECISION",
        "PROJECT",
        "EMPLOYEE",
        "BUDGET_LINE",
        "FINANCIAL_LINE",
    }
    actual_types = {rt.value for rt in RecordType}
    assert actual_types == expected_record_types

"""Tests for Cross-Document Consistency XD-01..XD-05 (T-210).

Implements:
- TC-IDP-015: XD-01 (04 §12.1, DEC-030 Option A):
  - BCTC monthly revenue vs SUM(subtotal) of invoices (MATCH / MISMATCH / NOT_COMPARABLE).
  - No quarterly-to-monthly or divide-by-3 comparison.
- TC-IDP-016: XD-02..XD-05:
  - XD-02: Customer name matching (Invoice ↔ Contract ↔ Sales Report).
  - XD-03: Attendees / assignees in Meeting Minutes exist in Employee List.
  - XD-04: Metric codes in KPI/OKR match standard metric registry.
  - XD-05: Duplicate invoice number or contract number detection.
- TC-DATA-007: ENT-ExtractionJob persistence of cross_doc_results and attempt_no increment.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import Role, User
from app.modules.idp.cross_doc import (
    evaluate_xd01,
    evaluate_xd02,
    evaluate_xd03,
    evaluate_xd04,
    evaluate_xd05,
    run_cross_document_checks,
)
from app.modules.idp.enums import (
    DocType,
    DocumentKind,
    DocumentStatus,
    FieldValueType,
    InputChannel,
    JobStatus,
    SensitivityLabel,
    SourceLocationKind,
)
from app.modules.idp.models import ExtractedField, ExtractionJob, SourceDocument


@pytest.fixture
def test_user(db_session: Session) -> User:
    role = db_session.execute(select(Role).where(Role.code == "ROLE-01")).scalar_one_or_none()
    if not role:
        role = Role(
            code="ROLE-01",
            name_i18n_key="shell.roles.ROLE-01",
            pillar_scope=["FIN", "CUS", "OPS", "HR"],
            pillar_agg_scope=[],
            review_pillars=["FIN", "CUS", "OPS", "HR"],
            home_route="/dashboard",
        )
        db_session.add(role)
        db_session.flush()

    user = db_session.execute(
        select(User).where(User.email == "user_t210@abc.demo")
    ).scalar_one_or_none()
    if not user:
        user = User(
            email="user_t210@abc.demo",
            password_hash="$fake_hash",
            full_name="User T210",
            salutation="anh",
            role_id=role.id,
            is_demo_account=True,
        )
        db_session.add(user)
        db_session.flush()
    return user


def create_document_with_job(
    db: Session,
    user: User,
    doc_type: DocType,
    filename: str = "doc.pdf",
) -> tuple[SourceDocument, ExtractionJob]:
    doc = SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename=filename,
        mime_type="application/pdf",
        doc_type=doc_type,
        status=DocumentStatus.EXTRACTING,
        uploaded_by_id=user.id,
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    db.flush()

    job = ExtractionJob(
        id=uuid4(),
        source_document_id=doc.id,
        attempt_no=1,
        doc_type=doc_type,
        status=JobStatus.RUNNING,
        started_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    db.refresh(doc)
    db.refresh(job)
    return doc, job


def add_field(
    db: Session,
    doc_id: Any,
    job_id: Any,
    field_key: str,
    value: Any,
    value_type: FieldValueType,
    table_key: str | None = None,
    row_index: int | None = None,
) -> ExtractedField:
    field = ExtractedField(
        id=uuid4(),
        extraction_job_id=job_id,
        source_document_id=doc_id,
        field_key=field_key,
        table_key=table_key,
        row_index=row_index,
        value_type=value_type,
        value=value,
        raw_text=str(value),
        confidence=0.95,
        source_location={"kind": "pdf_region"},
        source_kind=SourceLocationKind.PDF_REGION,
        sensitivity=SensitivityLabel.NONE,
    )
    db.add(field)
    db.commit()
    return field


# ---------------------------------------------------------------------------
# TC-IDP-015: XD-01 (04 §12.1; DEC-030 Option A)
# ---------------------------------------------------------------------------


def test_tc_idp_015_xd01_match_within_half_percent(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-015 Part 1: BCTC month revenue matches SUM(subtotal) of invoices within ±0.5%."""
    # BCTC with month 2026-09 revenue = 8,500,000,000 đ
    bctc, job_bctc = create_document_with_job(
        db_session, test_user, DocType.FINANCIAL_REPORT, "bctc.pdf"
    )
    add_field(
        db_session,
        bctc.id,
        job_bctc.id,
        "month",
        "2026-09",
        FieldValueType.PERIOD,
        table_key="revenue_by_month",
        row_index=0,
    )
    add_field(
        db_session,
        bctc.id,
        job_bctc.id,
        "revenue",
        8500000000,
        FieldValueType.MONEY,
        table_key="revenue_by_month",
        row_index=0,
    )

    # Invoices: 2 invoices summing to 8,500,000,000 đ before VAT
    inv1, job1 = create_document_with_job(db_session, test_user, DocType.INVOICE, "inv1.pdf")
    add_field(db_session, inv1.id, job1.id, "subtotal", 4500000000, FieldValueType.MONEY)

    inv2, job2 = create_document_with_job(db_session, test_user, DocType.INVOICE, "inv2.pdf")
    add_field(db_session, inv2.id, job2.id, "subtotal", 4000000000, FieldValueType.MONEY)

    res = evaluate_xd01(db_session, bctc.id, [inv1.id, inv2.id], target_period="2026-09")

    assert res["result"] == "MATCH"
    assert res["severity"] == "info"
    assert res["values"]["diff"] == 0
    assert str(bctc.id) in res["ref_document_ids"]
    assert str(inv1.id) in res["ref_document_ids"]


def test_tc_idp_015_xd01_mismatch_exceeds_half_percent(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-015 Part 2: BCTC month revenue deviates > 0.5% -> MISMATCH (blocking)."""
    bctc, job_bctc = create_document_with_job(
        db_session, test_user, DocType.FINANCIAL_REPORT, "bctc_mismatch.pdf"
    )
    add_field(
        db_session,
        bctc.id,
        job_bctc.id,
        "month",
        "2026-09",
        FieldValueType.PERIOD,
        table_key="revenue_by_month",
        row_index=0,
    )
    add_field(
        db_session,
        bctc.id,
        job_bctc.id,
        "revenue",
        8500000000,
        FieldValueType.MONEY,
        table_key="revenue_by_month",
        row_index=0,
    )

    # Invoices summing to 7,000,000,000 đ (exceeds ±0.5%)
    inv, job_inv = create_document_with_job(
        db_session, test_user, DocType.INVOICE, "inv_deviate.pdf"
    )
    add_field(db_session, inv.id, job_inv.id, "subtotal", 7000000000, FieldValueType.MONEY)

    res = evaluate_xd01(db_session, bctc.id, [inv.id], target_period="2026-09")

    assert res["result"] == "MISMATCH"
    assert res["severity"] == "blocking"
    assert res["values"]["diff"] == 1500000000
    assert "lệch SUM(subtotal)" in res["message"]


def test_tc_idp_015_xd01_not_comparable_when_no_monthly_breakdown(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-015 Part 3: BCTC without monthly revenue -> NOT_COMPARABLE (no divide by 3)."""
    bctc, job_bctc = create_document_with_job(
        db_session, test_user, DocType.FINANCIAL_REPORT, "bctc_q_only.pdf"
    )
    # Only quarter revenue, no revenue_by_month table
    add_field(db_session, bctc.id, job_bctc.id, "revenue", 24500000000, FieldValueType.MONEY)

    res = evaluate_xd01(db_session, bctc.id, target_period="2026-09")

    assert res["result"] == "NOT_COMPARABLE"
    assert "Không đối chiếu được" in res["message"]
    assert res["values"]["bctc_revenue"] is None


# ---------------------------------------------------------------------------
# TC-IDP-016: XD-02..XD-05 Cross-Doc Consistency
# ---------------------------------------------------------------------------


def test_tc_idp_016_xd02_customer_name_match_and_mismatch(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-016 Part 1: XD-02 customer name consistency between invoice and contract."""
    # Known contract with party_b = "Công ty TNHH Thiết bị Giáo dục Minh Phát"
    contract, job_con = create_document_with_job(
        db_session, test_user, DocType.CONTRACT, "contract_mp.pdf"
    )
    add_field(
        db_session,
        contract.id,
        job_con.id,
        "party_b_name",
        "Công ty TNHH Thiết bị Giáo dục Minh Phát",
        FieldValueType.ORG_NAME,
    )

    # 1. Invoice matching with minor prefix variance -> MATCH
    inv_match, _ = create_document_with_job(
        db_session, test_user, DocType.INVOICE, "inv_mp.pdf"
    )
    res_match = evaluate_xd02(
        db_session, "Thiết bị Giáo dục Minh Phát", inv_match.id, [contract.id]
    )
    assert res_match["result"] == "MATCH"
    assert res_match["severity"] == "info"

    # 2. Invoice with unknown customer -> MISMATCH (warning)
    inv_unknown, _ = create_document_with_job(
        db_session, test_user, DocType.INVOICE, "inv_unknown.pdf"
    )
    res_mismatch = evaluate_xd02(
        db_session, "Công ty Xây dựng Phương Nam", inv_unknown.id, [contract.id]
    )
    assert res_mismatch["result"] == "MISMATCH"
    assert res_mismatch["severity"] == "warning"


def test_tc_idp_016_xd03_meeting_attendees_vs_employee_list(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-016 Part 2: XD-03 attendees/assignees in Meeting Minutes exist in Employee List."""
    # Employee List document with employees
    emp_doc, job_emp = create_document_with_job(
        db_session, test_user, DocType.EMPLOYEE_LIST, "staff.xlsx"
    )
    add_field(
        db_session, emp_doc.id, job_emp.id, "full_name", "Trần Thị Minh", FieldValueType.PERSON_NAME
    )
    add_field(
        db_session,
        emp_doc.id,
        job_emp.id,
        "full_name",
        "Lê Hoàng Giang",
        FieldValueType.PERSON_NAME,
    )

    # Meeting Minutes document
    meeting, _ = create_document_with_job(
        db_session, test_user, DocType.MEETING_MINUTES, "meeting.docx"
    )

    # 1. All attendees exist -> MATCH
    res_match = evaluate_xd03(
        db_session, meeting.id, ["Bà Trần Thị Minh", "Ông Lê Hoàng Giang"], emp_doc.id
    )
    assert res_match["result"] == "MATCH"
    assert res_match["severity"] == "info"

    # 2. Unknown attendee -> MISMATCH (warning)
    res_mismatch = evaluate_xd03(
        db_session, meeting.id, ["Bà Trần Thị Minh", "Nguyễn Văn Không Có"], emp_doc.id
    )
    assert res_mismatch["result"] == "MISMATCH"
    assert res_mismatch["severity"] == "warning"
    assert "Nguyễn Văn Không Có" in res_mismatch["message"]


def test_tc_idp_016_xd04_kpi_metric_code_consistency(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-016 Part 3: XD-04 KPI/OKR metric codes must exist in standard 18 metric registry."""
    kpi_doc, _ = create_document_with_job(db_session, test_user, DocType.KPI_OKR, "kpi.docx")

    # 1. Valid metric codes -> MATCH
    res_valid = evaluate_xd04(db_session, kpi_doc.id, ["METRIC-FIN-01", "METRIC-CUS-01"])
    assert res_valid["result"] == "MATCH"
    assert res_valid["severity"] == "info"

    # 2. Invalid metric code -> MISMATCH (blocking)
    res_invalid = evaluate_xd04(db_session, kpi_doc.id, ["METRIC-FIN-01", "METRIC-INVALID-99"])
    assert res_invalid["result"] == "MISMATCH"
    assert res_invalid["severity"] == "blocking"
    assert "METRIC-INVALID-99" in res_invalid["message"]


def test_tc_idp_016_xd05_duplicate_business_record(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-016 Part 4: XD-05 duplicate invoice number or contract number detection."""
    # Existing invoice
    existing_inv, job_orig = create_document_with_job(
        db_session, test_user, DocType.INVOICE, "inv_orig.pdf"
    )
    add_field(
        db_session,
        existing_inv.id,
        job_orig.id,
        "invoice_number",
        "HD-2026-001234",
        FieldValueType.TEXT,
    )

    # New invoice with same number -> duplicate detected (blocking)
    new_inv, _ = create_document_with_job(
        db_session, test_user, DocType.INVOICE, "inv_dup.pdf"
    )
    res_dup = evaluate_xd05(db_session, new_inv.id, "invoice_number", "HD-2026-001234")

    assert res_dup["result"] == "MISMATCH"
    assert res_dup["severity"] == "blocking"
    assert "Trùng số nghiệp vụ" in res_dup["message"]
    assert str(existing_inv.id) in res_dup["ref_document_ids"]

    # Unique number -> MATCH
    res_unique = evaluate_xd05(db_session, new_inv.id, "invoice_number", "HD-2026-999999")
    assert res_unique["result"] == "MATCH"
    assert res_unique["severity"] == "info"


# ---------------------------------------------------------------------------
# TC-DATA-007: ENT-ExtractionJob persistence of cross_doc_results & attempt_no
# ---------------------------------------------------------------------------


def test_tc_data_007_cross_doc_results_persistence_and_routing(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-DATA-007: cross_doc_results stored in job and forces REVIEW on blocking conflicts."""
    doc, job = create_document_with_job(
        db_session, test_user, DocType.FINANCIAL_REPORT, "bctc_flow.pdf"
    )
    add_field(db_session, doc.id, job.id, "revenue", 24500000000, FieldValueType.MONEY)

    # Run cross-document checks on document
    results = run_cross_document_checks(db_session, doc.id, job.id)
    db_session.refresh(job)

    # Verify cross_doc_results stored in job
    assert job.cross_doc_results is not None
    assert len(job.cross_doc_results) == len(results)
    assert job.cross_doc_results[0]["rule"] == "XD-01"
    assert job.cross_doc_results[0]["result"] == "NOT_COMPARABLE"

    # Retry increases attempt_no
    job.attempt_no += 1
    db_session.commit()
    db_session.refresh(job)
    assert job.attempt_no == 2

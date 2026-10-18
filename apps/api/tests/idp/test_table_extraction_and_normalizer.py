"""Tests for Table Extraction and Vietnamese Data Normalization (T-208).

Implements:
- TC-IDP-012: Table extraction: line items, action items, employee list, revenue_by_month.
- TC-IDP-013: VN normalization (date, money, percent, period, tax_code) preserving raw_text.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import Role, User
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
from app.modules.idp.models import ExtractionJob, SourceDocument
from app.modules.idp.normalizer import (
    normalize_date,
    normalize_field_value,
    normalize_money,
    normalize_percent,
    normalize_period,
    normalize_tax_code,
)
from app.modules.idp.table_extractor import extract_table_rows


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
        select(User).where(User.email == "user_t208@abc.demo")
    ).scalar_one_or_none()
    if not user:
        user = User(
            email="user_t208@abc.demo",
            password_hash="$fake_hash",
            full_name="User T208",
            salutation="anh",
            role_id=role.id,
            is_demo_account=True,
        )
        db_session.add(user)
        db_session.flush()
    return user


def create_job_fixture(
    db: Session, user: User, doc_type: DocType
) -> tuple[SourceDocument, ExtractionJob]:
    doc = SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename="doc_table.pdf",
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
    return doc, job


# ---------------------------------------------------------------------------
# TC-IDP-013: Vietnamese Data Normalizer (P04, FR-DC-12)
# ---------------------------------------------------------------------------


def test_tc_idp_013_date_normalization() -> None:
    """TC-IDP-013 Part 1: Date normalizer accepts VN formats and outputs ISO YYYY-MM-DD."""
    assert normalize_date("05/10/2026") == "2026-10-05"
    assert normalize_date("5/10/2026") == "2026-10-05"
    assert normalize_date("05-10-2026") == "2026-10-05"
    assert normalize_date("ngày 5 tháng 10 năm 2026") == "2026-10-05"
    assert normalize_date("ngày 05 tháng 10 năm 2026") == "2026-10-05"
    assert normalize_date("2026-10-05") == "2026-10-05"
    assert normalize_date("invalid_date") is None


def test_tc_idp_013_money_normalization() -> None:
    """TC-IDP-013 Part 2: Money normalizer handles VND integers, tỷ, triệu, and abbreviations."""
    assert normalize_money("1.250.000 đ") == 1250000
    assert normalize_money("1.250.000") == 1250000
    assert normalize_money("1,2 tỷ") == 1200000000
    assert normalize_money("1.2 tỷ") == 1200000000
    assert normalize_money("850 tr") == 850000000
    assert normalize_money("1,25 triệu") == 1250000
    assert normalize_money(25000000) == 25000000


def test_tc_idp_013_percent_normalization() -> None:
    """TC-IDP-013 Part 3: Percent normalizer outputs decimal floats."""
    assert normalize_percent("12,5%") == 0.125
    assert normalize_percent("12.5%") == 0.125
    assert normalize_percent("10%") == 0.10
    assert normalize_percent("8%") == 0.08
    assert normalize_percent("0%") == 0.0
    assert normalize_percent(0.125) == 0.125


def test_tc_idp_013_period_normalization() -> None:
    """TC-IDP-013 Part 4: Period normalizer handles YYYY-MM and YYYY-Qn."""
    assert normalize_period("T9/2026") == "2026-09"
    assert normalize_period("Tháng 9/2026") == "2026-09"
    assert normalize_period("Tháng 09/2026") == "2026-09"
    assert normalize_period("2026-09") == "2026-09"
    assert normalize_period("Q3/2026") == "2026-Q3"
    assert normalize_period("Quý 3/2026") == "2026-Q3"
    assert normalize_period("Quý III/2026") == "2026-Q3"
    assert normalize_period("2026-Q3") == "2026-Q3"


def test_tc_idp_013_tax_code_normalization() -> None:
    """TC-IDP-013 Part 5: Tax code normalizer accepts 10 or 13 digits."""
    assert normalize_tax_code("0301234567") == "0301234567"
    assert normalize_tax_code("0101234567-001") == "0101234567-001"
    assert normalize_tax_code("0101234567001") == "0101234567-001"
    assert normalize_tax_code("12345") is None


def test_tc_idp_013_raw_text_preservation() -> None:
    """TC-IDP-013 Part 6: normalize_field_value preserves raw_text alongside normalized value."""
    val, raw = normalize_field_value(FieldValueType.MONEY, "1.250.000 đ")
    assert val == 1250000
    assert raw == "1.250.000 đ"

    val_d, raw_d = normalize_field_value(FieldValueType.DATE, "05/10/2026")
    assert val_d == "2026-10-05"
    assert raw_d == "05/10/2026"

    val_p, raw_p = normalize_field_value(FieldValueType.PERIOD, "T9/2026")
    assert val_p == "2026-09"
    assert raw_p == "T9/2026"


# ---------------------------------------------------------------------------
# TC-IDP-012: Table Extraction (FR-DC-11)
# ---------------------------------------------------------------------------


def test_tc_idp_012_extract_invoice_line_items(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-012 Part 1: Extract line_items with row_index and normalized cells."""
    doc, job = create_job_fixture(db_session, test_user, DocType.INVOICE)

    raw_items = [
        {
            "description": "Giấy in A4 Double A 70gsm",
            "quantity": "50",
            "unit_price": "65.000 đ",
            "amount": "3.250.000 đ",
        },
        {
            "description": "Bút bi Thiên Long 0.5mm",
            "quantity": "200",
            "unit_price": "4.500 đ",
            "amount": "900.000 đ",
        },
    ]

    records = extract_table_rows(
        db=db_session,
        doc_id=doc.id,
        job_id=job.id,
        table_key="line_items",
        raw_rows=raw_items,
        source_kind=SourceLocationKind.CELL,
    )

    assert len(records) == 8  # 2 rows x 4 columns

    # Check row 0
    row0_fields = [r for r in records if r.row_index == 0]
    assert len(row0_fields) == 4
    row0_map = {r.field_key: r for r in row0_fields}

    assert row0_map["description"].value == "Giấy in A4 Double A 70gsm"
    assert row0_map["quantity"].value == 50
    assert row0_map["unit_price"].value == 65000
    assert row0_map["unit_price"].raw_text == "65.000 đ"
    assert row0_map["amount"].value == 3250000
    assert row0_map["amount"].source_location["kind"] == "cell"
    assert row0_map["amount"].source_location["row"] == 1


def test_tc_idp_012_extract_meeting_action_items(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-012 Part 2: Extract action_items from meeting minutes."""
    doc, job = create_job_fixture(db_session, test_user, DocType.MEETING_MINUTES)

    action_items = [
        {
            "title": "Bổ sung hồ sơ vay vốn VCB",
            "assignee": "Bà Trần Thị Minh",
            "due_date": "15/10/2026",
            "status": "IN_PROGRESS",
        },
        {
            "title": "Tuyển dụng 3 nhân viên kinh doanh",
            "assignee": "Cô Phạm Thị Hạnh",
            "due_date": "20/10/2026",
            "status": "TODO",
        },
    ]

    records = extract_table_rows(
        db=db_session,
        doc_id=doc.id,
        job_id=job.id,
        table_key="action_items",
        raw_rows=action_items,
    )

    assert len(records) == 8
    row0_map = {r.field_key: r for r in records if r.row_index == 0}
    assert row0_map["due_date"].value == "2026-10-15"
    assert row0_map["due_date"].raw_text == "15/10/2026"
    assert row0_map["assignee"].value == "Bà Trần Thị Minh"


def test_tc_idp_012_extract_employee_list_with_salary(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-012 Part 3: Extract employee list rows with salary marked as SALARY sensitivity."""
    doc, job = create_job_fixture(db_session, test_user, DocType.EMPLOYEE_LIST)

    employees = [
        {
            "employee_code": "NV001",
            "full_name": "Trần Thị Minh",
            "title": "CFO",
            "department": "Tài chính",
            "start_date": "01/03/2020",
            "status": "ACTIVE",
            "salary": "45.000.000 đ",
        },
        {
            "employee_code": "NV002",
            "full_name": "Lê Hoàng Giang",
            "title": "Sales Director",
            "department": "Kinh doanh",
            "start_date": "15/06/2021",
            "status": "ACTIVE",
            "salary": "40.000.000 đ",
        },
    ]

    records = extract_table_rows(
        db=db_session,
        doc_id=doc.id,
        job_id=job.id,
        table_key="employees",
        raw_rows=employees,
    )

    assert len(records) == 14  # 2 rows x 7 columns
    salary_fields = [r for r in records if r.field_key == "salary"]
    assert len(salary_fields) == 2
    for s_field in salary_fields:
        assert s_field.sensitivity == SensitivityLabel.SALARY
        assert s_field.value in (45000000, 40000000)


def test_tc_idp_012_extract_financial_revenue_by_month(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-012 Part 4: Extract revenue_by_month rows for financial reports."""
    doc, job = create_job_fixture(db_session, test_user, DocType.FINANCIAL_REPORT)

    months_data = [
        {"month": "T7/2026", "revenue": "8.100.000.000 đ"},
        {"month": "T8/2026", "revenue": "8.200.000.000 đ"},
        {"month": "T9/2026", "revenue": "8.200.000.000 đ"},
    ]

    records = extract_table_rows(
        db=db_session,
        doc_id=doc.id,
        job_id=job.id,
        table_key="revenue_by_month",
        raw_rows=months_data,
    )

    assert len(records) == 6  # 3 rows x 2 columns
    for idx, expected_month, expected_rev in [
        (0, "2026-07", 8100000000),
        (1, "2026-08", 8200000000),
        (2, "2026-09", 8200000000),
    ]:
        row_fields = {r.field_key: r for r in records if r.row_index == idx}
        assert row_fields["month"].value == expected_month
        assert row_fields["revenue"].value == expected_rev

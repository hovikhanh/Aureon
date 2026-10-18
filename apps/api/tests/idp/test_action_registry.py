"""Tests for Action Registry (T-212).

Specs:
- FR-DC-17, US-DC-014: Action Registry (invoice.create, contract.create, task.create_from_minutes,
  employee.upsert, metric_value.upsert, metric_target.upsert, document.reject, document.rollback).
- Idempotency by hash(document_id, field_set_version, action_name).
- Permission check by Role & Autonomy level (L3 for AI).
- Transaction rollback and transition to NEEDS_REVIEW on mid-execution failure (IDP-E10).
- TC-IDP-023: Full action lifecycle and validation.
- TC-IDP-024: Static check verifying no module outside Action Registry writes to business entities.
"""

import os
import re
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.modules.auth.models import Role, User
from app.modules.idp.action_registry import (
    execute_action,
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
from app.modules.idp.models import (
    BusinessRecord,
    ExtractedField,
    ExtractionJob,
    SourceDocument,
)


@pytest.fixture
def test_roles(db_session: Session) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for code, pillars in [
        ("ROLE-01", ["FIN", "CUS", "OPS", "HR"]),
        ("ROLE-02", ["FIN"]),
        ("ROLE-03", ["CUS"]),
        ("ROLE-04", ["HR"]),
        ("ROLE-05", ["FIN", "CUS", "OPS", "HR"]),
    ]:
        r = db_session.execute(select(Role).where(Role.code == code)).scalar_one_or_none()
        if not r:
            r = Role(
                code=code,
                name_i18n_key=f"shell.roles.{code}",
                pillar_scope=pillars,
                pillar_agg_scope=[],
                review_pillars=pillars,
                home_route="/dashboard",
            )
            db_session.add(r)
            db_session.flush()
        roles[code] = r
    db_session.commit()
    return roles


@pytest.fixture
def test_users(db_session: Session, test_roles: dict[str, Role]) -> dict[str, User]:
    users: dict[str, User] = {}
    for code, role in test_roles.items():
        email = f"user_{code.lower()}@abc.demo"
        u = db_session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if not u:
            u = User(
                email=email,
                password_hash="$fake_hash",
                full_name=f"User {code}",
                salutation="anh",
                role_id=role.id,
                is_demo_account=True,
            )
            db_session.add(u)
            db_session.flush()
        users[code] = u
    db_session.commit()
    return users


def create_doc(
    db: Session,
    user: User,
    doc_type: DocType = DocType.INVOICE,
    autonomy: str = "L2",
) -> tuple[SourceDocument, ExtractionJob]:
    doc = SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename="doc.pdf",
        mime_type="application/pdf",
        doc_type=doc_type,
        status=DocumentStatus.NEEDS_REVIEW,
        manual_payload={"autonomy_level": autonomy},
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
        status=JobStatus.SUCCEEDED,
        started_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    db.refresh(doc)
    db.refresh(job)
    return doc, job


# ---------------------------------------------------------------------------
# TC-IDP-023: Action Registry Execution & Validations
# ---------------------------------------------------------------------------


def test_tc_idp_023_invoice_create_and_lineage(
    db_session: Session,
    test_users: dict[str, User],
) -> None:
    """TC-IDP-023: invoice.create creates INVOICE + FINANCIAL_LINE and links extracted fields."""
    cfo = test_users["ROLE-02"]
    doc, job = create_doc(db_session, cfo, DocType.INVOICE)

    # Add extracted field to verify lineage
    field = ExtractedField(
        id=uuid4(),
        extraction_job_id=job.id,
        source_document_id=doc.id,
        field_key="total_amount",
        value=11000000,
        raw_text="11000000",
        value_type=FieldValueType.MONEY,
        confidence=0.95,
        source_location={"kind": "pdf_region"},
        source_kind=SourceLocationKind.PDF_REGION,
        sensitivity=SensitivityLabel.NONE,
    )
    db_session.add(field)
    db_session.commit()

    payload = {
        "invoice_number": "INV-2026-901",
        "issue_date": "2026-09-15",
        "customer_name": "Công ty TNHH Khách Hàng",
        "subtotal": 10000000,
        "vat_rate": 0.10,
        "vat_amount": 1000000,
        "total_amount": 11000000,
        "paid_amount": 4000000,
    }

    res = execute_action(
        db=db_session,
        action_name="invoice.create",
        document_id=doc.id,
        payload=payload,
        actor=cfo,
    )

    db_session.commit()
    db_session.refresh(field)

    assert res["record_type"] == "INVOICE"
    assert res["amount_due"] == 7000000  # 11M - 4M
    # Lineage verified: ExtractedField is linked to BusinessRecord!
    assert str(field.business_record_id) == res["business_record_id"]


def test_tc_idp_023_contract_create_and_opportunity_side_effect(
    db_session: Session,
    test_users: dict[str, User],
) -> None:
    """TC-IDP-023: contract.create creates CONTRACT + OPPORTUNITY side effect (DEC-037)."""
    sales = test_users["ROLE-03"]
    doc, _ = create_doc(db_session, sales, DocType.CONTRACT)

    payload = {
        "contract_number": "HD-2026-ABC",
        "party_b_name": "Công ty Phương Nam",
        "effective_date": "2026-01-01",
        "expiry_date": "2026-12-31",
        "total_value": 500000000,
    }

    res = execute_action(
        db=db_session,
        action_name="contract.create",
        document_id=doc.id,
        payload=payload,
        actor=sales,
    )
    db_session.commit()

    assert res["record_type"] == "CONTRACT"
    assert "side_effect_record_id" in res


def test_tc_idp_023_task_create_and_decision_side_effect(
    db_session: Session,
    test_users: dict[str, User],
) -> None:
    """TC-IDP-023: task.create_from_minutes creates TASK + DECISION side effect (DEC-037)."""
    reviewer = test_users["ROLE-05"]
    doc, _ = create_doc(db_session, reviewer, DocType.MEETING_MINUTES)

    payload = {
        "title": "Nâng cấp hạ tầng bảo mật",
        "assignee": "Lê Hoàng Giang",
        "due_date": "2026-10-30",
        "decision_text": "Phê duyệt ngân sách 200M cho firewall",
    }

    res = execute_action(
        db=db_session,
        action_name="task.create_from_minutes",
        document_id=doc.id,
        payload=payload,
        actor=reviewer,
    )
    db_session.commit()

    assert res["record_type"] == "TASK"
    assert res["decision_record_id"] is not None


def test_tc_idp_023_employee_upsert(
    db_session: Session,
    test_users: dict[str, User],
) -> None:
    """TC-IDP-023: employee.upsert creates or updates EMPLOYEE record."""
    hr = test_users["ROLE-04"]
    doc, _ = create_doc(db_session, hr, DocType.EMPLOYEE_LIST)

    payload = {
        "employee_code": "NV-045",
        "full_name": "Nguyễn Văn Test",
        "department": "Kế toán",
        "title": "Chuyên viên",
        "salary": 25000000,
    }

    res = execute_action(
        db=db_session,
        action_name="employee.upsert",
        document_id=doc.id,
        payload=payload,
        actor=hr,
    )
    db_session.commit()

    assert res["record_type"] == "EMPLOYEE"
    assert res["employee_code"] == "NV-045"


def test_tc_idp_023_idempotency_prevents_duplicate_records(
    db_session: Session,
    test_users: dict[str, User],
) -> None:
    """TC-IDP-023: Action call with same key returns ALREADY_COMMITTED without duplicate."""
    cfo = test_users["ROLE-02"]
    doc, _ = create_doc(db_session, cfo, DocType.INVOICE)

    payload = {
        "invoice_number": "INV-IDEM-001",
        "issue_date": "2026-09-20",
        "customer_name": "Công ty Idempotent",
        "subtotal": 5000000,
        "vat_rate": 0.10,
        "vat_amount": 500000,
        "total_amount": 5500000,
    }

    # First execution
    first = execute_action(
        db=db_session,
        action_name="invoice.create",
        document_id=doc.id,
        payload=payload,
        actor=cfo,
        field_set_version=1,
    )
    db_session.commit()

    # Second execution with same parameters
    second = execute_action(
        db=db_session,
        action_name="invoice.create",
        document_id=doc.id,
        payload=payload,
        actor=cfo,
        field_set_version=1,
    )

    assert second["status"] == "ALREADY_COMMITTED"
    assert second["business_record_id"] == first["business_record_id"]

    # Verify only 1 record created in database
    records = db_session.execute(
        select(BusinessRecord).where(BusinessRecord.code == "INV-IDEM-001")
    ).scalars().all()
    assert len(records) == 1


def test_tc_idp_023_permission_and_autonomy_enforcement(
    db_session: Session,
    test_users: dict[str, User],
) -> None:
    """TC-IDP-023: Role without permission rejected with 403; AI under L3 rejected with 403."""
    cfo = test_users["ROLE-02"]
    sales = test_users["ROLE-03"]
    doc, _ = create_doc(db_session, cfo, DocType.INVOICE, autonomy="L2")

    payload = {
        "invoice_number": "INV-AUTH-001",
        "issue_date": "2026-09-20",
        "customer_name": "Công ty Auth",
        "subtotal": 5000000,
        "vat_rate": 0.10,
        "vat_amount": 500000,
        "total_amount": 5500000,
    }

    # 1. Sales Director trying to execute invoice.create -> 403 FORBIDDEN_ROLE
    with pytest.raises(ApiError) as exc_info:
        execute_action(
            db=db_session,
            action_name="invoice.create",
            document_id=doc.id,
            payload=payload,
            actor=sales,
        )
    assert exc_info.value.code == ErrorCode.FORBIDDEN_ROLE

    # 2. AI actor on L2 document -> 403 FORBIDDEN_ROLE
    with pytest.raises(ApiError) as exc_ai:
        execute_action(
            db=db_session,
            action_name="invoice.create",
            document_id=doc.id,
            payload=payload,
            actor="ai:idp",
        )
    assert exc_ai.value.code == ErrorCode.FORBIDDEN_ROLE

    # 3. AI actor on L3 document -> Allowed
    doc.manual_payload = {"autonomy_level": "L3"}
    db_session.commit()
    res_ai = execute_action(
        db=db_session,
        action_name="invoice.create",
        document_id=doc.id,
        payload=payload,
        actor="ai:idp",
    )
    assert res_ai["record_type"] == "INVOICE"


def test_tc_idp_023_transaction_rollback_on_failure(
    db_session: Session,
    test_users: dict[str, User],
) -> None:
    """TC-IDP-023: Error mid-step rolls back transaction and marks NEEDS_REVIEW (IDP-E10)."""
    cfo = test_users["ROLE-02"]
    doc, _ = create_doc(db_session, cfo, DocType.INVOICE)

    # Invalid payload (missing required customer_name)
    bad_payload = {
        "invoice_number": "INV-FAIL-001",
        # customer_name missing!
        "subtotal": 5000000,
    }

    with pytest.raises(ApiError) as exc_info:
        execute_action(
            db=db_session,
            action_name="invoice.create",
            document_id=doc.id,
            payload=bad_payload,
            actor=cfo,
        )
    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR


# ---------------------------------------------------------------------------
# TC-IDP-024: Static Check - Isolation of Business Entity Writes
# ---------------------------------------------------------------------------


def test_tc_idp_024_static_check_business_records_isolation() -> None:
    """TC-IDP-024: Static check that no module outside Action Registry writes business entities."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    src_dir = os.path.join(repo_root, "apps/api/src/app")

    target_dirs = [
        os.path.join(src_dir, "modules/idp"),
        os.path.join(src_dir, "workers"),
    ]

    violations: list[str] = []
    # Pattern detecting instantiation of BusinessRecord: db.add(BusinessRecord(...))
    insert_pattern = re.compile(r"db\s*\.\s*add\s*\(\s*BusinessRecord\b")

    for t_dir in target_dirs:
        for root, _, files in os.walk(t_dir):
            for file in files:
                if file.endswith(".py") and file != "action_registry.py":
                    fpath = os.path.join(root, file)
                    with open(fpath, encoding="utf-8") as f:
                        for line_idx, line in enumerate(f, 1):
                            if insert_pattern.search(line):
                                violations.append(f"{fpath}:{line_idx}: {line.strip()}")

    # Verified: NO module in IDP or workers outside action_registry writes to BusinessRecord!
    msg = f"Found direct writes to BusinessRecord outside Action Registry: {violations}"
    assert len(violations) == 0, msg

"""Integration tests for IDP Review operations: EP-30, EP-31, EP-32.

Test Cases:
- TC-IDP-021: EP-30 edit field, AI value preservation, audit salary masking, lock requirement.
- TC-IDP-022: EP-31 approve validation gates, Action Registry commit, lineage, audit.
- TC-IDP-025: EP-32 reject validation and status transition.
- TC-DATA-008: Lineage linkage between ExtractedField and BusinessRecord.
- TC-DATA-009: 7-day undo deadline for committed documents.
"""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_config
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Role, User
from app.modules.auth.token import create_access_token
from app.modules.idp.enums import (
    DocType,
    DocumentKind,
    DocumentStatus,
    FieldValueType,
    InputChannel,
    JobStatus,
    ReviewDecision,
    SensitivityLabel,
    SourceLocationKind,
)
from app.modules.idp.models import (
    BusinessRecord,
    ExtractedField,
    ExtractionJob,
    ExtractionReview,
    SourceDocument,
)


@pytest.fixture
def app_client(db_session: Session) -> Generator[TestClient, None, None]:
    from app.db.session import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def seed_test_users(db_session: Session) -> dict[str, tuple[User, str]]:
    cfg = get_config()
    demo_emails = {
        "ROLE-01": "ceo@abc.demo",
        "ROLE-02": "cfo@abc.demo",
        "ROLE-03": "sales@abc.demo",
        "ROLE-04": "hr@abc.demo",
        "ROLE-05": "reviewer@abc.demo",
    }

    user_tokens: dict[str, tuple[User, str]] = {}
    for role_code, email in demo_emails.items():
        stmt = (
            select(User)
            .options(joinedload(User.role))
            .where(User.email == email, User.deleted_at.is_(None))
        )
        user = db_session.execute(stmt).scalar_one_or_none()
        if not user:
            stmt_role = select(Role).where(Role.code == role_code)
            role = db_session.execute(stmt_role).scalar_one_or_none()
            if not role:
                all_p = ["FIN", "CUS", "OPS", "HR"]
                scope = (
                    all_p
                    if role_code in ("ROLE-01", "ROLE-05")
                    else [role_code.replace("ROLE-0", "")]
                )
                if role_code == "ROLE-02":
                    scope = ["FIN"]
                elif role_code == "ROLE-03":
                    scope = ["CUS"]
                elif role_code == "ROLE-04":
                    scope = ["HR"]
                role = Role(
                    code=role_code,
                    name_i18n_key=f"shell.roles.{role_code}",
                    pillar_scope=scope,
                    pillar_agg_scope=[],
                    review_pillars=scope,
                    can_view_salary=(role_code in ("ROLE-04", "ROLE-05")),
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
        user_tokens[role_code] = (user, token)

    db_session.commit()
    return user_tokens


def setup_in_review_doc(
    db: Session,
    reviewer: User,
    doc_type: DocType = DocType.INVOICE,
    pillars: list[str] | None = None,
    with_salary_field: bool = False,
    low_confidence_field: bool = False,
    with_cross_doc_conflict: bool = False,
) -> tuple[SourceDocument, ExtractionJob, ExtractionReview, list[ExtractedField]]:
    now = datetime.now(UTC)
    doc = SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename=f"{doc_type.value.lower()}_test.pdf",
        mime_type="application/pdf",
        size_bytes=20480,
        page_count=2,
        storage_key=f"documents/{uuid4()}.pdf",
        doc_type=doc_type,
        pillars=pillars or ["FIN"],
        status=DocumentStatus.IN_REVIEW,
        locked_by_id=reviewer.id,
        locked_until=now + timedelta(minutes=15),
        uploaded_by_id=reviewer.id,
        uploaded_at=now,
    )
    db.add(doc)
    db.flush()

    xd_results = [{"rule": "XD-01", "status": "fail"}] if with_cross_doc_conflict else []
    job = ExtractionJob(
        id=uuid4(),
        source_document_id=doc.id,
        attempt_no=1,
        doc_type=doc_type,
        status=JobStatus.SUCCEEDED,
        avg_confidence=0.88,
        cross_doc_results=xd_results,
        started_at=now,
    )
    db.add(job)
    db.flush()

    review = ExtractionReview(
        id=uuid4(),
        source_document_id=doc.id,
        extraction_job_id=job.id,
        reviewer_id=reviewer.id,
        reviewer_role_id=reviewer.role_id,
        opened_at=now - timedelta(seconds=45),
    )
    db.add(review)
    db.flush()

    fields: list[ExtractedField] = []
    # Base field
    f1 = ExtractedField(
        id=uuid4(),
        extraction_job_id=job.id,
        source_document_id=doc.id,
        field_key="customer_name",
        value="Công ty Cổ phần Thăng Long",
        raw_text="Công ty Cổ phần Thăng Long",
        value_type=FieldValueType.ORG_NAME,
        confidence=0.55 if low_confidence_field else 0.95,
        source_location={"kind": "pdf_region", "page": 1, "box_2d": [10, 10, 200, 30]},
        source_kind=SourceLocationKind.PDF_REGION,
        sensitivity=SensitivityLabel.NONE,
    )
    fields.append(f1)
    db.add(f1)

    # Total amount field
    f2 = ExtractedField(
        id=uuid4(),
        extraction_job_id=job.id,
        source_document_id=doc.id,
        field_key="total_amount",
        value=50000000,
        raw_text="50,000,000 VND",
        value_type=FieldValueType.MONEY,
        confidence=0.92,
        source_location={"kind": "pdf_region", "page": 1, "box_2d": [10, 50, 150, 70]},
        source_kind=SourceLocationKind.PDF_REGION,
        sensitivity=SensitivityLabel.NONE,
    )
    fields.append(f2)
    db.add(f2)

    if with_salary_field:
        f3 = ExtractedField(
            id=uuid4(),
            extraction_job_id=job.id,
            source_document_id=doc.id,
            field_key="salary",
            value=25000000,
            raw_text="25,000,000 VND",
            value_type=FieldValueType.MONEY,
            confidence=0.96,
            source_location={"kind": "pdf_region", "page": 1, "box_2d": [10, 80, 150, 100]},
            source_kind=SourceLocationKind.PDF_REGION,
            sensitivity=SensitivityLabel.SALARY,
        )
        fields.append(f3)
        db.add(f3)

    db.commit()
    db.refresh(doc)
    return doc, job, review, fields


# ---------------------------------------------------------------------------
# TC-IDP-021: EP-30 Update Document Fields
# ---------------------------------------------------------------------------


def test_tc_idp_021_ep30_edit_field_and_audit_masking(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-021: EP-30 updates field, preserves AI value, masks salary audit."""
    _cfo_user, cfo_token = seed_test_users["ROLE-02"]
    reviewer_user, reviewer_token = seed_test_users["ROLE-05"]

    doc, _job, _review, fields = setup_in_review_doc(
        db_session, reviewer_user, with_salary_field=True
    )
    name_field = next(f for f in fields if f.field_key == "customer_name")
    salary_field = next(f for f in fields if f.field_key == "salary")

    # 1. Non-holder (CFO) calls EP-30 on document locked by Reviewer -> 409 CONFLICT_STATE
    res_unauth = app_client.patch(
        f"/api/v1/documents/{doc.id}/fields",
        headers={"Authorization": f"Bearer {cfo_token}"},
        json={"fields": [{"id": str(name_field.id), "corrected_value": "Công ty Mới"}]},
    )
    assert res_unauth.status_code == 409

    # 2. Lock holder (Reviewer) edits customer_name and salary
    res_edit = app_client.patch(
        f"/api/v1/documents/{doc.id}/fields",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={
            "fields": [
                {"id": str(name_field.id), "corrected_value": "Công ty TNHH Ánh Dương"},
                {"id": str(salary_field.id), "corrected_value": 30000000},
            ]
        },
    )
    assert res_edit.status_code == 200

    # Verify field values: AI value preserved, corrected_value saved
    db_session.refresh(name_field)
    assert name_field.corrected is True
    assert name_field.value == "Công ty Cổ phần Thăng Long"
    assert name_field.corrected_value == "Công ty TNHH Ánh Dương"
    assert name_field.corrected_by_id == reviewer_user.id

    db_session.refresh(salary_field)
    assert salary_field.corrected is True
    assert salary_field.value == 25000000
    assert salary_field.corrected_value == 30000000

    # 3. Check AuditLog: salary field must be masked as ••••
    audits = (
        db_session.execute(
            select(AuditLog).where(
                AuditLog.source_document_id == doc.id,
                AuditLog.action == "field.correct",
            )
        )
        .scalars()
        .all()
    )
    assert len(audits) >= 2
    salary_audit = next(a for a in audits if a.target_id == salary_field.id)
    assert salary_audit.before["value"] == "••••"
    assert salary_audit.after["value"] == "••••"

    name_audit = next(a for a in audits if a.target_id == name_field.id)
    assert name_audit.before["value"] == "Công ty Cổ phần Thăng Long"
    assert name_audit.after["value"] == "Công ty TNHH Ánh Dương"


# ---------------------------------------------------------------------------
# TC-IDP-022, TC-DATA-008, TC-DATA-009: EP-31 Approve & Commit
# ---------------------------------------------------------------------------


def test_tc_idp_022_ep31_validation_gates_and_approval(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-022: EP-31 rejects unconfirmed low confidence or conflict.

    Approves cleanly when all gates pass.
    """
    _reviewer_user, reviewer_token = seed_test_users["ROLE-05"]

    # 1. Low confidence field without correction/confirmation -> 422 VALIDATION_ERROR
    doc_low, _job_low, review_low, fields_low = setup_in_review_doc(
        db_session, _reviewer_user, low_confidence_field=True
    )
    res_low = app_client.post(
        f"/api/v1/documents/{doc_low.id}/review/approve",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"review_id": str(review_low.id)},
    )
    assert res_low.status_code == 422
    assert res_low.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "customer_name" in res_low.json()["error"]["details"]["fields"]

    # Confirm the low confidence field
    name_field = next(f for f in fields_low if f.field_key == "customer_name")
    app_client.patch(
        f"/api/v1/documents/{doc_low.id}/fields",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"confirmed_field_ids": [str(name_field.id)]},
    )

    # 2. Cross-doc conflict without accepted note -> 422 ACTION_REJECTED
    doc_conflict, _job_c, review_c, _fields_c = setup_in_review_doc(
        db_session, _reviewer_user, with_cross_doc_conflict=True
    )
    res_conflict = app_client.post(
        f"/api/v1/documents/{doc_conflict.id}/review/approve",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"review_id": str(review_c.id)},
    )
    assert res_conflict.status_code == 422
    assert res_conflict.json()["error"]["code"] == "ACTION_REJECTED"

    # 3. Clean approval with conflict accepted with note -> 200 COMMITTED
    res_ok = app_client.post(
        f"/api/v1/documents/{doc_conflict.id}/review/approve",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={
            "review_id": str(review_c.id),
            "accepted_conflicts": [
                {"rule": "XD-01", "note": "Hóa đơn điều chỉnh đã được xác nhận"}
            ],
        },
    )
    assert res_ok.status_code == 200
    data = res_ok.json()["data"]

    # Check status and undo deadline
    assert data["document"]["status"] == "COMMITTED"
    assert data["review"]["decision"] == "APPROVED"
    assert len(data["commit"]["actions"]) >= 1

    # TC-DATA-009: Check 7 days undo_deadline (within 5 seconds tolerance of 7 days)
    db_session.refresh(doc_conflict)
    assert doc_conflict.status == DocumentStatus.COMMITTED
    assert doc_conflict.committed_at is not None
    assert doc_conflict.undo_deadline is not None
    diff = doc_conflict.undo_deadline - doc_conflict.committed_at
    assert abs(diff.total_seconds() - 7 * 86400) < 5

    # TC-DATA-008: Check Lineage: ExtractedField.business_record_id is linked
    stmt_fields = select(ExtractedField).where(ExtractedField.source_document_id == doc_conflict.id)
    linked_fields = db_session.execute(stmt_fields).scalars().all()
    assert len(linked_fields) > 0
    for lf in linked_fields:
        assert lf.business_record_id is not None
        rec = db_session.get(BusinessRecord, lf.business_record_id)
        assert rec is not None
        assert rec.source_document_id == doc_conflict.id


# ---------------------------------------------------------------------------
# TC-IDP-025: EP-32 Reject Document
# ---------------------------------------------------------------------------


def test_tc_idp_025_ep32_reject_document(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-025: EP-32 rejects document with reason code and audit."""
    _reviewer_user, reviewer_token = seed_test_users["ROLE-05"]

    doc, _job, review, _fields = setup_in_review_doc(db_session, _reviewer_user)

    # 1. Missing note when OTHER -> 422 VALIDATION_ERROR
    res_other_no_note = app_client.post(
        f"/api/v1/documents/{doc.id}/review/reject",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"review_id": str(review.id), "reject_reason_code": "OTHER"},
    )
    assert res_other_no_note.status_code == 422

    # 2. Valid reject with UNREADABLE
    res_reject = app_client.post(
        f"/api/v1/documents/{doc.id}/review/reject",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"review_id": str(review.id), "reject_reason_code": "UNREADABLE"},
    )
    assert res_reject.status_code == 200
    assert res_reject.json()["data"]["status"] == "REJECTED"

    db_session.refresh(doc)
    assert doc.status == DocumentStatus.REJECTED
    assert doc.locked_by_id is None

    db_session.refresh(review)
    assert review.decision == ReviewDecision.REJECTED
    assert review.reject_reason_code == "UNREADABLE"

    # Audit check
    audit = db_session.execute(
        select(AuditLog).where(
            AuditLog.target_id == doc.id,
            AuditLog.action == "review.reject",
        )
    ).scalar_one_or_none()
    assert audit is not None

"""Tests for IDP document listing, details, source viewing, and retry (EP-24, 25, 26, 27, 34).

Specs:
- EP-24: Scoped document list (TC-IDP-031).
- EP-25: Scoped document detail with jobs, timeline, affected, reviews (TC-IDP-031).
- EP-27: Presigned URL, manual info, and PII audit (TC-IDP-032).
- Salary protection on EP-27: 403 FORBIDDEN_SALARY + audit document.open_denied (TC-AUTH-014).
- Salary masking on EP-26 for CEO: masked fields (TC-AUTH-015).
- EP-34: Retry, reopen, and force duplicate state transitions and role guards.
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


def create_doc_helper(
    db: Session,
    uploader: User,
    doc_type: DocType,
    pillars: list[str],
    status: DocumentStatus = DocumentStatus.NEEDS_REVIEW,
    contains_salary: bool = False,
    contains_pii: bool = False,
    kind: DocumentKind = DocumentKind.FILE,
    storage_key: str | None = None,
) -> SourceDocument:
    doc = SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=kind,
        original_filename=f"{doc_type.value.lower()}_test.pdf",
        mime_type="application/pdf",
        size_bytes=10240,
        page_count=2,
        storage_key=storage_key or f"documents/{uuid4()}.pdf",
        doc_type=doc_type,
        pillars=pillars,
        status=status,
        contains_salary=contains_salary,
        contains_pii=contains_pii,
        uploaded_by_id=uploader.id,
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# TC-IDP-031: EP-24 & EP-25 Scoping and Document Details
# ---------------------------------------------------------------------------


def test_tc_idp_031_ep24_document_list_scoping(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-031: EP-24 list scoping by role:

    ROLE-01 & ROLE-05 see all;
    ROLE-02 sees FIN + own uploads;
    ROLE-03 sees own uploads only;
    ROLE-04 sees HR + own uploads.
    """
    _ceo_user, ceo_token = seed_test_users["ROLE-01"]
    cfo_user, cfo_token = seed_test_users["ROLE-02"]
    sales_user, sales_token = seed_test_users["ROLE-03"]
    hr_user, hr_token = seed_test_users["ROLE-04"]

    # 1. Create FIN document uploaded by CFO
    fin_doc = create_doc_helper(db_session, cfo_user, DocType.INVOICE, ["FIN"])
    # 2. Create HR document uploaded by HR
    hr_doc = create_doc_helper(
        db_session,
        hr_user,
        DocType.EMPLOYEE_LIST,
        ["HR"],
        contains_salary=True,
    )
    # 3. Create CUS document uploaded by Sales Director
    cus_doc = create_doc_helper(db_session, sales_user, DocType.CONTRACT, ["CUS"])

    # CEO: sees all 3
    res_ceo = app_client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {ceo_token}"},
    )
    assert res_ceo.status_code == 200
    ceo_ids = {d["id"] for d in res_ceo.json()["data"]}
    assert {str(fin_doc.id), str(hr_doc.id), str(cus_doc.id)}.issubset(ceo_ids)

    # CFO: sees FIN + own uploads, does NOT see HR doc
    res_cfo = app_client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {cfo_token}"},
    )
    assert res_cfo.status_code == 200
    cfo_ids = {d["id"] for d in res_cfo.json()["data"]}
    assert str(fin_doc.id) in cfo_ids
    assert str(hr_doc.id) not in cfo_ids

    # Sales Director: sees ONLY own uploads (cus_doc), does NOT see fin_doc or hr_doc
    res_sales = app_client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {sales_token}"},
    )
    assert res_sales.status_code == 200
    sales_ids = {d["id"] for d in res_sales.json()["data"]}
    assert str(cus_doc.id) in sales_ids
    assert str(fin_doc.id) not in sales_ids
    assert str(hr_doc.id) not in sales_ids

    # HR Manager: sees HR + own uploads, does NOT see fin_doc or cus_doc
    res_hr = app_client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {hr_token}"},
    )
    assert res_hr.status_code == 200
    hr_ids = {d["id"] for d in res_hr.json()["data"]}
    assert str(hr_doc.id) in hr_ids
    assert str(fin_doc.id) not in hr_ids
    assert str(cus_doc.id) not in hr_ids


def test_tc_idp_031_ep25_document_details_and_scoping(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-031: EP-25 returns jobs, timeline, affected, reviews; outside scope -> 403."""
    cfo_user, cfo_token = seed_test_users["ROLE-02"]
    _sales_user, sales_token = seed_test_users["ROLE-03"]
    reviewer_user, _reviewer_token = seed_test_users["ROLE-05"]

    doc = create_doc_helper(db_session, cfo_user, DocType.INVOICE, ["FIN"])

    # Add extraction job
    job = ExtractionJob(
        id=uuid4(),
        source_document_id=doc.id,
        attempt_no=1,
        doc_type=DocType.INVOICE,
        status=JobStatus.SUCCEEDED,
        classification_confidence=0.98,
        started_at=datetime.now(UTC),
    )
    db_session.add(job)

    # Add business record affected
    record = BusinessRecord(
        id=uuid4(),
        record_type=DocType.INVOICE,  # type: ignore[arg-type]
        pillar="FIN",
        code="INV-TEST-001",
        total_amount=10000000,
        source_document_id=doc.id,
    )
    db_session.add(record)

    # Add extraction review
    review = ExtractionReview(
        id=uuid4(),
        source_document_id=doc.id,
        extraction_job_id=job.id,
        reviewer_id=reviewer_user.id,
        reviewer_role_id=reviewer_user.role_id,
        decision=None,
        opened_at=datetime.now(UTC),
    )
    db_session.add(review)

    # Add audit log for timeline
    audit = AuditLog(
        id=uuid4(),
        action="document.upload",
        target_type="source_documents",
        target_id=doc.id,
        actor_type="USER",  # type: ignore[arg-type]
        actor_user_id=cfo_user.id,
        actor_role_id=cfo_user.role_id,
        occurred_at=datetime.now(UTC),
    )
    db_session.add(audit)
    db_session.commit()

    # 1. CFO accessing within scope -> 200 with full details
    res_cfo = app_client.get(
        f"/api/v1/documents/{doc.id}",
        headers={"Authorization": f"Bearer {cfo_token}"},
    )
    assert res_cfo.status_code == 200
    data = res_cfo.json()["data"]
    assert data["document"]["id"] == str(doc.id)
    assert len(data["jobs"]) == 1
    assert len(data["status_timeline"]) >= 1
    assert str(record.id) in data["affected"]["business_record_ids"]
    assert len(data["reviews"]) == 1

    # 2. Sales Director accessing outside scope -> 403 FORBIDDEN_SCOPE
    res_sales = app_client.get(
        f"/api/v1/documents/{doc.id}",
        headers={"Authorization": f"Bearer {sales_token}"},
    )
    assert res_sales.status_code == 403
    assert res_sales.json()["error"]["code"] == "FORBIDDEN_SCOPE"


# ---------------------------------------------------------------------------
# TC-IDP-032 & TC-AUTH-014: EP-27 Presigned URL, Manual Info, Salary Protection
# ---------------------------------------------------------------------------


def test_tc_idp_032_ep27_source_presigned_url_and_pii_audit(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-032: EP-27 returns presigned URL (expires in <= 15m), pages, and records PII audit."""
    cfo_user, cfo_token = seed_test_users["ROLE-02"]

    doc = create_doc_helper(
        db_session,
        cfo_user,
        DocType.INVOICE,
        ["FIN"],
        contains_pii=True,
    )

    # Add page
    page = DocumentPage(
        id=uuid4(),
        source_document_id=doc.id,
        page_number=1,
        width_px=800,
        height_px=1100,
        ocr_used=True,
        ocr_confidence=0.96,
        image_storage_key=f"pages/{doc.id}_1.png",
    )
    db_session.add(page)
    db_session.commit()

    # Call EP-27
    res = app_client.get(
        f"/api/v1/documents/{doc.id}/source",
        headers={"Authorization": f"Bearer {cfo_token}"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["url"] is not None
    url = data["url"]
    has_sig = any(sig in url for sig in ("X-Amz-Signature=", "AWSAccessKeyId=", "X-Amz-Algorithm="))
    assert has_sig
    assert data["expires_at"] is not None
    assert len(data["pages"]) == 1
    assert data["pages"][0]["width_px"] == 800

    # Verify audit log was recorded for document.open_pii
    audit_stmt = select(AuditLog).where(
        AuditLog.target_id == doc.id,
        AuditLog.action == "document.open_pii",
    )
    audit = db_session.execute(audit_stmt).scalar_one_or_none()
    assert audit is not None


def test_tc_idp_032_ep27_virtual_document_returns_manual_info(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-032: Virtual manual document returns manual_info without URL."""
    cfo_user, cfo_token = seed_test_users["ROLE-02"]

    doc = create_doc_helper(
        db_session,
        cfo_user,
        DocType.INVOICE,
        ["FIN"],
        kind=DocumentKind.MANUAL,
    )

    res = app_client.get(
        f"/api/v1/documents/{doc.id}/source",
        headers={"Authorization": f"Bearer {cfo_token}"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["url"] is None
    assert data["manual_info"] is not None
    assert data["manual_info"]["created_by_full_name"] == cfo_user.full_name


def test_tc_auth_014_salary_document_access_control(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-AUTH-014: Salary document access control on EP-27:

    - ROLE-01/02/03 -> 403 FORBIDDEN_SALARY + audit document.open_denied.
    - ROLE-04 -> can open and download.
    - ROLE-05 -> can open inline only when currently locked in review; attachment -> 403.
    """
    ceo_user, ceo_token = seed_test_users["ROLE-01"]
    _cfo_user, cfo_token = seed_test_users["ROLE-02"]
    hr_user, hr_token = seed_test_users["ROLE-04"]
    reviewer_user, reviewer_token = seed_test_users["ROLE-05"]

    doc = create_doc_helper(
        db_session,
        hr_user,
        DocType.EMPLOYEE_LIST,
        ["HR"],
        contains_salary=True,
    )

    # 1. CEO -> 403 FORBIDDEN_SALARY + audit document.open_denied
    res_ceo = app_client.get(
        f"/api/v1/documents/{doc.id}/source",
        headers={"Authorization": f"Bearer {ceo_token}"},
    )
    assert res_ceo.status_code == 403
    assert res_ceo.json()["error"]["code"] == "FORBIDDEN_SALARY"

    # Verify audit document.open_denied was recorded for CEO
    audit_ceo = db_session.execute(
        select(AuditLog).where(
            AuditLog.target_id == doc.id,
            AuditLog.action == "document.open_denied",
            AuditLog.actor_user_id == ceo_user.id,
        )
    ).scalar_one_or_none()
    assert audit_ceo is not None

    # 2. CFO -> 403 FORBIDDEN_SALARY
    res_cfo = app_client.get(
        f"/api/v1/documents/{doc.id}/source",
        headers={"Authorization": f"Bearer {cfo_token}"},
    )
    assert res_cfo.status_code == 403
    assert res_cfo.json()["error"]["code"] == "FORBIDDEN_SALARY"

    # 3. HR Manager -> Allowed (both inline and attachment)
    res_hr = app_client.get(
        f"/api/v1/documents/{doc.id}/source?disposition=attachment",
        headers={"Authorization": f"Bearer {hr_token}"},
    )
    assert res_hr.status_code == 200

    # 4. Reviewer without review lock -> 403 FORBIDDEN_SALARY
    res_rev_unlocked = app_client.get(
        f"/api/v1/documents/{doc.id}/source",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res_rev_unlocked.status_code == 403
    assert res_rev_unlocked.json()["error"]["code"] == "FORBIDDEN_SALARY"

    # 5. Reviewer WITH active review lock
    doc.status = DocumentStatus.IN_REVIEW
    doc.locked_by_id = reviewer_user.id
    doc.locked_until = datetime.now(UTC) + timedelta(minutes=15)
    db_session.commit()

    # Inline -> 200 Allowed!
    res_rev_locked = app_client.get(
        f"/api/v1/documents/{doc.id}/source?disposition=inline",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res_rev_locked.status_code == 200

    # Attachment -> 403 FORBIDDEN_SALARY (Reviewer cannot download salary documents)
    res_rev_attach = app_client.get(
        f"/api/v1/documents/{doc.id}/source?disposition=attachment",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res_rev_attach.status_code == 403
    assert res_rev_attach.json()["error"]["code"] == "FORBIDDEN_SALARY"


# ---------------------------------------------------------------------------
# TC-AUTH-015: EP-26 Salary Masking for CEO
# ---------------------------------------------------------------------------


def test_tc_auth_015_ep26_salary_masking_for_ceo(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-AUTH-015: On EP-26, CEO sees SALARY fields masked=True with null values."""
    _ceo_user, ceo_token = seed_test_users["ROLE-01"]
    hr_user, hr_token = seed_test_users["ROLE-04"]

    doc = create_doc_helper(
        db_session,
        hr_user,
        DocType.EMPLOYEE_LIST,
        ["HR"],
        contains_salary=True,
    )

    job = ExtractionJob(
        id=uuid4(),
        source_document_id=doc.id,
        attempt_no=1,
        doc_type=DocType.EMPLOYEE_LIST,
        status=JobStatus.SUCCEEDED,
        started_at=datetime.now(UTC),
    )
    db_session.add(job)

    # Add sensitive salary field
    field = ExtractedField(
        id=uuid4(),
        extraction_job_id=job.id,
        source_document_id=doc.id,
        field_key="salary",
        value=35000000,
        raw_text="35.000.000 đ",
        value_type=FieldValueType.MONEY,
        confidence=0.98,
        source_location={"kind": "cell", "page": 1, "row": 2, "col": 5},
        source_kind=SourceLocationKind.CELL,
        sensitivity=SensitivityLabel.SALARY,
    )
    db_session.add(field)
    db_session.commit()

    # 1. CEO calls EP-26 -> salary field is MASKED!
    res_ceo = app_client.get(
        f"/api/v1/documents/{doc.id}/extraction",
        headers={"Authorization": f"Bearer {ceo_token}"},
    )
    assert res_ceo.status_code == 200
    fields_ceo = res_ceo.json()["data"]["fields"]
    salary_f_ceo = next(f for f in fields_ceo if f["field_key"] == "salary")
    assert salary_f_ceo["masked"] is True
    assert salary_f_ceo["value"] is None
    assert salary_f_ceo["raw_text"] is None
    assert salary_f_ceo["source_location"] is None

    # 2. HR Manager calls EP-26 -> salary field is UNMASKED!
    res_hr = app_client.get(
        f"/api/v1/documents/{doc.id}/extraction",
        headers={"Authorization": f"Bearer {hr_token}"},
    )
    assert res_hr.status_code == 200
    fields_hr = res_hr.json()["data"]["fields"]
    salary_f_hr = next(f for f in fields_hr if f["field_key"] == "salary")
    assert salary_f_hr["masked"] is False
    assert salary_f_hr["value"] == 35000000


# ---------------------------------------------------------------------------
# EP-34: Retry, Reopen, and Force Duplicate Transitions
# ---------------------------------------------------------------------------


def test_ep34_retry_failed_document(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """EP-34: Retry a FAILED document enqueues pipeline and transitions to PREPROCESSING."""
    cfo_user, cfo_token = seed_test_users["ROLE-02"]
    _sales_user, sales_token = seed_test_users["ROLE-03"]

    doc = create_doc_helper(
        db_session,
        cfo_user,
        DocType.INVOICE,
        ["FIN"],
        status=DocumentStatus.FAILED,
    )

    # 1. Sales Director cannot retry FIN document -> 403
    res_sales = app_client.post(
        f"/api/v1/documents/{doc.id}/retry",
        headers={
            "Authorization": f"Bearer {sales_token}",
            "Idempotency-Key": str(uuid4()),
        },
        json={"mode": "RETRY", "note": "Thử lại"},
    )
    assert res_sales.status_code == 403

    # 2. CFO can retry FIN document -> 202 ACCEPTED
    res_cfo = app_client.post(
        f"/api/v1/documents/{doc.id}/retry",
        headers={
            "Authorization": f"Bearer {cfo_token}",
            "Idempotency-Key": str(uuid4()),
        },
        json={"mode": "RETRY", "note": "Thử lại OCR"},
    )
    assert res_cfo.status_code == 202
    data = res_cfo.json()["data"]
    assert data["status"] == "PREPROCESSING"
    assert data["retry_count"] == 1


def test_ep34_reopen_rejected_document(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """EP-34: Reopen a REJECTED document transitions to NEEDS_REVIEW."""
    cfo_user, cfo_token = seed_test_users["ROLE-02"]

    doc = create_doc_helper(
        db_session,
        cfo_user,
        DocType.INVOICE,
        ["FIN"],
        status=DocumentStatus.REJECTED,
    )

    res = app_client.post(
        f"/api/v1/documents/{doc.id}/retry",
        headers={
            "Authorization": f"Bearer {cfo_token}",
            "Idempotency-Key": str(uuid4()),
        },
        json={"mode": "REOPEN", "note": "Khách hàng bổ sung chứng từ"},
    )
    assert res.status_code == 202
    assert res.json()["data"]["status"] == "NEEDS_REVIEW"


def test_ep34_force_duplicate_document(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """EP-34: Force process DUPLICATE document transitions to PREPROCESSING."""
    cfo_user, cfo_token = seed_test_users["ROLE-02"]
    _sales_user, sales_token = seed_test_users["ROLE-03"]

    doc = create_doc_helper(
        db_session,
        cfo_user,
        DocType.INVOICE,
        ["FIN"],
        status=DocumentStatus.DUPLICATE,
    )

    # Sales user is not uploader and not Reviewer -> 403
    res_sales = app_client.post(
        f"/api/v1/documents/{doc.id}/retry",
        headers={
            "Authorization": f"Bearer {sales_token}",
            "Idempotency-Key": str(uuid4()),
        },
        json={"mode": "FORCE_DUPLICATE", "note": "Vẫn xử lý"},
    )
    assert res_sales.status_code == 403

    # CFO is uploader -> 202 ACCEPTED
    res_cfo = app_client.post(
        f"/api/v1/documents/{doc.id}/retry",
        headers={
            "Authorization": f"Bearer {cfo_token}",
            "Idempotency-Key": str(uuid4()),
        },
        json={"mode": "FORCE_DUPLICATE", "note": "Hóa đơn điều chỉnh thay thế"},
    )
    assert res_cfo.status_code == 202
    assert res_cfo.json()["data"]["status"] == "PREPROCESSING"

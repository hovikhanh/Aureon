"""Tests for IDP Review Queue (EP-28), Review Lock (EP-29), and Release (EP-35).

Specs:
- EP-28: Prioritized review queue and role scoping (TC-IDP-018).
- EP-29: Open review with 15-minute soft lock (TC-IDP-019).
- EP-35: Release review lock and abandon review (TC-IDP-019).
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


def create_queue_doc(
    db: Session,
    uploader: User,
    doc_type: DocType,
    pillars: list[str],
    status: DocumentStatus = DocumentStatus.NEEDS_REVIEW,
    avg_confidence: float = 0.85,
    has_conflict: bool = False,
    uploaded_at: datetime | None = None,
) -> tuple[SourceDocument, ExtractionJob]:
    now = uploaded_at or datetime.now(UTC)
    doc = SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename=f"{doc_type.value.lower()}_queue.pdf",
        mime_type="application/pdf",
        size_bytes=20480,
        page_count=2,
        storage_key=f"documents/{uuid4()}.pdf",
        doc_type=doc_type,
        pillars=pillars,
        status=status,
        uploaded_by_id=uploader.id,
        uploaded_at=now,
    )
    db.add(doc)
    db.flush()

    xd_results = [{"rule": "XD-01", "status": "fail"}] if has_conflict else []
    job = ExtractionJob(
        id=uuid4(),
        source_document_id=doc.id,
        attempt_no=1,
        doc_type=doc_type,
        status=JobStatus.SUCCEEDED,
        avg_confidence=avg_confidence,
        cross_doc_results=xd_results,
        started_at=now,
    )
    db.add(job)
    db.flush()

    field = ExtractedField(
        id=uuid4(),
        extraction_job_id=job.id,
        source_document_id=doc.id,
        field_key="test_field",
        value="test_val",
        raw_text="test_val",
        value_type=FieldValueType.TEXT,
        confidence=avg_confidence,
        source_location={"kind": "pdf_region", "page": 1, "box_2d": [0, 0, 100, 100]},
        source_kind=SourceLocationKind.PDF_REGION,
        sensitivity=SensitivityLabel.NONE,
    )
    db.add(field)
    db.commit()
    db.refresh(doc)
    return doc, job


# ---------------------------------------------------------------------------
# TC-IDP-018: EP-28 Review Queue
# ---------------------------------------------------------------------------


def test_tc_idp_018_ep28_prioritized_review_queue(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-018: EP-28 priority order: conflict > low confidence > oldest uploaded_at."""
    _cfo_user, _cfo_token = seed_test_users["ROLE-02"]
    reviewer_user, reviewer_token = seed_test_users["ROLE-05"]

    t0 = datetime.now(UTC) - timedelta(hours=3)
    t1 = datetime.now(UTC) - timedelta(hours=2)
    t2 = datetime.now(UTC) - timedelta(hours=1)

    # doc_low: low confidence (0.65), no conflict, t1
    doc_low, _ = create_queue_doc(
        db_session, reviewer_user, DocType.INVOICE, ["FIN"], avg_confidence=0.65, uploaded_at=t1
    )
    # doc_conflict: has cross-doc conflict, higher confidence (0.95), t2
    doc_conflict, _ = create_queue_doc(
        db_session,
        reviewer_user,
        DocType.INVOICE,
        ["FIN"],
        avg_confidence=0.95,
        has_conflict=True,
        uploaded_at=t2,
    )
    # doc_old: oldest uploaded_at t0, high confidence (0.88), no conflict
    doc_old, _ = create_queue_doc(
        db_session, reviewer_user, DocType.INVOICE, ["FIN"], avg_confidence=0.88, uploaded_at=t0
    )

    res = app_client.get(
        "/api/v1/review-queue",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res.status_code == 200
    body = res.json()
    items = body["data"]
    item_ids = [it["document"]["id"] for it in items]

    # Verify doc_conflict is prioritized first among these 3
    idx_conflict = item_ids.index(str(doc_conflict.id))
    idx_low = item_ids.index(str(doc_low.id))
    idx_old = item_ids.index(str(doc_old.id))

    assert idx_conflict < idx_low < idx_old


def test_tc_idp_018_ep28_role_scoping_and_counts(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-018: EP-28 scoping: CFO sees FIN only, HR sees HR only, Sales is 403."""
    cfo_user, cfo_token = seed_test_users["ROLE-02"]
    _sales_user, sales_token = seed_test_users["ROLE-03"]
    hr_user, hr_token = seed_test_users["ROLE-04"]
    _rev_user, rev_token = seed_test_users["ROLE-05"]

    fin_doc, _ = create_queue_doc(
        db_session, cfo_user, DocType.INVOICE, ["FIN"], status=DocumentStatus.NEEDS_REVIEW
    )
    hr_doc, _ = create_queue_doc(
        db_session, hr_user, DocType.EMPLOYEE_LIST, ["HR"], status=DocumentStatus.IN_REVIEW
    )

    # 1. Sales Director calling EP-28 -> 403 FORBIDDEN_ROLE
    res_sales = app_client.get(
        "/api/v1/review-queue",
        headers={"Authorization": f"Bearer {sales_token}"},
    )
    assert res_sales.status_code == 403

    # 2. CFO sees only FIN
    res_cfo = app_client.get(
        "/api/v1/review-queue",
        headers={"Authorization": f"Bearer {cfo_token}"},
    )
    assert res_cfo.status_code == 200
    cfo_doc_ids = {it["document"]["id"] for it in res_cfo.json()["data"]}
    assert str(fin_doc.id) in cfo_doc_ids
    assert str(hr_doc.id) not in cfo_doc_ids

    # 3. HR sees only HR
    res_hr = app_client.get(
        "/api/v1/review-queue",
        headers={"Authorization": f"Bearer {hr_token}"},
    )
    assert res_hr.status_code == 200
    hr_doc_ids = {it["document"]["id"] for it in res_hr.json()["data"]}
    assert str(hr_doc.id) in hr_doc_ids
    assert str(fin_doc.id) not in hr_doc_ids

    # 4. Reviewer sees both + counts in meta
    res_rev = app_client.get(
        "/api/v1/review-queue",
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert res_rev.status_code == 200
    rev_doc_ids = {it["document"]["id"] for it in res_rev.json()["data"]}
    assert str(fin_doc.id) in rev_doc_ids
    assert str(hr_doc.id) in rev_doc_ids

    meta = res_rev.json()["meta"]
    assert "counts" in meta
    assert meta["counts"]["needs_review"] >= 1
    assert meta["counts"]["in_review"] >= 1


# ---------------------------------------------------------------------------
# TC-IDP-019: EP-29 Review Open & EP-35 Review Release
# ---------------------------------------------------------------------------


def test_tc_idp_019_ep29_open_lock_and_conflict(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-019: EP-29 locks document for 15 minutes.

    Second reviewer receives 409 REVIEW_LOCKED.
    """
    cfo_user, cfo_token = seed_test_users["ROLE-02"]
    reviewer_user, reviewer_token = seed_test_users["ROLE-05"]

    doc, _ = create_queue_doc(
        db_session, cfo_user, DocType.INVOICE, ["FIN"], status=DocumentStatus.NEEDS_REVIEW
    )

    # 1. Reviewer opens review -> 200, status becomes IN_REVIEW, locked_by = Reviewer
    res_open = app_client.post(
        f"/api/v1/documents/{doc.id}/review/open",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res_open.status_code == 200
    body = res_open.json()["data"]
    assert body["document"]["status"] == "IN_REVIEW"
    assert body["document"]["locked_by"]["id"] == str(reviewer_user.id)
    assert body["review_id"] is not None
    assert body["extraction"] is not None

    # Check AuditLog
    audit_open = db_session.execute(
        select(AuditLog).where(
            AuditLog.target_id == doc.id,
            AuditLog.action == "review.open",
        )
    ).scalar_one_or_none()
    assert audit_open is not None

    # Check ExtractionReview
    rev_row = db_session.execute(
        select(ExtractionReview).where(ExtractionReview.source_document_id == doc.id)
    ).scalar_one_or_none()
    assert rev_row is not None
    assert rev_row.reviewer_id == reviewer_user.id
    assert rev_row.opened_at is not None

    # 2. CFO tries to open the same document while locked by Reviewer -> 409 REVIEW_LOCKED
    res_conflict = app_client.post(
        f"/api/v1/documents/{doc.id}/review/open",
        headers={"Authorization": f"Bearer {cfo_token}"},
    )
    assert res_conflict.status_code == 409
    err = res_conflict.json()["error"]
    assert err["code"] == "REVIEW_LOCKED"
    assert err["details"]["locked_by"] == reviewer_user.full_name
    assert err["details"]["remaining_seconds"] > 0

    # 3. Same Reviewer calls EP-29 again -> 200, renews lock
    res_renew = app_client.post(
        f"/api/v1/documents/{doc.id}/review/open",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res_renew.status_code == 200


def test_tc_idp_019_ep35_release_lock_and_abandon(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-019: EP-35 releases review lock, returns to NEEDS_REVIEW, marks review ABANDONED."""
    cfo_user, cfo_token = seed_test_users["ROLE-02"]
    _reviewer_user, reviewer_token = seed_test_users["ROLE-05"]

    doc, _ = create_queue_doc(
        db_session, cfo_user, DocType.INVOICE, ["FIN"], status=DocumentStatus.NEEDS_REVIEW
    )

    # 1. Reviewer opens review
    app_client.post(
        f"/api/v1/documents/{doc.id}/review/open",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    # 2. CFO cannot release lock held by Reviewer -> 403
    res_cfo_release = app_client.post(
        f"/api/v1/documents/{doc.id}/review/release",
        headers={"Authorization": f"Bearer {cfo_token}"},
    )
    assert res_cfo_release.status_code == 403

    # 3. Reviewer releases review -> 200, status returns to NEEDS_REVIEW
    res_release = app_client.post(
        f"/api/v1/documents/{doc.id}/review/release",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res_release.status_code == 200
    assert res_release.json()["data"]["status"] == "NEEDS_REVIEW"
    assert res_release.json()["data"]["locked_by"] is None

    # Check ExtractionReview marked ABANDONED
    rev_row = db_session.execute(
        select(ExtractionReview).where(ExtractionReview.source_document_id == doc.id)
    ).scalar_one_or_none()
    assert rev_row is not None
    assert rev_row.decision == ReviewDecision.ABANDONED
    assert rev_row.decided_at is not None

    # Check AuditLog
    audit_release = db_session.execute(
        select(AuditLog).where(
            AuditLog.target_id == doc.id,
            AuditLog.action == "review.release",
        )
    ).scalar_one_or_none()
    assert audit_release is not None

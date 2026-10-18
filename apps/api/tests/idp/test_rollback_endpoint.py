"""Integration tests for IDP Rollback: EP-33 (TC-IDP-026, TC-IDP-030).

Test Cases:
- TC-IDP-026: EP-33 rollback within 7 days -> ROLLED_BACK, records soft-deleted, audit recorded.
  - Expired undo deadline -> 410 UNDO_EXPIRED.
  - Non-committed document -> 409 CONFLICT_STATE.
  - CEO (ROLE-01) / Sales (ROLE-03) -> 403 FORBIDDEN_ROLE.
  - CFO (ROLE-02) on non-FIN pillar -> 403 FORBIDDEN_SCOPE.
  - Empty reason -> 422 VALIDATION_ERROR.
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
    InputChannel,
    JobStatus,
    RecordType,
)
from app.modules.idp.models import (
    BusinessRecord,
    ExtractionJob,
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


def setup_committed_doc(
    db: Session,
    actor: User,
    doc_type: DocType = DocType.INVOICE,
    pillars: list[str] | None = None,
    is_expired: bool = False,
) -> tuple[SourceDocument, BusinessRecord]:
    now = datetime.now(UTC)
    committed_at = now - timedelta(days=8) if is_expired else now - timedelta(days=2)
    undo_deadline = committed_at + timedelta(days=7)

    doc = SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename=f"{doc_type.value.lower()}_committed.pdf",
        mime_type="application/pdf",
        size_bytes=10240,
        page_count=1,
        storage_key=f"documents/{uuid4()}.pdf",
        doc_type=doc_type,
        pillars=pillars or ["FIN"],
        status=DocumentStatus.COMMITTED,
        committed_at=committed_at,
        undo_deadline=undo_deadline,
        uploaded_by_id=actor.id,
        uploaded_at=committed_at - timedelta(hours=1),
    )
    db.add(doc)
    db.flush()

    job = ExtractionJob(
        id=uuid4(),
        source_document_id=doc.id,
        attempt_no=1,
        doc_type=doc_type,
        status=JobStatus.SUCCEEDED,
        avg_confidence=0.95,
        started_at=committed_at - timedelta(minutes=30),
    )
    db.add(job)
    db.flush()

    record = BusinessRecord(
        id=uuid4(),
        record_type=RecordType.INVOICE,
        pillar="FIN",
        code=f"INV-{doc.id.hex[:6].upper()}",
        name="Hóa đơn dịch vụ",
        total_amount=50000000,
        source_document_id=doc.id,
        created_by_action="invoice.create",
        idempotency_key=f"idem-{doc.id.hex[:8]}",
    )
    db.add(record)
    db.commit()
    db.refresh(doc)
    db.refresh(record)
    return doc, record


def test_tc_idp_026_ep33_rollback_clean(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-026: Rollback committed document within 7 days -> ROLLED_BACK & soft-delete record."""
    _reviewer_user, reviewer_token = seed_test_users["ROLE-05"]

    doc, record = setup_committed_doc(db_session, _reviewer_user)

    res = app_client.post(
        f"/api/v1/documents/{doc.id}/rollback",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"reason": "Phát hiện sai sót số tiền hợp đồng cần chỉnh sửa"},
    )
    assert res.status_code == 200
    data = res.json()["data"]

    # Verify response
    assert data["document"]["status"] == "ROLLED_BACK"
    assert "METRIC-FIN-01" in data["affected_metric_codes"]

    # Verify DB state
    db_session.refresh(doc)
    assert doc.status == DocumentStatus.ROLLED_BACK
    assert "Phát hiện sai sót" in (doc.status_reason or "")

    # Business record must be soft deleted
    db_session.refresh(record)
    assert record.deleted_at is not None

    # Audit log check
    audit = db_session.execute(
        select(AuditLog).where(
            AuditLog.target_id == doc.id,
            AuditLog.action == "document.rollback",
        )
    ).scalar_one_or_none()
    assert audit is not None
    assert audit.before["status"] == "COMMITTED"
    assert audit.after["status"] == "ROLLED_BACK"
    assert audit.metadata_["reason"] == "Phát hiện sai sót số tiền hợp đồng cần chỉnh sửa"


def test_tc_idp_026_ep33_rollback_expired_and_invalid_states(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-026: Rollback rejects expired deadline (410), invalid status (409), empty reason."""
    _reviewer_user, reviewer_token = seed_test_users["ROLE-05"]

    # 1. Expired undo deadline (> 7 days) -> 410 UNDO_EXPIRED
    doc_expired, _ = setup_committed_doc(db_session, _reviewer_user, is_expired=True)
    res_exp = app_client.post(
        f"/api/v1/documents/{doc_expired.id}/rollback",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"reason": "Quá hạn nhưng vẫn muốn hoàn tác"},
    )
    assert res_exp.status_code == 410
    assert res_exp.json()["error"]["code"] == "UNDO_EXPIRED"

    # 2. Non-committed document (IN_REVIEW) -> 409 CONFLICT_STATE
    now = datetime.now(UTC)
    doc_uncommitted = SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename="pending.pdf",
        mime_type="application/pdf",
        size_bytes=5120,
        page_count=1,
        storage_key=f"documents/{uuid4()}.pdf",
        doc_type=DocType.INVOICE,
        pillars=["FIN"],
        status=DocumentStatus.IN_REVIEW,
        uploaded_by_id=_reviewer_user.id,
        uploaded_at=now,
    )
    db_session.add(doc_uncommitted)
    db_session.commit()

    res_conflict = app_client.post(
        f"/api/v1/documents/{doc_uncommitted.id}/rollback",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"reason": "Chưa duyệt mà đòi rollback"},
    )
    assert res_conflict.status_code == 409
    assert res_conflict.json()["error"]["code"] == "CONFLICT_STATE"

    # 3. Empty or whitespace reason -> 422 VALIDATION_ERROR
    doc_ok, _ = setup_committed_doc(db_session, _reviewer_user)
    res_empty_reason = app_client.post(
        f"/api/v1/documents/{doc_ok.id}/rollback",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"reason": "   "},
    )
    assert res_empty_reason.status_code == 422


def test_tc_idp_026_ep33_role_and_scope_permissions(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-026: CEO (ROLE-01) & Sales (ROLE-03) forbidden; CFO (ROLE-02) scoped to FIN."""
    _ceo_user, ceo_token = seed_test_users["ROLE-01"]
    _cfo_user, cfo_token = seed_test_users["ROLE-02"]
    _sales_user, sales_token = seed_test_users["ROLE-03"]
    reviewer_user, _reviewer_token = seed_test_users["ROLE-05"]

    # Doc in HR pillar
    doc_hr, _ = setup_committed_doc(
        db_session, reviewer_user, doc_type=DocType.EMPLOYEE_LIST, pillars=["HR"]
    )

    # 1. CEO -> 403 FORBIDDEN_ROLE
    res_ceo = app_client.post(
        f"/api/v1/documents/{doc_hr.id}/rollback",
        headers={"Authorization": f"Bearer {ceo_token}"},
        json={"reason": "CEO muốn hoàn tác"},
    )
    assert res_ceo.status_code == 403

    # 2. Sales Director -> 403 FORBIDDEN_ROLE
    res_sales = app_client.post(
        f"/api/v1/documents/{doc_hr.id}/rollback",
        headers={"Authorization": f"Bearer {sales_token}"},
        json={"reason": "Sales muốn hoàn tác"},
    )
    assert res_sales.status_code == 403

    # 3. CFO on HR pillar doc -> 403 FORBIDDEN_SCOPE
    res_cfo_hr = app_client.post(
        f"/api/v1/documents/{doc_hr.id}/rollback",
        headers={"Authorization": f"Bearer {cfo_token}"},
        json={"reason": "CFO muốn hoàn tác tài liệu HR"},
    )
    assert res_cfo_hr.status_code == 403
    assert res_cfo_hr.json()["error"]["code"] == "FORBIDDEN_SCOPE"

    # 4. CFO on FIN pillar doc -> 200 OK
    doc_fin, _ = setup_committed_doc(
        db_session, reviewer_user, doc_type=DocType.INVOICE, pillars=["FIN"]
    )
    res_cfo_fin = app_client.post(
        f"/api/v1/documents/{doc_fin.id}/rollback",
        headers={"Authorization": f"Bearer {cfo_token}"},
        json={"reason": "CFO hoàn tác tài liệu Tài chính"},
    )
    assert res_cfo_fin.status_code == 200
    assert res_cfo_fin.json()["data"]["document"]["status"] == "ROLLED_BACK"

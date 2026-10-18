"""Tests for C1 Manual Form (EP-21) and C2 Natural Language (EP-22) endpoints (T-204).

Implements TC-IDP-004 and TC-IDP-005.
"""

from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.main import app
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Role, User
from app.modules.auth.token import create_access_token
from app.modules.idp.enums import (
    DocumentKind,
    InputChannel,
    RoutingDecision,
    SourceLocationKind,
)
from app.modules.idp.models import ExtractedField, ExtractionJob, SourceDocument


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
def test_user_token(db_session: Session) -> tuple[User, str]:
    """Fixture providing user and token for reviewer."""
    cfg = get_config()
    stmt = select(User).where(User.email == "reviewer@abc.demo", User.deleted_at.is_(None))
    user = db_session.execute(stmt).scalar_one_or_none()
    if not user:
        role = db_session.execute(select(Role).where(Role.code == "ROLE-05")).scalar_one()
        user = User(
            email="reviewer@abc.demo",
            password_hash="$fake_hash",
            full_name="Nguyễn Văn Duyệt",
            salutation="anh",
            role_id=role.id,
            is_demo_account=True,
        )
        db_session.add(user)
        db_session.commit()

    token, _ = create_access_token(user, cfg)
    return user, token


# ---------------------------------------------------------------------------
# TC-IDP-004: EP-21 Form C1 Manual Entry
# ---------------------------------------------------------------------------


def test_tc_idp_004_manual_entry_tax_code_validation_and_fields(
    app_client: TestClient,
    test_user_token: tuple[User, str],
    db_session: Session,
) -> None:
    """TC-IDP-004: Invalid tax code -> 422; valid -> kind=MANUAL, confidence=1.0, source=manual."""
    _user, token = test_user_token
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "idemp-manual-001",
    }

    # 1. Invalid tax_code (e.g. 5 digits) -> 422 VALIDATION_ERROR
    invalid_payload = {
        "doc_type": "INVOICE",
        "fields": {
            "invoice_number": "HD-00123",
            "customer_name": "Công ty TNHH Thử Nghiệm",
            "customer_tax_code": "12345",  # Invalid! Must be 10 or 13 digits
            "total_amount": 10000000,
        },
    }
    resp_invalid = app_client.post(
        "/api/v1/documents/manual",
        headers=headers,
        json=invalid_payload,
    )
    assert resp_invalid.status_code == 422
    err_body = resp_invalid.json()
    assert err_body["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in err_body["error"]
    assert "fields" in err_body["error"]["details"]
    err_fields = err_body["error"]["details"]["fields"]
    assert any(f["field"] == "customer_tax_code" for f in err_fields)

    # 2. Valid manual entry with 10-digit tax code
    valid_payload = {
        "doc_type": "INVOICE",
        "fields": {
            "invoice_number": "HD-00123",
            "customer_name": "Công ty TNHH Thử Nghiệm",
            "customer_tax_code": "0101234567",  # Valid 10 digits
            "subtotal": 10000000,
            "vat_rate": 0.10,
            "vat_amount": 1000000,
            "total_amount": 11000000,
        },
    }
    resp_valid = app_client.post(
        "/api/v1/documents/manual",
        headers=headers,
        json=valid_payload,
    )
    assert resp_valid.status_code == 201
    data = resp_valid.json()["data"]
    doc_id = UUID(data["id"])
    assert data["kind"] == "MANUAL"
    assert data["channel"] == "C1"
    assert data["status"] == "NEEDS_REVIEW"

    # Verify database: SourceDocument, ExtractionJob, and ExtractedFields
    doc = db_session.get(SourceDocument, doc_id)
    assert doc is not None
    assert doc.kind == DocumentKind.MANUAL
    assert doc.channel == InputChannel.C1
    assert doc.manual_payload == valid_payload["fields"]

    # Verify ExtractedFields: confidence = 1.0, source_kind = MANUAL
    stmt_fields = select(ExtractedField).where(ExtractedField.source_document_id == doc_id)
    fields = db_session.execute(stmt_fields).scalars().all()
    assert len(fields) == len(valid_payload["fields"])
    for f in fields:
        assert f.confidence == 1.0
        assert f.source_kind == SourceLocationKind.MANUAL
        assert f.source_location == {"kind": "manual"}

    # Verify Audit log
    audit = db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "document.manual_create",
            AuditLog.target_id == doc_id,
        )
    ).scalar_one_or_none()
    assert audit is not None


# ---------------------------------------------------------------------------
# TC-IDP-005: EP-22 Natural Language Entry & Kill Switch
# ---------------------------------------------------------------------------


def test_tc_idp_005_natural_language_draft_and_kill_switch(
    app_client: TestClient,
    test_user_token: tuple[User, str],
    db_session: Session,
) -> None:
    """TC-IDP-005: Natural text -> L2 draft, source=transcript, never STP; kill switch -> 423."""
    _user, token = test_user_token
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "idemp-nl-001",
    }

    prompt_text = "Hóa đơn 0001234 cho Công ty Minh Phát 25 triệu ngày 05/10/2026"
    resp = app_client.post(
        "/api/v1/documents/natural-language",
        headers=headers,
        json={"text": prompt_text},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    doc_id = UUID(data["id"])
    assert data["kind"] == "TRANSCRIPT"
    assert data["channel"] == "C2"
    assert data["autonomy_level"] == "L2"
    assert data["status"] == "NEEDS_REVIEW"

    # Verify database
    doc = db_session.get(SourceDocument, doc_id)
    assert doc is not None
    assert doc.kind == DocumentKind.TRANSCRIPT
    assert doc.channel == InputChannel.C2

    # Verify ExtractedFields: source_location.kind = transcript
    stmt_fields = select(ExtractedField).where(ExtractedField.source_document_id == doc_id)
    fields = db_session.execute(stmt_fields).scalars().all()
    assert len(fields) >= 1
    field_dict = {f.field_key: f for f in fields}

    assert "invoice_number" in field_dict
    assert field_dict["invoice_number"].value == "0001234"
    assert field_dict["invoice_number"].source_kind == SourceLocationKind.TRANSCRIPT

    assert "total_amount" in field_dict
    assert field_dict["total_amount"].value == 25_000_000

    # Verify Job is never STP
    stmt_job = select(ExtractionJob).where(ExtractionJob.source_document_id == doc_id)
    job = db_session.execute(stmt_job).scalars().first()
    assert job is not None
    assert job.routing_decision == RoutingDecision.REVIEW

    # Audit log verified
    audit = db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "document.nl_create",
            AuditLog.target_id == doc_id,
        )
    ).scalar_one_or_none()
    assert audit is not None

    # Test Kill Switch L0 -> 423 AI_DISABLED
    cfg = get_config()
    cfg.ai_kill_switch = True
    try:
        resp_disabled = app_client.post(
            "/api/v1/documents/natural-language",
            headers=headers,
            json={"text": "Một hóa đơn khác"},
        )
        assert resp_disabled.status_code == 423
        assert resp_disabled.json()["error"]["code"] == "AI_DISABLED"
    finally:
        cfg.ai_kill_switch = False

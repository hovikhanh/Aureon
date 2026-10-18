"""Tests for IDP upload endpoints (EP-20, EP-40) and deduplication (T-203).

Implements TC-IDP-001, TC-IDP-002, TC-IDP-003, TC-UC07-001, and TC-UC07-002.
"""

import io
import time
from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.core.storage import get_storage_service
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Role, User
from app.modules.auth.token import create_access_token
from app.modules.idp.models import SourceDocument


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
    """Fixture providing user and bearer token for each of the 5 demo roles."""
    from sqlalchemy.orm import joinedload

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
            # Fallback create if DB was wiped
            stmt_role = select(Role).where(Role.code == role_code)
            role = db_session.execute(stmt_role).scalar_one_or_none()
            if not role:
                all_pillars = ["FIN", "CUS", "OPS", "HR"]
                scope = all_pillars if role_code in ("ROLE-01", "ROLE-05") else ["FIN"]
                review_p = ["FIN"] if role_code in ("ROLE-02", "ROLE-05") else []
                role = Role(
                    code=role_code,
                    name_i18n_key=f"shell.roles.{role_code}",
                    pillar_scope=scope,
                    pillar_agg_scope=[],
                    review_pillars=review_p,
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

        token_str, _ = create_access_token(user, cfg)
        user_tokens[role_code] = (user, token_str)

    db_session.commit()
    return user_tokens


def generate_dummy_pdf(num_pages: int = 1, extra_padding: int = 0) -> bytes:
    """Generate minimal valid PDF bytes with specified page count and padding."""
    lines = [
        b"%PDF-1.4",
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
    ]
    page_refs = " ".join([f"{i + 3} 0 R" for i in range(num_pages)])
    kids_entry = f"2 0 obj << /Type /Pages /Kids [{page_refs}] /Count {num_pages} >> endobj"
    lines.append(kids_entry.encode())

    for i in range(num_pages):
        obj_id = i + 3
        lines.append(f"{obj_id} 0 obj << /Type /Page /Parent 2 0 R >> endobj".encode())

    lines.append(b"xref")
    lines.append(f"0 {num_pages + 3}".encode())
    lines.append(b"trailer << /Root 1 0 R >>")
    lines.append(b"%%EOF")

    pdf_base = b"\n".join(lines)
    if extra_padding > 0:
        pdf_base += b"\n% " + (b"0" * extra_padding)
    return pdf_base


# ---------------------------------------------------------------------------
# TC-IDP-001: 5MB PDF Upload Stream <= 2s
# ---------------------------------------------------------------------------


def test_tc_idp_001_upload_5mb_pdf_stream(
    app_client: TestClient,
    seed_test_users: dict[str, tuple[User, str]],
    db_session: Session,
) -> None:
    """TC-IDP-001: 5MB PDF upload succeeds in <= 2s, stored on MinIO, sha256 valid."""
    _, token = seed_test_users["ROLE-01"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate 5MB PDF
    five_mb = 5 * 1024 * 1024
    pdf_bytes = generate_dummy_pdf(num_pages=3, extra_padding=five_mb)

    start_time = time.perf_counter()
    resp = app_client.post(
        "/api/v1/documents",
        headers=headers,
        data={"channel": "C3", "doc_type_hint": "INVOICE"},
        files={"file": ("invoice_5mb.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    elapsed = time.perf_counter() - start_time

    assert resp.status_code == 201, resp.text
    # Performance requirement: <= 2.0s
    assert elapsed <= 2.0, f"Upload took {elapsed:.2f}s, exceeding 2.0s threshold"

    body = resp.json()
    assert "data" in body
    data = body["data"]
    doc_id = UUID(data["id"])
    assert data["status"] == "UPLOADED"
    assert data["doc_type"] == "INVOICE"
    assert data["page_count"] == 3
    assert data["size_bytes"] >= five_mb

    # Verify database record
    doc = db_session.get(SourceDocument, doc_id)
    assert doc is not None
    assert doc.sha256 is not None
    assert doc.storage_key is not None

    # Verify storage in MinIO
    storage = get_storage_service()
    content = storage.get_object(doc.storage_key)
    assert len(content) == len(pdf_bytes)


# ---------------------------------------------------------------------------
# TC-IDP-002: Validation (File too large, pages > 50, invalid format)
# ---------------------------------------------------------------------------


def test_tc_idp_002_file_too_large_and_unsupported_media_type(
    app_client: TestClient,
    seed_test_users: dict[str, tuple[User, str]],
    db_session: Session,
) -> None:
    """TC-IDP-002: >20MB or >50 pages -> 413; .zip/.exe -> 415; no document created."""
    _, token = seed_test_users["ROLE-01"]
    headers = {"Authorization": f"Bearer {token}"}
    initial_doc_count = len(db_session.execute(select(SourceDocument)).scalars().all())

    # 1. > 20 MB file -> 413 FILE_TOO_LARGE
    twenty_one_mb = 21 * 1024 * 1024
    large_pdf = generate_dummy_pdf(num_pages=1, extra_padding=twenty_one_mb)
    resp_large = app_client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("large.pdf", io.BytesIO(large_pdf), "application/pdf")},
    )
    assert resp_large.status_code == 413
    assert resp_large.json()["error"]["code"] == "FILE_TOO_LARGE"

    # 2. > 50 pages -> 413 FILE_TOO_LARGE
    fifty_one_page_pdf = generate_dummy_pdf(num_pages=51)
    resp_pages = app_client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("many_pages.pdf", io.BytesIO(fifty_one_page_pdf), "application/pdf")},
    )
    assert resp_pages.status_code == 413
    assert resp_pages.json()["error"]["code"] == "FILE_TOO_LARGE"

    # 3. Unsupported extension (.zip, .exe) -> 415 UNSUPPORTED_MEDIA_TYPE
    resp_unsupported = app_client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("malware.zip", io.BytesIO(b"PK00fake"), "application/zip")},
    )
    assert resp_unsupported.status_code == 415
    assert resp_unsupported.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"

    # Verify no documents were created
    current_doc_count = len(db_session.execute(select(SourceDocument)).scalars().all())
    assert current_doc_count == initial_doc_count


# ---------------------------------------------------------------------------
# TC-IDP-003: SHA-256 Deduplication
# ---------------------------------------------------------------------------


def test_tc_idp_003_sha256_deduplication(
    app_client: TestClient,
    seed_test_users: dict[str, tuple[User, str]],
    db_session: Session,
) -> None:
    """TC-IDP-003: Re-uploading identical file creates DUPLICATE doc with duplicate_of_id."""
    _, token = seed_test_users["ROLE-02"]
    headers = {"Authorization": f"Bearer {token}"}
    pdf_bytes = generate_dummy_pdf(num_pages=2, extra_padding=1024)

    # 1. First upload: UPLOADED
    resp1 = app_client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("contract.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp1.status_code == 201
    doc1_id = resp1.json()["data"]["id"]
    assert resp1.json()["data"]["status"] == "UPLOADED"
    assert "meta" not in resp1.json() or resp1.json().get("meta") is None

    # 2. Second upload identical file: DUPLICATE
    resp2 = app_client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("contract_copy.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp2.status_code == 201
    body2 = resp2.json()
    data2 = body2["data"]
    assert data2["status"] == "DUPLICATE"
    assert data2["duplicate_of_id"] == doc1_id

    # Check warning meta
    assert "meta" in body2
    assert body2["meta"]["warning"]["code"] == "DUPLICATE_DOCUMENT"
    assert body2["meta"]["warning"]["duplicate_of_id"] == doc1_id

    # Verify audit log for duplicate
    doc2_id = UUID(data2["id"])
    audit_entry = db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "document.upload_duplicate",
            AuditLog.target_id == doc2_id,
        )
    ).scalar_one_or_none()
    assert audit_entry is not None


# ---------------------------------------------------------------------------
# TC-UC07-001 & TC-UC07-002: Batch Creation and Upload Scoping
# ---------------------------------------------------------------------------


def test_tc_uc07_001_batch_creation_permissions(
    app_client: TestClient,
    seed_test_users: dict[str, tuple[User, str]],
    db_session: Session,
) -> None:
    """TC-UC07-001: EP-40 restricted to ROLE-01 and ROLE-05; ROLE-02..04 return 403."""
    # ROLE-01 (CEO): 201 Created with 7 checklist items
    _, ceo_token = seed_test_users["ROLE-01"]
    resp_ceo = app_client.post(
        "/api/v1/onboarding/batches",
        headers={"Authorization": f"Bearer {ceo_token}"},
        json={"label": "Onboarding Q4"},
    )
    assert resp_ceo.status_code == 201
    data_ceo = resp_ceo.json()["data"]
    batch_id = UUID(data_ceo["batch_id"])
    assert len(data_ceo["checklist"]) == 7
    assert data_ceo["upload_endpoint"] == "/api/v1/documents"

    # Audit log verified
    audit = db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "onboarding.batch_create",
            AuditLog.target_id == batch_id,
        )
    ).scalar_one_or_none()
    assert audit is not None

    # ROLE-05 (Reviewer): 201 Created
    _, rev_token = seed_test_users["ROLE-05"]
    resp_rev = app_client.post(
        "/api/v1/onboarding/batches",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={},
    )
    assert resp_rev.status_code == 201

    # ROLE-02 (CFO), ROLE-03 (Sales), ROLE-04 (HR): 403 FORBIDDEN_ROLE
    for role_code in ["ROLE-02", "ROLE-03", "ROLE-04"]:
        _, token = seed_test_users[role_code]
        resp_forbidden = app_client.post(
            "/api/v1/onboarding/batches",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert resp_forbidden.status_code == 403
        assert resp_forbidden.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_tc_uc07_002_batch_upload_scoping(
    app_client: TestClient,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-UC07-002: Uploading to a batch_id is restricted to ROLE-01 and ROLE-05."""
    test_batch_id = uuid4()
    pdf_bytes = generate_dummy_pdf(num_pages=1, extra_padding=512)

    # 1. CFO (ROLE-02) upload with batch_id -> 403 FORBIDDEN_ROLE
    _, cfo_token = seed_test_users["ROLE-02"]
    resp_cfo = app_client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {cfo_token}"},
        data={"batch_id": str(test_batch_id)},
        files={"file": ("bctc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp_cfo.status_code == 403
    assert resp_cfo.json()["error"]["code"] == "FORBIDDEN_ROLE"

    # 2. CEO (ROLE-01) upload with batch_id -> 201 OK
    _, ceo_token = seed_test_users["ROLE-01"]
    resp_ceo = app_client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {ceo_token}"},
        data={"batch_id": str(test_batch_id)},
        files={"file": ("bctc_ceo.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp_ceo.status_code == 201
    assert resp_ceo.json()["data"]["batch_id"] == str(test_batch_id)

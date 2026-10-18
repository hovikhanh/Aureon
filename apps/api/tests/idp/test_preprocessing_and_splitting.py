"""Tests for Preprocessing, OCR analysis, and Multi-doc splitting (T-206).

Implements:
- TC-IDP-008: Preprocessing & OCR detection (text_layer_exists, ocr_used, ocr_confidence)
- TC-IDP-010: Multi-document PDF splitting into child documents (parent_id, page_range)
- TC-IDP-040: Corrupted file failure handling (DocumentStatus.FAILED) & performance p95 <= 60s
"""

import time
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.storage import get_storage_service
from app.main import app
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Role, User
from app.modules.idp.enums import DocType, DocumentKind, DocumentStatus, InputChannel
from app.modules.idp.models import DocumentPage, SourceDocument
from app.modules.idp.preprocessing import (
    check_text_layer_quality,
    preprocess_document,
    split_multi_document,
)


def make_test_pdf_bytes(pages_text: list[str]) -> bytes:
    """Construct a minimal valid multi-page PDF in raw bytes."""
    objects: list[bytes] = []
    page_obj_ids: list[int] = []
    current_id = 3

    for text in pages_text:
        content = f"BT /F1 12 Tf ({text}) Tj ET".encode()
        stream_id = current_id
        current_id += 1
        objects.append(
            f"{stream_id} 0 obj\n<< /Length {len(content)} >>\nstream\n".encode("latin1")
            + content
            + b"\nendstream\nendobj\n"
        )
        page_id = current_id
        current_id += 1
        page_obj_ids.append(page_id)
        page_obj = (
            f"{page_id} 0 obj\n<< /Type /Page /Parent 2 0 R /Contents {stream_id} 0 R >>\nendobj\n"
        ).encode("latin1")
        objects.append(page_obj)

    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    pages_obj = (
        f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_ids)} >>\nendobj\n"
    ).encode("latin1")
    catalog_obj = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"

    return b"%PDF-1.4\n" + catalog_obj + pages_obj + b"".join(objects) + b"%%EOF"


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
def test_uploader(db_session: Session) -> User:
    role = db_session.execute(select(Role).where(Role.code == "ROLE-02")).scalar_one_or_none()
    if not role:
        role = Role(
            code="ROLE-02",
            name_i18n_key="shell.roles.ROLE-02",
            pillar_scope=["FIN"],
            pillar_agg_scope=[],
            review_pillars=["FIN"],
            home_route="/dashboard",
        )
        db_session.add(role)
        db_session.flush()

    user = db_session.execute(
        select(User).where(User.email == "uploader_t206@abc.demo")
    ).scalar_one_or_none()
    if not user:
        user = User(
            email="uploader_t206@abc.demo",
            password_hash="$fake_hash",
            full_name="Uploader T206",
            salutation="anh",
            role_id=role.id,
            is_demo_account=True,
        )
        db_session.add(user)
        db_session.flush()

    return user


def create_db_document(
    db: Session,
    uploader: User,
    file_bytes: bytes,
    filename: str = "test.pdf",
    mime_type: str = "application/pdf",
    doc_type: DocType = DocType.INVOICE,
) -> SourceDocument:
    doc_id = uuid4()
    storage_key = f"documents/{doc_id}/{filename}"
    storage = get_storage_service()
    storage.put_object(storage_key, file_bytes, content_type=mime_type)

    doc = SourceDocument(
        id=doc_id,
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename=filename,
        mime_type=mime_type,
        size_bytes=len(file_bytes),
        page_count=1,
        storage_key=storage_key,
        doc_type=doc_type,
        pillars=["FIN"],
        status=DocumentStatus.UPLOADED,
        uploaded_by_id=uploader.id,
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# TC-IDP-008: Preprocessing & OCR quality checks
# ---------------------------------------------------------------------------


def test_tc_idp_008_quality_checker_unit() -> None:
    """TC-IDP-008: Check text layer quality threshold (>=20 chars, >=60% valid ratio)."""
    # Empty
    is_good, ratio = check_text_layer_quality("")
    assert is_good is False
    assert ratio == 0.0

    # Short (< 20 valid characters)
    is_good, ratio = check_text_layer_quality("Short text 123")
    assert is_good is False
    assert ratio == 1.0

    # Good text layer
    good_text = "Hóa đơn giá trị gia tăng số 0012345 - Công ty TNHH Minh Phát"
    is_good, ratio = check_text_layer_quality(good_text)
    assert is_good is True
    assert ratio == 1.0

    # Junk characters (ratio < 0.60)
    junk = "".join(chr(i) for i in range(1, 15)) * 10
    is_good, ratio = check_text_layer_quality(junk)
    assert is_good is False
    assert ratio < 0.60


def test_tc_idp_008_pdf_good_text_layer_no_ocr(
    db_session: Session,
    test_uploader: User,
) -> None:
    """TC-IDP-008: PDF with good text layer -> text_layer_exists=True, ocr_used=False."""
    text_content = "Hóa đơn giá trị gia tăng số 0012345 - Công ty TNHH Minh Phát ngày 15/09/2026"
    pdf_bytes = make_test_pdf_bytes([text_content])

    doc = create_db_document(db_session, test_uploader, pdf_bytes, filename="invoice_good.pdf")
    processed = preprocess_document(db_session, doc.id)

    assert processed.status == DocumentStatus.CLASSIFYING
    assert processed.page_count == 1

    # Check document_pages
    stmt = select(DocumentPage).where(DocumentPage.source_document_id == doc.id)
    pages = db_session.execute(stmt).scalars().all()
    assert len(pages) == 1
    page = pages[0]

    assert page.page_number == 1
    assert page.text_layer_exists is True
    assert page.text_layer_quality is not None and float(page.text_layer_quality) >= 0.90
    assert page.ocr_used is False
    assert page.ocr_confidence is None
    assert "0012345" in (page.text_content or "")


def test_tc_idp_008_scanned_image_triggers_ocr(
    db_session: Session,
    test_uploader: User,
) -> None:
    """TC-IDP-008: Image file or scan without text layer -> ocr_used=True, ocr_confidence stored."""
    # Simulate an image file with dummy PNG header
    dummy_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    doc = create_db_document(
        db_session,
        test_uploader,
        dummy_image,
        filename="scanned_invoice.png",
        mime_type="image/png",
    )
    processed = preprocess_document(db_session, doc.id)

    assert processed.status == DocumentStatus.CLASSIFYING
    assert processed.page_count == 1

    stmt = select(DocumentPage).where(DocumentPage.source_document_id == doc.id)
    pages = db_session.execute(stmt).scalars().all()
    assert len(pages) == 1
    page = pages[0]

    assert page.page_number == 1
    assert page.text_layer_exists is False
    assert page.ocr_used is True
    assert page.ocr_confidence is not None
    assert float(page.ocr_confidence) == 0.88
    assert page.text_content is not None
    assert "OCR trang 1" in page.text_content


def test_tc_idp_008_pdf_with_junk_text_triggers_ocr(
    db_session: Session,
    test_uploader: User,
) -> None:
    """TC-IDP-008: PDF with junk/empty text layer -> ocr_used=True, ocr_confidence stored."""
    # Short junk text < 20 chars
    pdf_bytes = make_test_pdf_bytes(["abc"])
    doc = create_db_document(db_session, test_uploader, pdf_bytes, filename="invoice_junk.pdf")
    processed = preprocess_document(db_session, doc.id)

    assert processed.status == DocumentStatus.CLASSIFYING
    stmt = select(DocumentPage).where(DocumentPage.source_document_id == doc.id)
    pages = db_session.execute(stmt).scalars().all()
    assert len(pages) == 1
    page = pages[0]

    assert page.text_layer_exists is False
    assert page.ocr_used is True
    assert page.ocr_confidence is not None


# ---------------------------------------------------------------------------
# TC-IDP-010: Multi-document splitting
# ---------------------------------------------------------------------------


def test_tc_idp_010_multi_document_split_10_invoices(
    db_session: Session,
    test_uploader: User,
) -> None:
    """TC-IDP-010 Part 1: Merged PDF with 10 invoices splits into 10 child SourceDocuments."""
    invoice_pages = [
        f"Hóa đơn GTGT #{i:03d} - Khách hàng Công ty {i} - Tiền 25.000.000 VND"
        for i in range(1, 11)
    ]
    pdf_bytes = make_test_pdf_bytes(invoice_pages)

    parent_doc = create_db_document(
        db_session,
        test_uploader,
        pdf_bytes,
        filename="10_invoices_merged.pdf",
    )
    # Preprocess parent document
    preprocess_document(db_session, parent_doc.id)

    stmt_parent_pages = select(DocumentPage).where(DocumentPage.source_document_id == parent_doc.id)
    assert len(db_session.execute(stmt_parent_pages).scalars().all()) == 10

    # Split into 10 1-page child documents: [(1, 1), (2, 2), ..., (10, 10)]
    split_ranges = [(i, i) for i in range(1, 11)]
    children = split_multi_document(
        db=db_session,
        parent_id=parent_doc.id,
        split_ranges=split_ranges,
        actor_user_id=test_uploader.id,
    )

    assert len(children) == 10

    for idx, child in enumerate(children, start=1):
        # Verify parent_id and page_range
        assert child.parent_id == parent_doc.id
        assert child.page_range == (idx, idx)
        assert child.page_count == 1
        assert child.status == DocumentStatus.UPLOADED

        # Verify child pages cloned correctly
        stmt_child_pages = select(DocumentPage).where(DocumentPage.source_document_id == child.id)
        c_pages = db_session.execute(stmt_child_pages).scalars().all()
        assert len(c_pages) == 1
        assert c_pages[0].page_number == 1
        assert f"#{idx:03d}" in (c_pages[0].text_content or "")

    # Verify audit log for split
    stmt_audit = select(AuditLog).where(
        AuditLog.action == "document.split",
        AuditLog.target_id == parent_doc.id,
    )
    audit = db_session.execute(stmt_audit).scalar_one_or_none()
    assert audit is not None
    assert audit.after is not None
    assert audit.after.get("split_count") == 10


def test_tc_idp_010_split_ranges_adjustment(
    db_session: Session,
    test_uploader: User,
) -> None:
    """TC-IDP-010 Part 2: Split multi-document with customized/adjusted page ranges."""
    pages = [f"Page {i} content text >= 20 characters for test" for i in range(1, 11)]
    pdf_bytes = make_test_pdf_bytes(pages)

    parent_doc = create_db_document(
        db_session,
        test_uploader,
        pdf_bytes,
        filename="custom_split.pdf",
    )
    preprocess_document(db_session, parent_doc.id)

    # Split into 3 custom ranges: (1..3), (4..7), (8..10)
    custom_ranges = [(1, 3), (4, 7), (8, 10)]
    children = split_multi_document(
        db=db_session,
        parent_id=parent_doc.id,
        split_ranges=custom_ranges,
        actor_user_id=test_uploader.id,
    )

    assert len(children) == 3

    assert children[0].page_range == (1, 3)
    assert children[0].page_count == 3
    assert children[1].page_range == (4, 7)
    assert children[1].page_count == 4
    assert children[2].page_range == (8, 10)
    assert children[2].page_count == 3


# ---------------------------------------------------------------------------
# TC-IDP-040: Failure handling & Performance
# ---------------------------------------------------------------------------


def test_tc_idp_040_corrupted_file_fails_gracefully(
    db_session: Session,
    test_uploader: User,
) -> None:
    """TC-IDP-040 Part 1: Corrupted file transitions to FAILED with clear reason."""
    corrupted_bytes = b"CORRUPTED_NOT_A_PDF_DATA_HERE"
    doc = create_db_document(
        db_session,
        test_uploader,
        corrupted_bytes,
        filename="bad_corrupted.pdf",
    )

    # Must NOT raise unhandled exception
    failed_doc = preprocess_document(db_session, doc.id)

    assert failed_doc.status == DocumentStatus.FAILED
    assert failed_doc.status_reason is not None
    reason = failed_doc.status_reason.lower()
    assert "thất bại" in reason or "failed" in reason

    # Check audit log
    stmt_audit = select(AuditLog).where(
        AuditLog.action == "document.preprocess_failed",
        AuditLog.target_id == doc.id,
    )
    audit = db_session.execute(stmt_audit).scalar_one_or_none()
    assert audit is not None


def test_tc_idp_040_performance_under_60_seconds(
    db_session: Session,
    test_uploader: User,
) -> None:
    """TC-IDP-040 Part 2: 10-page document preprocessing completes in <= 60 seconds (NFR-IDP-01)."""
    pages = [f"Page {i} invoice content text >= 20 characters for timing" for i in range(1, 11)]
    pdf_bytes = make_test_pdf_bytes(pages)

    doc = create_db_document(db_session, test_uploader, pdf_bytes, filename="perf_10_pages.pdf")

    start_time = time.perf_counter()
    processed = preprocess_document(db_session, doc.id)
    elapsed = time.perf_counter() - start_time

    assert processed.status == DocumentStatus.CLASSIFYING
    assert processed.page_count == 10
    assert elapsed < 60.0, f"Processing took {elapsed:.2f}s, exceeding 60s limit"


def test_celery_preprocess_document_task(
    db_session: Session,
    test_uploader: User,
) -> None:
    """Test Celery preprocess_document_task runs and processes document."""
    from app.workers.idp import preprocess_document_task

    pdf_bytes = make_test_pdf_bytes(["Test invoice page 1 with at least twenty characters here."])
    doc = create_db_document(db_session, test_uploader, pdf_bytes, filename="celery_doc.pdf")

    res = preprocess_document_task.apply(kwargs={"document_id": str(doc.id), "db": db_session})
    val = res.get()
    assert val["document_id"] == str(doc.id)
    assert val["status"] == "CLASSIFYING"
    assert val["page_count"] == 1

"""Tests for Document State Machine (04 §8.2, TC-IDP-034) and MinIO Storage Service (T-202).

Validates all 14-state transitions, actor permission guards, 7-day undo deadline,
and MinIO S3 operations (upload, download, delete, presigned URL).
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.storage import StorageService
from app.modules.idp.enums import DocumentKind, DocumentStatus, InputChannel
from app.modules.idp.models import SourceDocument
from app.modules.idp.state_machine import (
    DocumentStateMachine,
    ForbiddenStateTransitionError,
    InvalidStateTransitionError,
    UndoDeadlineExpiredError,
)

ALL_STATUSES = list(DocumentStatus)


def make_doc(
    status: DocumentStatus = DocumentStatus.UPLOADED,
    pillars: list[str] | None = None,
    committed_at: datetime | None = None,
    undo_deadline: datetime | None = None,
) -> SourceDocument:
    """Helper to create a SourceDocument instance for state testing."""
    return SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        uploaded_by_id=uuid4(),
        pillars=pillars or ["FIN"],
        status=status,
        committed_at=committed_at,
        undo_deadline=undo_deadline,
    )


# ---------------------------------------------------------------------------
# TC-IDP-034: State Machine Tests
# ---------------------------------------------------------------------------


def test_tc_idp_034_all_valid_transitions_succeed() -> None:
    """Verify that every valid transition defined in DocumentStateMachine succeeds."""
    valid_map = DocumentStateMachine.VALID_TRANSITIONS

    for from_status, target_statuses in valid_map.items():
        for to_status in target_statuses:
            # Set up doc with appropriate properties for the transition
            doc = make_doc(status=from_status, pillars=["FIN"])
            if to_status == DocumentStatus.ROLLED_BACK:
                now = datetime.now(UTC)
                doc.committed_at = now - timedelta(days=2)
                doc.undo_deadline = doc.committed_at + timedelta(days=7)

            actor = "ROLE-05"  # Reviewer has broad permission
            reason = "Test rejection reason" if to_status == DocumentStatus.REJECTED else None

            res = DocumentStateMachine.transition(
                doc, to_status, actor_role=actor, reason=reason
            )
            assert res == to_status
            assert doc.status == to_status


@pytest.mark.parametrize(
    ("from_status", "invalid_target"),
    [
        (DocumentStatus.UPLOADED, DocumentStatus.COMMITTED),
        (DocumentStatus.UPLOADED, DocumentStatus.APPROVED),
        (DocumentStatus.UPLOADED, DocumentStatus.IN_REVIEW),
        (DocumentStatus.PREPROCESSING, DocumentStatus.COMMITTED),
        (DocumentStatus.CLASSIFYING, DocumentStatus.AUTO_APPROVED),
        (DocumentStatus.EXTRACTING, DocumentStatus.IN_REVIEW),
        (DocumentStatus.VALIDATING, DocumentStatus.COMMITTED),
        (DocumentStatus.NEEDS_REVIEW, DocumentStatus.COMMITTED),
        (DocumentStatus.NEEDS_REVIEW, DocumentStatus.APPROVED),
        (DocumentStatus.IN_REVIEW, DocumentStatus.PREPROCESSING),
        (DocumentStatus.COMMITTED, DocumentStatus.NEEDS_REVIEW),
        (DocumentStatus.COMMITTED, DocumentStatus.PREPROCESSING),
        (DocumentStatus.ROLLED_BACK, DocumentStatus.UPLOADED),
        (DocumentStatus.ROLLED_BACK, DocumentStatus.PREPROCESSING),
        (DocumentStatus.FAILED, DocumentStatus.COMMITTED),
        (DocumentStatus.DUPLICATE, DocumentStatus.COMMITTED),
    ],
)
def test_tc_idp_034_invalid_transitions_raise_conflict_state(
    from_status: DocumentStatus, invalid_target: DocumentStatus
) -> None:
    """Verify invalid transitions raise InvalidStateTransitionError with code CONFLICT_STATE."""
    doc = make_doc(status=from_status)
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        DocumentStateMachine.transition(doc, invalid_target, actor_role="ROLE-05")

    assert exc_info.value.code == "CONFLICT_STATE"
    assert exc_info.value.current_status == from_status
    assert exc_info.value.target_status == invalid_target


def test_tc_idp_034_rejection_requires_non_empty_reason() -> None:
    """IN_REVIEW -> REJECTED requires a non-empty reason."""
    doc = make_doc(status=DocumentStatus.IN_REVIEW)
    with pytest.raises(InvalidStateTransitionError, match="reason is required"):
        DocumentStateMachine.transition(
            doc, DocumentStatus.REJECTED, actor_role="ROLE-05", reason=None
        )


def test_tc_idp_034_ceo_cannot_rollback() -> None:
    """04 §8.2, 02 §3.4: CEO (ROLE-01) is strictly forbidden from rolling back committed docs."""
    now = datetime.now(UTC)
    doc = make_doc(
        status=DocumentStatus.COMMITTED,
        committed_at=now - timedelta(days=1),
        undo_deadline=now + timedelta(days=6),
    )
    with pytest.raises(ForbiddenStateTransitionError) as exc_info:
        DocumentStateMachine.transition(
            doc, DocumentStatus.ROLLED_BACK, actor_role="ROLE-01"
        )
    assert exc_info.value.code == "FORBIDDEN_ROLE"
    assert "ROLE-01" in exc_info.value.message


def test_tc_idp_034_cfo_cannot_rollback_hr_document() -> None:
    """CFO (ROLE-02) can only rollback FIN documents, not HR."""
    now = datetime.now(UTC)
    doc = make_doc(
        status=DocumentStatus.COMMITTED,
        pillars=["HR"],
        committed_at=now - timedelta(days=1),
        undo_deadline=now + timedelta(days=6),
    )
    with pytest.raises(ForbiddenStateTransitionError) as exc_info:
        DocumentStateMachine.transition(
            doc, DocumentStatus.ROLLED_BACK, actor_role="ROLE-02"
        )
    assert exc_info.value.code == "FORBIDDEN_ROLE"
    assert "CFO" in exc_info.value.message


def test_tc_idp_034_undo_deadline_expired_raises_undo_expired() -> None:
    """Attempting rollback after undo_deadline (> 7 days) raises UndoDeadlineExpiredError."""
    past = datetime.now(UTC) - timedelta(days=8)
    deadline = past + timedelta(days=7)  # expired yesterday
    doc = make_doc(
        status=DocumentStatus.COMMITTED,
        pillars=["FIN"],
        committed_at=past,
        undo_deadline=deadline,
    )
    with pytest.raises(UndoDeadlineExpiredError) as exc_info:
        DocumentStateMachine.transition(
            doc, DocumentStatus.ROLLED_BACK, actor_role="ROLE-05"
        )
    assert exc_info.value.code == "UNDO_EXPIRED"


def test_tc_idp_034_manual_retry_permissions() -> None:
    """FAILED -> PREPROCESSING retry permissions."""
    doc = make_doc(status=DocumentStatus.FAILED, pillars=["FIN"])

    # Reviewer can retry
    DocumentStateMachine.transition(doc, DocumentStatus.PREPROCESSING, actor_role="ROLE-05")
    assert doc.status == DocumentStatus.PREPROCESSING

    # Reset
    doc.status = DocumentStatus.FAILED
    # CFO can retry FIN
    DocumentStateMachine.transition(doc, DocumentStatus.PREPROCESSING, actor_role="ROLE-02")
    assert doc.status == DocumentStatus.PREPROCESSING

    # Reset
    doc.status = DocumentStatus.FAILED
    # Sales Director (ROLE-03) cannot retry
    with pytest.raises(ForbiddenStateTransitionError):
        DocumentStateMachine.transition(
            doc, DocumentStatus.PREPROCESSING, actor_role="ROLE-03"
        )


# ---------------------------------------------------------------------------
# Storage Service Tests (MinIO / S3)
# ---------------------------------------------------------------------------


def test_storage_service_crud_and_presigned_url() -> None:
    """Verify put, get, delete, and presigned URL generation on MinIO."""
    storage = StorageService()
    storage.ensure_bucket_exists()

    test_key = f"tests/test_file_{uuid4().hex[:8]}.txt"
    test_content = b"Hello Aureon IDP Storage!"

    # 1. Put
    saved_key = storage.put_object(test_key, test_content, content_type="text/plain")
    assert saved_key == test_key

    # 2. Get
    retrieved = storage.get_object(test_key)
    assert retrieved == test_content

    # 3. Presigned URL (15 minutes = 900 seconds)
    url = storage.generate_presigned_url(test_key, expires_in=900)
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in url
    assert "X-Amz-Expires=900" in url
    assert "X-Amz-Signature=" in url
    assert test_key in url

    # 4. Delete
    storage.delete_object(test_key)

    # 5. Get deleted should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        storage.get_object(test_key)

"""Document lifecycle state machine per 04-IDP-FEATURE-SPEC.md §8.2 (T-202).

Enforces valid status transitions, actor role checks, and the 7-day undo deadline.
"""

from datetime import UTC, datetime
from typing import ClassVar

from app.modules.idp.enums import DocumentStatus
from app.modules.idp.models import SourceDocument


class StateTransitionError(Exception):
    """Base error for state machine transition violations."""

    def __init__(self, message: str, code: str = "CONFLICT_STATE") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class InvalidStateTransitionError(StateTransitionError):
    """Raised when a status transition is not permitted by the state chart."""

    def __init__(
        self,
        current_status: DocumentStatus,
        target_status: DocumentStatus,
        detail: str | None = None,
    ) -> None:
        msg = f"Cannot transition document from {current_status} to {target_status}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg, code="CONFLICT_STATE")
        self.current_status = current_status
        self.target_status = target_status


class ForbiddenStateTransitionError(StateTransitionError):
    """Raised when an actor lacks permission to trigger a specific transition."""

    def __init__(
        self,
        actor_role: str,
        target_status: DocumentStatus,
        detail: str | None = None,
    ) -> None:
        msg = f"Role '{actor_role}' is not authorized to transition document to {target_status}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg, code="FORBIDDEN_ROLE")
        self.actor_role = actor_role
        self.target_status = target_status


class UndoDeadlineExpiredError(StateTransitionError):
    """Raised when an undo/rollback is attempted past the 7-day deadline (04 §8.2)."""

    def __init__(self, deadline: datetime) -> None:
        msg = f"Rollback rejected: undo deadline expired at {deadline.isoformat()} (> 7 days)"
        super().__init__(msg, code="UNDO_EXPIRED")
        self.deadline = deadline


class DocumentStateMachine:
    """State machine governing SourceDocument lifecycle transitions (04 §8.2)."""

    VALID_TRANSITIONS: ClassVar[dict[DocumentStatus, set[DocumentStatus]]] = {
        DocumentStatus.UPLOADED: {
            DocumentStatus.PREPROCESSING,
            DocumentStatus.DUPLICATE,
        },
        DocumentStatus.DUPLICATE: {
            DocumentStatus.PREPROCESSING,  # "Vẫn xử lý"
        },
        DocumentStatus.PREPROCESSING: {
            DocumentStatus.CLASSIFYING,
            DocumentStatus.FAILED,
        },
        DocumentStatus.CLASSIFYING: {
            DocumentStatus.EXTRACTING,
            DocumentStatus.FAILED,
        },
        DocumentStatus.EXTRACTING: {
            DocumentStatus.VALIDATING,
            DocumentStatus.FAILED,
        },
        DocumentStatus.VALIDATING: {
            DocumentStatus.AUTO_APPROVED,
            DocumentStatus.NEEDS_REVIEW,
            DocumentStatus.FAILED,
        },
        DocumentStatus.FAILED: {
            DocumentStatus.PREPROCESSING,  # Manual retry
        },
        DocumentStatus.NEEDS_REVIEW: {
            DocumentStatus.IN_REVIEW,
        },
        DocumentStatus.IN_REVIEW: {
            DocumentStatus.NEEDS_REVIEW,  # Lock released / timeout
            DocumentStatus.APPROVED,
            DocumentStatus.REJECTED,
        },
        DocumentStatus.REJECTED: {
            DocumentStatus.NEEDS_REVIEW,  # Reopen
        },
        DocumentStatus.AUTO_APPROVED: {
            DocumentStatus.COMMITTED,
            DocumentStatus.NEEDS_REVIEW,  # Action conflict on commit
        },
        DocumentStatus.APPROVED: {
            DocumentStatus.COMMITTED,
        },
        DocumentStatus.COMMITTED: {
            DocumentStatus.ROLLED_BACK,  # Undo <= 7 days
        },
        DocumentStatus.ROLLED_BACK: set(),  # Terminal state
    }

    @classmethod
    def can_transition(
        cls, current_status: DocumentStatus, target_status: DocumentStatus
    ) -> bool:
        """Check if target_status is theoretically valid from current_status."""
        return target_status in cls.VALID_TRANSITIONS.get(current_status, set())

    @classmethod
    def transition(
        cls,
        document: SourceDocument,
        target_status: DocumentStatus,
        actor_role: str | None = None,
        reason: str | None = None,
    ) -> DocumentStatus:
        """Execute a state transition on a SourceDocument with validation and actor checks."""
        current = document.status

        # 1. Check basic graph transition
        if not cls.can_transition(current, target_status):
            raise InvalidStateTransitionError(current, target_status)

        # 2. Check actor permission for guarded transitions (04 §8.2, 02 §3.4)
        if target_status == DocumentStatus.ROLLED_BACK:
            # 04 §8.2: Reviewer (ROLE-05), CFO (ROLE-02, FIN only), HR Manager (ROLE-04, HR only)
            # CEO (ROLE-01) explicitly has NO rollback permission
            if actor_role == "ROLE-01":
                detail = "CEO (ROLE-01) does not have undo permission"
                raise ForbiddenStateTransitionError(actor_role, target_status, detail=detail)
            if actor_role not in ("ROLE-05", "ROLE-02", "ROLE-04"):
                raise ForbiddenStateTransitionError(
                    actor_role or "UNKNOWN", target_status, detail="Role cannot undo commits"
                )

            # Pillar scope checks for CFO and HR Manager
            if actor_role == "ROLE-02" and "FIN" not in document.pillars:
                raise ForbiddenStateTransitionError(
                    actor_role, target_status, detail="CFO can only rollback FIN documents"
                )
            if actor_role == "ROLE-04" and "HR" not in document.pillars:
                raise ForbiddenStateTransitionError(
                    actor_role, target_status, detail="HR Manager can only rollback HR documents"
                )

            # Check 7-day deadline
            now = datetime.now(UTC)
            if document.undo_deadline and now > document.undo_deadline:
                raise UndoDeadlineExpiredError(document.undo_deadline)

        elif current == DocumentStatus.FAILED and target_status == DocumentStatus.PREPROCESSING:
            # Manual retry: ROLE-05, ROLE-02 (FIN), ROLE-04 (HR)
            if actor_role not in ("ROLE-05", "ROLE-02", "ROLE-04"):
                detail = "Only Reviewer, CFO (FIN) or HR Manager (HR) can manually retry"
                raise ForbiddenStateTransitionError(
                    actor_role or "UNKNOWN", target_status, detail=detail
                )
            if actor_role == "ROLE-02" and "FIN" not in document.pillars:
                detail = "CFO can only retry FIN documents"
                raise ForbiddenStateTransitionError(actor_role, target_status, detail=detail)
            if actor_role == "ROLE-04" and "HR" not in document.pillars:
                detail = "HR Manager can only retry HR documents"
                raise ForbiddenStateTransitionError(actor_role, target_status, detail=detail)

        elif current == DocumentStatus.REJECTED and target_status == DocumentStatus.NEEDS_REVIEW:
            # Reopen: ROLE-05, ROLE-02 (FIN), ROLE-04 (HR)
            if actor_role not in ("ROLE-05", "ROLE-02", "ROLE-04"):
                detail = "Only Reviewer, CFO (FIN) or HR Manager (HR) can reopen rejected documents"
                raise ForbiddenStateTransitionError(
                    actor_role or "UNKNOWN", target_status, detail=detail
                )

        elif current == DocumentStatus.IN_REVIEW and target_status == DocumentStatus.REJECTED:
            # Rejection requires reason
            if not reason:
                msg = "A non-empty reason is required when rejecting a document"
                raise InvalidStateTransitionError(current, target_status, detail=msg)

        # 3. Apply state change
        document.status = target_status
        if reason:
            document.status_reason = reason

        if target_status == DocumentStatus.COMMITTED:
            document.mark_committed()

        return target_status

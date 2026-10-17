"""Error contract — 10 §1.2 (error envelope) and 10 §1.3 (error code table). T-005.

`ErrorCode` is the single backend source of the stable `error.code` values; it must stay equal to
the table in 10 §1.3 and to `ApiErrorCode` in packages/shared-types (checked by TC-SYS-002
contract tests).
"""

from enum import StrEnum
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(StrEnum):
    """Stable `error.code` values — 10 §1.3 (order follows the table)."""

    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    FORBIDDEN_ROLE = "FORBIDDEN_ROLE"
    FORBIDDEN_SCOPE = "FORBIDDEN_SCOPE"
    FORBIDDEN_SALARY = "FORBIDDEN_SALARY"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT_STATE = "CONFLICT_STATE"
    REVIEW_LOCKED = "REVIEW_LOCKED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    DUPLICATE_DOCUMENT = "DUPLICATE_DOCUMENT"
    UNDO_EXPIRED = "UNDO_EXPIRED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    ACTION_REJECTED = "ACTION_REJECTED"
    AI_DISABLED = "AI_DISABLED"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"

    @property
    def http_status(self) -> int:
        return ERROR_HTTP_STATUS[self]


# HTTP status per code — column "HTTP" of 10 §1.3.
ERROR_HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.BAD_REQUEST: 400,
    ErrorCode.UNAUTHENTICATED: 401,
    ErrorCode.INVALID_CREDENTIALS: 401,
    ErrorCode.FORBIDDEN_ROLE: 403,
    ErrorCode.FORBIDDEN_SCOPE: 403,
    ErrorCode.FORBIDDEN_SALARY: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT_STATE: 409,
    ErrorCode.REVIEW_LOCKED: 409,
    ErrorCode.IDEMPOTENCY_CONFLICT: 409,
    ErrorCode.DUPLICATE_DOCUMENT: 409,
    ErrorCode.UNDO_EXPIRED: 410,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: 415,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.ACTION_REJECTED: 422,
    ErrorCode.AI_DISABLED: 423,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.DEPENDENCY_UNAVAILABLE: 503,
}

# Default English debug messages (10 §1.1: the UI maps `error.code` to i18n `error.<code>`).
DEFAULT_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.BAD_REQUEST: "Bad request",
    ErrorCode.UNAUTHENTICATED: "Authentication required",
    ErrorCode.INVALID_CREDENTIALS: "Invalid credentials",
    ErrorCode.FORBIDDEN_ROLE: "Role is not allowed to call this endpoint",
    ErrorCode.FORBIDDEN_SCOPE: "Resource is outside the role scope",
    ErrorCode.FORBIDDEN_SALARY: "Resource contains salary data",
    ErrorCode.NOT_FOUND: "Not found",
    ErrorCode.CONFLICT_STATE: "Invalid state transition",
    ErrorCode.REVIEW_LOCKED: "Document is locked by another reviewer",
    ErrorCode.IDEMPOTENCY_CONFLICT: "Idempotency-Key was reused with a different request",
    ErrorCode.DUPLICATE_DOCUMENT: "Duplicate document",
    ErrorCode.UNDO_EXPIRED: "Undo window has expired",
    ErrorCode.FILE_TOO_LARGE: "File too large",
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: "Unsupported media type",
    ErrorCode.VALIDATION_ERROR: "Validation error",
    ErrorCode.ACTION_REJECTED: "Action rejected",
    ErrorCode.AI_DISABLED: "AI features are disabled",
    ErrorCode.RATE_LIMITED: "Too many requests",
    ErrorCode.INTERNAL_ERROR: "Internal server error",
    ErrorCode.DEPENDENCY_UNAVAILABLE: "Dependency unavailable",
}


class FieldError(BaseModel):
    """One entry of `details.fields` for VALIDATION_ERROR — 10 §1.2."""

    loc: list[str | int]
    msg: str
    type: str


class ErrorBody(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    """`{ "error": { code, message, details } }` — 10 §1.2."""

    error: ErrorBody


class ApiError(Exception):
    """Raise from endpoints/dependencies to return a contract error envelope.

    Example: `raise ApiError(ErrorCode.REVIEW_LOCKED, details={"locked_by": ...})`.
    The HTTP status always comes from 10 §1.3 (`ERROR_HTTP_STATUS`).
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.code = code
        self.message = message or DEFAULT_MESSAGES[code]
        self.details = details or {}
        self.headers = headers
        super().__init__(f"{code}: {self.message}")

    @property
    def status_code(self) -> int:
        return ERROR_HTTP_STATUS[self.code]


def error_response(
    code: ErrorCode,
    message: str | None = None,
    details: dict[str, Any] | None = None,
    *,
    status_code: int | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Render the 10 §1.2 error envelope. `status_code` overrides only for HTTPException mapping."""
    envelope = ErrorEnvelope(
        error=ErrorBody(code=code, message=message or DEFAULT_MESSAGES[code], details=details or {})
    )
    return JSONResponse(
        status_code=status_code or ERROR_HTTP_STATUS[code],
        content=envelope.model_dump(mode="json"),
        headers=headers,
    )

"""Application errors → `{ error: { code, message, details } }` (10 §1.3–1.4, DEC-130).

Only codes from 10 §1.4 may be used. Handlers are registered by `install_error_handlers`.
"""

from typing import Any


class AppError(Exception):
    """Base error. `code` is the stable 10 §1.4 code; `message` is debug-only text."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.message = message or self.code
        self.details: dict[str, Any] = details or {}
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code, code = 400, "BAD_REQUEST"


class UnauthenticatedError(AppError):
    status_code, code = 401, "UNAUTHENTICATED"


class InvalidCredentialsError(AppError):
    status_code, code = 401, "INVALID_CREDENTIALS"


class RefreshTokenInvalidError(AppError):
    status_code, code = 401, "REFRESH_TOKEN_INVALID"


class PermissionDeniedError(AppError):
    """403 — missing `<domain>:<action>` (FORBIDDEN_ROLE) or out of scope (FORBIDDEN_SCOPE)."""

    status_code, code = 403, "FORBIDDEN_ROLE"


class ScopeDeniedError(PermissionDeniedError):
    code = "FORBIDDEN_SCOPE"


class SalaryDeniedError(PermissionDeniedError):
    """403 — level-4 salary / PII data outside ROLE-01/ROLE-04 (02 §6.3)."""

    code = "FORBIDDEN_SALARY"


class NotFoundError(AppError):
    status_code, code = 404, "NOT_FOUND"


class ConflictStateError(AppError):
    status_code, code = 409, "CONFLICT_STATE"


class DuplicateResourceError(AppError):
    status_code, code = 409, "DUPLICATE_RESOURCE"


class IdempotencyConflictError(AppError):
    status_code, code = 409, "IDEMPOTENCY_CONFLICT"


class ReviewLockedError(AppError):
    """409 — document under another reviewer's soft lock (15 min, 10 §1.4, EP-29/30)."""

    status_code, code = 409, "REVIEW_LOCKED"


class UndoExpiredError(AppError):
    """410 — undo window elapsed (7 days IDP / 24h AI L3, DEC-134; EP-33/EP-116)."""

    status_code, code = 410, "UNDO_EXPIRED"


class ActionRejectedError(AppError):
    """422 — Action Registry / autonomy policy rejected the write (10 §1.4, EP-31)."""

    status_code, code = 422, "ACTION_REJECTED"


class ValidationError(AppError):
    status_code, code = 422, "VALIDATION_ERROR"


class BusinessRuleError(AppError):
    status_code, code = 422, "BUSINESS_RULE_VIOLATION"


class RateLimitError(AppError):
    status_code, code = 429, "RATE_LIMIT_EXCEEDED"


class DependencyUnavailableError(AppError):
    status_code, code = 503, "DEPENDENCY_UNAVAILABLE"


class AIError(AppError):
    """Base for `AI_*` codes (10 §1.4)."""

    status_code, code = 502, "AI_PROVIDER_ERROR"


AI_ERROR_CODES: dict[str, int] = {
    "AI_CONTEXT_TOO_LARGE": 422,
    "AI_DISABLED": 423,
    "AI_QUOTA_EXCEEDED": 429,
    "AI_PROVIDER_ERROR": 502,
    "AI_FUNCTION_CALL_FAILED": 502,
    "AI_PROVIDER_TIMEOUT": 504,
}


def ai_error(code: str, message: str | None = None, **details: Any) -> AIError:
    """`raise ai_error("AI_QUOTA_EXCEEDED")` — status taken from 10 §1.4."""
    if code not in AI_ERROR_CODES:
        raise ValueError(f"unknown AI error code {code!r} (10 §1.4)")
    return AIError(message, code=code, status_code=AI_ERROR_CODES[code], details=details)


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}

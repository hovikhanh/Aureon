"""Exception handlers rendering the 10 §1.2 error envelope with 10 §1.3 codes. T-005.

- `ApiError`               → its own code/status.
- `RequestValidationError` → 422 `VALIDATION_ERROR` (body) or 400 `BAD_REQUEST` (only
  query/path/header/cookie params invalid), both with `details.fields[{loc,msg,type}]`.
- Starlette/FastAPI `HTTPException` (router 404/405, framework errors) → mapped code.
- Unhandled exceptions     → 500 `INTERNAL_ERROR` (handled in `RequestIdMiddleware`).
"""

from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.core.errors import ApiError, ErrorCode, FieldError, error_response

# HTTPException status → 10 §1.3 code. The HTTP status of the exception is preserved.
# 405 has no row in 10 §1.3; it maps to BAD_REQUEST with HTTP 405 kept (proposed DEC).
_HTTP_STATUS_TO_CODE: dict[int, ErrorCode] = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHENTICATED,
    403: ErrorCode.FORBIDDEN_ROLE,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.BAD_REQUEST,
    409: ErrorCode.CONFLICT_STATE,
    413: ErrorCode.FILE_TOO_LARGE,
    415: ErrorCode.UNSUPPORTED_MEDIA_TYPE,
    422: ErrorCode.VALIDATION_ERROR,
    423: ErrorCode.AI_DISABLED,
    429: ErrorCode.RATE_LIMITED,
    503: ErrorCode.DEPENDENCY_UNAVAILABLE,
}


_PARAM_LOCATIONS = frozenset({"query", "path", "header", "cookie"})


def code_for_http_status(status_code: int) -> ErrorCode:
    if status_code in _HTTP_STATUS_TO_CODE:
        return _HTTP_STATUS_TO_CODE[status_code]
    return ErrorCode.INTERNAL_ERROR if status_code >= 500 else ErrorCode.BAD_REQUEST


def validation_fields(errors: Sequence[Any]) -> list[dict[str, Any]]:
    """Reduce pydantic errors to `{loc,msg,type}` — never echo `input`/`ctx` (may hold PII)."""
    fields = [
        FieldError(
            loc=[p if isinstance(p, int) else str(p) for p in err.get("loc", ())],
            msg=str(err.get("msg", "")),
            type=str(err.get("type", "")),
        )
        for err in errors
    ]
    return [f.model_dump() for f in fields]


async def api_error_handler(_: Request, exc: Exception) -> Response:
    if not isinstance(exc, ApiError):  # narrowing for the generic handler signature
        raise exc
    return error_response(exc.code, exc.message, exc.details, headers=exc.headers)


async def validation_error_handler(_: Request, exc: Exception) -> Response:
    if not isinstance(exc, RequestValidationError):  # narrowing for the generic handler signature
        raise exc
    errors = exc.errors()
    fields = validation_fields(errors)
    # 10 §1.3: invalid request *parameters* (query/path/header/cookie, e.g. `period_key`,
    # `page_size` > 100 — TC-SYS-006) → 400 BAD_REQUEST; body schema errors → 422
    # VALIDATION_ERROR. Both carry `details.fields` (10 §1.2).
    if fields and all(f["loc"] and f["loc"][0] in _PARAM_LOCATIONS for f in fields):
        return error_response(ErrorCode.BAD_REQUEST, details={"fields": fields})
    return error_response(ErrorCode.VALIDATION_ERROR, details={"fields": fields})


async def http_exception_handler(_: Request, exc: Exception) -> Response:
    if not isinstance(exc, StarletteHTTPException):  # narrowing for the generic handler signature
        raise exc
    code = code_for_http_status(exc.status_code)
    # Only reuse `detail` when it is a plain string (framework messages like "Not Found").
    message = exc.detail if isinstance(exc.detail, str) and exc.status_code < 500 else None
    return error_response(
        code, message, status_code=exc.status_code, headers=getattr(exc, "headers", None)
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

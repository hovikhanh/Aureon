"""Exception handlers → error envelope `{ error: { code, message, details } }` (10 §1.3).

Unhandled exceptions become `500 INTERNAL_ERROR` in `RequestIdMiddleware` (request_context.py).
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError, error_body

# Starlette's own HTTP errors (404 route, 405 …) mapped onto 10 §1.4 codes.
_HTTP_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN_ROLE",
    404: "NOT_FOUND",
    405: "BAD_REQUEST",
    409: "CONFLICT_STATE",
    413: "FILE_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMIT_EXCEEDED",
    503: "DEPENDENCY_UNAVAILABLE",
}


async def _app_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):  # pragma: no cover — registered for AppError only
        raise exc
    return JSONResponse(error_body(exc.code, exc.message, exc.details), exc.status_code)


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(
        exc, RequestValidationError
    ):  # pragma: no cover — registered for RequestValidationError only
        raise exc
    fields = [
        {"loc": list(e.get("loc", ())), "msg": str(e.get("msg", "")), "type": str(e.get("type"))}
        for e in exc.errors()
    ]
    return JSONResponse(
        error_body("VALIDATION_ERROR", "request validation failed", {"fields": fields}), 422
    )


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(
        exc, StarletteHTTPException
    ):  # pragma: no cover — registered for StarletteHTTPException only
        raise exc
    code = _HTTP_CODES.get(exc.status_code, "INTERNAL_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else code
    return JSONResponse(error_body(code, message), exc.status_code, headers=exc.headers)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)

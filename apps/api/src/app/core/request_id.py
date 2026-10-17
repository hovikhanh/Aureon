"""`X-Request-Id` middleware — 10 §1.2 ("every response has header X-Request-Id"). T-005.

Pure ASGI middleware (not BaseHTTPMiddleware) so the contextvar is visible to endpoints,
dependencies and exception handlers of the same request. It is the outermost app middleware and
also renders unhandled exceptions as `500 INTERNAL_ERROR` (10 §1.3, no stack trace) so that even
those responses carry the header. Later consumers (audit log `metadata.request_id`, 10 §1.7;
structured logs, 07 §10) read it via `get_request_id()` or `request.state.request_id`.
"""

import logging
import re
import uuid
from contextvars import ContextVar

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import ErrorCode, error_response

REQUEST_ID_HEADER = "X-Request-Id"
# Accept a client/proxy supplied id only if it is short and made of safe characters
# (prevents header/log injection); otherwise a fresh uuid4 is generated.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:\-]{1,128}$")

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("app.request")


def get_request_id() -> str | None:
    """Request id of the current request (None outside a request)."""
    return request_id_var.get()


def _incoming_request_id(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"x-request-id":
            candidate = value.decode("latin-1")
            return candidate if _SAFE_REQUEST_ID.match(candidate) else None
    return None


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _incoming_request_id(scope) or str(uuid.uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_var.set(request_id)
        response_started = False

        async def send_with_id(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            # Log the traceback server-side only; the client gets the generic envelope.
            logger.exception("unhandled exception", extra={"request_id": request_id})
            if response_started:
                raise
            response = error_response(ErrorCode.INTERNAL_ERROR)
            await response(scope, receive, send_with_id)
        finally:
            request_id_var.reset(token)

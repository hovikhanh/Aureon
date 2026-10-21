"""`X-Request-Id` (10 §1.9): accept a client UUID or mint one; expose via contextvar.

The id is echoed on every response (success and error) and read by the envelope, audit
metadata and event `correlation_id`. Unhandled exceptions are turned into `500 INTERNAL_ERROR`
here, so even crashes carry the envelope and the header.
"""

import json
import logging
import uuid
from contextvars import ContextVar

from starlette.types import ASGIApp, Message, Receive, Scope, Send

HEADER = "x-request-id"
log = logging.getLogger("app.errors")
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_request_id() -> str | None:
    return _request_id.get()


def _valid(value: str) -> str | None:
    try:
        return str(uuid.UUID(value))
    except ValueError:
        return None


class RequestIdMiddleware:
    """Pure ASGI (no BaseHTTPMiddleware) so streaming/SSE responses are not buffered."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope.get("headers") or []).get(HEADER.encode(), b"").decode()
        rid = _valid(incoming) or str(uuid.uuid4())
        token = _request_id.set(rid)

        started = False

        async def send_with_id(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = [(k, v) for k, v in message.get("headers", []) if k != HEADER.encode()]
                headers.append((HEADER.encode(), rid.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            # Unhandled error: answer with the 10 §1.3 envelope (no stack trace) + request id.
            log.exception("unhandled error", extra={"request_id": rid})
            if started:
                raise
            body = json.dumps(
                {"error": {"code": "INTERNAL_ERROR", "message": "internal error", "details": {}}}
            ).encode()
            await send_with_id(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send_with_id({"type": "http.response.body", "body": body})
        finally:
            _request_id.reset(token)

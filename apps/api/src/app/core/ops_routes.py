"""Orchestration probes outside the `/api/v1` contract (T-515, DEC-242).

Plain Starlette routes (not `APIRoute`, no envelope) for Docker / k8s:
- `GET /health`       → 200 `{status, version, uptime, dependencies}`; 503 only when DB/Redis down.
- `GET /health/ready` → readiness: DB + Redis only.
- `GET /health/live`  → liveness: 200 while the process serves requests.
- `GET /metrics`      → Prometheus text exposition (no client library; DEC: no new deps).
EP-01 (`/api/v1/health`, enveloped) lives in `app.modules.platform.routes.health`.
"""

from collections import Counter

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app import __version__
from app.core.health import REQUIRED, health_payload, run_checks, uptime_seconds

NO_STORE = {"Cache-Control": "no-store"}
_requests: Counter[tuple[str, int]] = Counter()


class RequestCounterMiddleware:
    """Counts responses by (method, status) for `/metrics`. Pure ASGI → SSE not buffered."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def counting_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                _requests[(scope.get("method", "GET"), int(message["status"]))] += 1
            await send(message)

        await self.app(scope, receive, counting_send)


async def health(_: Request) -> Response:
    payload = health_payload(await run_checks())
    code = 503 if payload["status"] == "down" else 200
    return JSONResponse(payload, status_code=code, headers=NO_STORE)


async def ready(_: Request) -> Response:
    deps = await run_checks(REQUIRED)
    ok = all(v == "ok" for v in deps.values())
    body = {"status": "ready" if ok else "not_ready", "dependencies": deps}
    return JSONResponse(body, status_code=200 if ok else 503, headers=NO_STORE)


async def live(_: Request) -> Response:
    return JSONResponse({"status": "alive", "uptime": uptime_seconds()}, headers=NO_STORE)


async def metrics(_: Request) -> Response:
    deps = await run_checks()
    lines = [
        "# HELP aureon_build_info Build information.",
        "# TYPE aureon_build_info gauge",
        f'aureon_build_info{{version="{__version__}"}} 1',
        "# HELP aureon_uptime_seconds Process uptime in seconds.",
        "# TYPE aureon_uptime_seconds gauge",
        f"aureon_uptime_seconds {uptime_seconds()}",
        "# HELP aureon_dependency_up Dependency reachability (1 = ok).",
        "# TYPE aureon_dependency_up gauge",
        *(f'aureon_dependency_up{{name="{n}"}} {int(v == "ok")}' for n, v in deps.items()),
        "# HELP aureon_http_requests_total HTTP responses by method and status.",
        "# TYPE aureon_http_requests_total counter",
        *(
            f'aureon_http_requests_total{{method="{m}",status="{s}"}} {c}'
            for (m, s), c in sorted(_requests.items())
        ),
    ]
    return PlainTextResponse(
        "\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4; charset=utf-8",
        headers=NO_STORE,
    )


def install_ops_routes(app: Starlette) -> None:
    app.add_route("/health", health, methods=["GET"], include_in_schema=False)
    app.add_route("/health/ready", ready, methods=["GET"], include_in_schema=False)
    app.add_route("/health/live", live, methods=["GET"], include_in_schema=False)
    app.add_route("/metrics", metrics, methods=["GET"], include_in_schema=False)
    app.add_middleware(RequestCounterMiddleware)

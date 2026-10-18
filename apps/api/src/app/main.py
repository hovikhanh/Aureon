"""FastAPI entrypoint: `uv run uvicorn app.main:app --reload --port 4000`."""

from fastapi import FastAPI

from app import __version__
from app.core.handlers import register_exception_handlers
from app.core.request_id import RequestIdMiddleware
from app.modules.auth.router import router as auth_router
from app.modules.idp.router import router as idp_router
from app.modules.system.router import router as system_router

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    application = FastAPI(title="Aureon Demo API", version=__version__)
    # T-005 — 10 §1.2/§1.3: error envelope for every error, X-Request-Id on every response.
    register_exception_handlers(application)
    # Added last → outermost app middleware: sees every response, incl. unhandled 500s.
    application.add_middleware(RequestIdMiddleware)
    application.include_router(system_router, prefix=API_PREFIX)
    # T-103 — EP-02 login (public, DEC-080) mounted the same way as the system router.
    application.include_router(auth_router, prefix=API_PREFIX)
    # T-203 — EP-20 upload document, EP-40 onboarding batches
    application.include_router(idp_router, prefix=API_PREFIX)
    return application


app = create_app()

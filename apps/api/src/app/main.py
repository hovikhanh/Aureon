"""FastAPI app factory: `uv run uvicorn app.main:app --reload --port 4000`."""

from fastapi import APIRouter, FastAPI

from app import __version__
from app.core.handlers import install_error_handlers
from app.core.ops_routes import install_ops_routes
from app.core.request_context import RequestIdMiddleware
from app.modules.ai.routes.router import router as ai_router
from app.modules.auth.routes.router import router as auth_router
from app.modules.dashboard.routes.router import router as dashboard_router
from app.modules.execution.routes.router import router as execution_router
from app.modules.finance.routes.router import router as finance_router
from app.modules.hr.routes.router import router as hr_router
from app.modules.idp.routes.router import router as idp_router
from app.modules.platform.routes.health import router as health_router
from app.modules.platform.routes.router import router as platform_router
from app.modules.product.routes.router import router as product_router
from app.modules.risk.routes.router import router as risk_router
from app.modules.sales.routes.router import router as sales_router

API_PREFIX = "/api/v1"

MODULE_ROUTERS: tuple[APIRouter, ...] = (
    platform_router,
    auth_router,
    dashboard_router,
    finance_router,
    sales_router,
    hr_router,
    product_router,
    risk_router,
    execution_router,
    idp_router,
    ai_router,
)


def create_app() -> FastAPI:
    application = FastAPI(title="Aureon API", version=__version__)
    install_error_handlers(application)
    install_ops_routes(application)  # /health, /health/ready, /health/live, /metrics (T-515)
    application.add_middleware(RequestIdMiddleware)
    application.include_router(health_router, prefix=API_PREFIX)  # EP-01 (platform module)
    for router in MODULE_ROUTERS:
        application.include_router(router, prefix=API_PREFIX)
    return application


app = create_app()

"""FastAPI entrypoint: `uv run uvicorn app.main:app --reload --port 4000`."""

from fastapi import FastAPI

from app import __version__
from app.modules.system.router import router as system_router

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    application = FastAPI(title="Aureon Demo API", version=__version__)
    application.include_router(system_router, prefix=API_PREFIX)
    return application


app = create_app()

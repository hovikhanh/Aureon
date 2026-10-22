"""EP-01 `GET /api/v1/health` (10 §3.1/§4): public, enveloped health incl. model gateway.

`503` only when a required dependency (DB/Redis) is down; optional ones → `degraded`.
"""

from typing import Literal

from fastapi import Response
from pydantic import BaseModel

from app import __version__
from app.core.config import get_config
from app.core.health import overall, run_checks, uptime_seconds
from app.core.routing import EnvelopeRouter

router = EnvelopeRouter(tags=["platform"])

Dep = Literal["ok", "unavailable"]


class ModelGatewayCheck(BaseModel):
    mode: str
    primary: str


class HealthChecks(BaseModel):
    db: Dep
    redis: Dep
    ollama: Dep
    clamav: Dep
    model_gateway: ModelGatewayCheck


class HealthOut(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    uptime: float
    checks: HealthChecks


@router.get("/health", response_model=HealthOut)
async def get_health(response: Response) -> HealthOut:
    deps = await run_checks()
    status = overall(deps)
    response.headers["Cache-Control"] = "no-store"
    if status == "down":
        response.status_code = 503
    cfg = get_config()
    return HealthOut(
        status=status,
        version=__version__,
        uptime=uptime_seconds(),
        checks=HealthChecks(
            db=deps["db"],
            redis=deps["redis"],
            ollama=deps["ollama"],
            clamav=deps["clamav"],
            model_gateway=ModelGatewayCheck(
                mode=cfg.model_gateway_mode, primary=cfg.model_provider_primary
            ),
        ),
    )

"""EP-01 GET /api/v1/health — public (DEC-080), no require_role, no secrets in body."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.config import ConfigService, get_config
from app.core.health import Probe, make_probes, run_probes
from app.modules.system.schemas import HealthChecks, HealthEnvelope, HealthOut

router = APIRouter(tags=["system"])


def get_probes(config: Annotated[ConfigService, Depends(get_config)]) -> dict[str, Probe]:
    return make_probes(config)


@router.get(
    "/health",
    response_model=HealthEnvelope,
    responses={503: {"model": HealthEnvelope, "description": "DEPENDENCY_UNAVAILABLE"}},
)
def health(
    response: Response,
    config: Annotated[ConfigService, Depends(get_config)],
    probes: Annotated[dict[str, Probe], Depends(get_probes)],
) -> HealthEnvelope:
    results = run_probes(probes)
    checks = HealthChecks(**{name: "ok" if ok else "fail" for name, ok in results.items()})
    degraded = not all(results.values())
    # 10 EP-01: 503 when the database is unavailable; body still reports status=degraded.
    if not results["database"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthEnvelope(
        data=HealthOut(
            status="degraded" if degraded else "ok",
            version=config.app_version,
            checks=checks,
            demo_mode=config.demo_mode,
        )
    )

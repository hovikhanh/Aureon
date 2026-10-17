"""EP-01 response models (10 §2 EP-01)."""

from typing import Literal

from pydantic import BaseModel

CheckState = Literal["ok", "fail"]


class HealthChecks(BaseModel):
    database: CheckState
    redis: CheckState
    storage: CheckState
    model_gateway: CheckState


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    checks: HealthChecks
    demo_mode: bool


class HealthEnvelope(BaseModel):
    data: HealthOut

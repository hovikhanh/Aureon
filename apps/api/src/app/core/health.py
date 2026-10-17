"""EP-01 dependency probes: return True when healthy; never raise or leak config."""

from collections.abc import Callable

import httpx
import redis
from sqlalchemy import create_engine, text

from app.core.config import ConfigService
from app.core.model_gateway import ModelGateway

Probe = Callable[[], bool]
PROBE_TIMEOUT_S = 2.0


def _safe(fn: Probe) -> bool:
    try:
        return fn()
    except Exception:
        return False


def make_probes(config: ConfigService) -> dict[str, Probe]:
    def database() -> bool:
        engine = create_engine(
            config.database_url.get_secret_value(),
            pool_pre_ping=True,
            connect_args={"connect_timeout": int(PROBE_TIMEOUT_S)},
        )
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        finally:
            engine.dispose()

    def redis_check() -> bool:
        client = redis.Redis.from_url(
            config.redis_url.get_secret_value(), socket_timeout=PROBE_TIMEOUT_S
        )
        try:
            return bool(client.ping())
        finally:
            client.close()

    def storage() -> bool:
        resp = httpx.get(f"{config.s3_endpoint}/minio/health/live", timeout=PROBE_TIMEOUT_S)
        return resp.status_code == 200

    def model_gateway() -> bool:
        # TC-IDP-036: only ModelGateway may call the LLM; fixture mode is always available.
        gateway = ModelGateway(config, timeout_s=PROBE_TIMEOUT_S)
        try:
            return gateway.ping()
        finally:
            gateway.close()

    return {
        "database": database,
        "redis": redis_check,
        "storage": storage,
        "model_gateway": model_gateway,
    }


def run_probes(probes: dict[str, Probe]) -> dict[str, bool]:
    return {name: _safe(probe) for name, probe in probes.items()}

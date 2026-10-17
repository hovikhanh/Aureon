"""EP-01 dependency probes: return True when healthy; never raise or leak config."""

from collections.abc import Callable

import httpx
import redis
from sqlalchemy import create_engine, text

from app.core.config import ConfigService

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
        # Fixture mode replays recorded outputs, so the gateway is always available (07 §5.2).
        if config.model_gateway_mode == "fixture":
            return True
        resp = httpx.post(
            f"{config.omniroute_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {config.omniroute_api_key.get_secret_value()}"},
            json={
                "model": config.model_classify,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            },
            timeout=PROBE_TIMEOUT_S,
        )
        return resp.status_code == 200

    return {
        "database": database,
        "redis": redis_check,
        "storage": storage,
        "model_gateway": model_gateway,
    }


def run_probes(probes: dict[str, Probe]) -> dict[str, bool]:
    return {name: _safe(probe) for name, probe in probes.items()}

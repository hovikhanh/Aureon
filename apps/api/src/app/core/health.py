"""Dependency health checks (T-515, EP-01, NFR observability).

Each probe is bounded by `PROBE_TIMEOUT_S` and never raises: it returns `"ok"` or
`"unavailable"`. Only DB + Redis gate readiness; Ollama / ClamAV are optional for the
demo (CLAMAV_REQUIRED=false, DEC-235) so they degrade `/health` without failing it.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Literal

import clamd
import httpx
import redis.asyncio as aioredis
from sqlalchemy import text

from app import __version__
from app.core.config import get_config
from app.core.db import get_engine

PROBE_TIMEOUT_S = 2.0
DepStatus = Literal["ok", "unavailable"]
STARTED_AT = time.monotonic()
REQUIRED = ("db", "redis")


async def check_db() -> None:
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))


async def check_redis() -> None:
    client = aioredis.from_url(
        get_config().redis_url.get_secret_value(), socket_connect_timeout=PROBE_TIMEOUT_S
    )
    try:
        await client.ping()
    finally:
        await client.aclose()


async def check_ollama() -> None:
    url = get_config().ollama_base_url.rstrip("/") + "/api/tags"
    async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_S) as client:
        (await client.get(url)).raise_for_status()


def _clamd_ping() -> None:
    cfg = get_config()
    clamd.ClamdNetworkSocket(cfg.clamav_host, cfg.clamav_port, timeout=PROBE_TIMEOUT_S).ping()


async def check_clamav() -> None:
    await asyncio.to_thread(_clamd_ping)


CHECKS: dict[str, Callable[[], Awaitable[None]]] = {
    "db": check_db,
    "redis": check_redis,
    "ollama": check_ollama,
    "clamav": check_clamav,
}


async def _probe(fn: Callable[[], Awaitable[None]]) -> DepStatus:
    try:
        await asyncio.wait_for(fn(), timeout=PROBE_TIMEOUT_S + 0.5)
    except Exception:  # any failure (refused, timeout, auth) = unavailable, never crash the probe
        return "unavailable"
    return "ok"


async def run_checks(names: tuple[str, ...] | None = None) -> dict[str, DepStatus]:
    selected = names or tuple(CHECKS)
    results = await asyncio.gather(*(_probe(CHECKS[n]) for n in selected))
    return dict(zip(selected, results, strict=True))


def overall(deps: dict[str, DepStatus]) -> Literal["ok", "degraded", "down"]:
    if any(deps.get(n) == "unavailable" for n in REQUIRED):
        return "down"
    return "ok" if all(v == "ok" for v in deps.values()) else "degraded"


def uptime_seconds() -> float:
    return round(time.monotonic() - STARTED_AT, 1)


def health_payload(deps: dict[str, DepStatus]) -> dict[str, object]:
    return {
        "status": overall(deps),
        "version": __version__,
        "uptime": uptime_seconds(),
        "dependencies": deps,
    }

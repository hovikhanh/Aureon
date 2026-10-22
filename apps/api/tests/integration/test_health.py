"""T-515 — health / readiness / liveness / metrics probes (TC-OPS-HEALTH-01..05)."""

from collections.abc import Awaitable, Callable

import pytest
from fastapi.testclient import TestClient

from app.core import health
from app.main import create_app


async def _ok() -> None:
    return None


async def _fail() -> None:
    raise ConnectionError("down")


def _patch(monkeypatch: pytest.MonkeyPatch, **status: bool) -> None:
    checks: dict[str, Callable[[], Awaitable[None]]] = {
        name: (_ok if status.get(name, True) else _fail) for name in health.CHECKS
    }
    monkeypatch.setattr(health, "CHECKS", checks)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health_all_ok(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["uptime"] >= 0
    assert body["dependencies"] == {"db": "ok", "redis": "ok", "ollama": "ok", "clamav": "ok"}
    assert res.headers["cache-control"] == "no-store"


def test_optional_dependency_down_degrades_but_200(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch(monkeypatch, ollama=False, clamav=False)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "degraded"
    assert res.json()["dependencies"]["ollama"] == "unavailable"
    assert client.get("/health/ready").status_code == 200


def test_required_dependency_down(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, db=False)
    assert client.get("/health").status_code == 503
    ready = client.get("/health/ready")
    assert ready.status_code == 503
    expected = {"db": "unavailable", "redis": "ok"}
    assert ready.json() == {"status": "not_ready", "dependencies": expected}
    assert client.get("/health/live").status_code == 200  # liveness ignores dependencies


def test_ep01_enveloped_public(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, ollama=False)
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "degraded"
    assert data["checks"]["ollama"] == "unavailable"
    assert {"mode", "primary"} <= data["checks"]["model_gateway"].keys()
    _patch(monkeypatch, redis=False)
    assert client.get("/api/v1/health").status_code == 503


def test_metrics_prometheus(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, clamav=False)
    client.get("/health/live")
    res = client.get("/metrics")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain; version=0.0.4")
    text = res.text
    assert 'aureon_dependency_up{name="db"} 1' in text
    assert 'aureon_dependency_up{name="clamav"} 0' in text
    assert "aureon_http_requests_total{" in text


async def test_probe_timeout_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "PROBE_TIMEOUT_S", 0.01)

    async def slow() -> None:
        import asyncio

        await asyncio.sleep(5)

    assert await health._probe(slow) == "unavailable"
    assert health.overall({"db": "ok", "redis": "ok", "ollama": "unavailable"}) == "degraded"

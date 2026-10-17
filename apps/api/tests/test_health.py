"""TC-SYS-001 — EP-01 health (T-002, T-003)."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import ConfigService, get_config
from app.core.health import Probe
from app.main import app
from app.modules.system.router import get_probes

FAKE_DB_URL = "postgresql+psycopg://leak-user:leak-pass@db.internal:5432/aureon"
FAKE_KEY = "sk-should-never-leak"


def _probes(**overrides: bool) -> dict[str, Probe]:
    states = {"database": True, "redis": True, "storage": True, "model_gateway": True, **overrides}
    return {name: (lambda ok=ok: ok) for name, ok in states.items()}


@pytest.fixture
def client_with():  # type: ignore[no-untyped-def]
    def build(**overrides: bool) -> TestClient:
        cfg = ConfigService(database_url=FAKE_DB_URL, omniroute_api_key=FAKE_KEY, demo_mode=True)
        app.dependency_overrides[get_config] = lambda: cfg
        app.dependency_overrides[get_probes] = lambda: _probes(**overrides)
        return TestClient(app)

    yield build
    app.dependency_overrides.clear()


def test_health_ok_without_jwt(client_with) -> None:  # type: ignore[no-untyped-def]
    resp = client_with().get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "ok"
    assert set(body["data"]["checks"]) == {"database", "redis", "storage", "model_gateway"}
    assert all(v == "ok" for v in body["data"]["checks"].values())
    assert body["data"]["demo_mode"] is True
    assert body["data"]["version"]


def test_health_db_down_returns_503_degraded(client_with) -> None:  # type: ignore[no-untyped-def]
    resp = client_with(database=False).get("/api/v1/health")
    assert resp.status_code == 503
    assert resp.json()["data"]["status"] == "degraded"
    assert resp.json()["data"]["checks"]["database"] == "fail"


def test_health_non_db_failure_is_degraded_but_200(client_with) -> None:  # type: ignore[no-untyped-def]
    resp = client_with(redis=False).get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "degraded"


def test_health_body_leaks_no_secrets(client_with) -> None:  # type: ignore[no-untyped-def]
    text = client_with(database=False).get("/api/v1/health").text
    for secret in ("leak-pass", "leak-user", "db.internal", FAKE_KEY, "postgresql"):
        assert secret not in text


def test_probe_exception_reports_fail() -> None:
    from app.core.health import run_probes

    def boom() -> bool:
        raise RuntimeError("connection refused to secret-host")

    assert run_probes({"database": boom}) == {"database": False}

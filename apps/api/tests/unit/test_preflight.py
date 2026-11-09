"""Container start preflight (restart after a Windows reboot, README 'Troubleshooting')."""

from pathlib import Path

import pytest
from pydantic import SecretStr

from app import preflight
from app.core.config import get_config


@pytest.fixture
def cfg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> object:
    c = get_config()
    monkeypatch.setattr(c, "idp_storage_dir", tmp_path)
    return c


def test_empty_bind_mount_is_reported(
    cfg: object, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    empty = tmp_path / "keys"
    empty.mkdir()
    monkeypatch.setattr(cfg, "jwt_public_key", None)  # no env key → the (empty) mounted files
    monkeypatch.setattr(cfg, "jwt_private_key", None)
    monkeypatch.setattr(cfg, "jwt_public_key_path", empty / "jwt_public.pem")
    monkeypatch.setattr(cfg, "jwt_private_key_path", empty / "jwt_private.pem")
    problem = preflight.check_keys()
    assert problem is not None and "jwt_public.pem" in problem and "BEGIN" not in problem


def test_readable_keys_and_writable_storage_pass(cfg: object) -> None:
    # conftest sets a real pair through JWT_PRIVATE_KEY / JWT_PUBLIC_KEY
    assert preflight.check_keys() is None
    assert preflight.check_storage() is None


def test_storage_missing_or_read_only(
    cfg: object, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cfg, "idp_storage_dir", tmp_path / "absent")
    assert "missing" in (preflight.check_storage() or "")
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o555)
    monkeypatch.setattr(cfg, "idp_storage_dir", ro)
    try:
        assert "not writable" in (preflight.check_storage() or "")
    finally:
        ro.chmod(0o755)


def test_db_wait_gives_up_with_endpoint_only(cfg: object, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cfg, "database_url", SecretStr("postgresql+psycopg://user:hidden@127.0.0.1:9/aureon")
    )
    problem = preflight.wait_for_db(0)
    assert problem is not None and "127.0.0.1:9" in problem and "hidden" not in problem


def test_main_exit_code(cfg: object, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preflight, "wait_for_db", lambda _t: None)
    assert preflight.main() == 0
    monkeypatch.setattr(preflight, "check_storage", lambda: "IDP storage directory missing: x")
    assert preflight.main() == 1

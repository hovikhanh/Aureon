"""Seed/reset CLI guards + entry points (DEC-062; T-101).

``app.reset`` is destructive, so it must refuse without DEMO_MODE or ``--yes``. The actual
drop/upgrade path (``reset_and_seed``) is exercised by the integration test, which restores the
shared DB to head + seeded afterwards.
"""

from __future__ import annotations

import importlib

import pytest

from app import reset as reset_module
from app.core.config import get_config
from app.seed import SeedError
from app.seed import run as seed_run


def test_reset_refused_without_demo_mode_or_yes() -> None:
    config = get_config().model_copy(update={"demo_mode": False})
    with pytest.raises(reset_module.ResetRefused):
        reset_module.run(confirmed=False, config=config)


def test_reset_main_refused_returns_exit_code_2(monkeypatch: pytest.MonkeyPatch) -> None:
    config = get_config().model_copy(update={"demo_mode": False})
    monkeypatch.setattr(reset_module, "get_config", lambda: config)
    assert reset_module.main([]) == 2


def test_seed_main_reports_error_without_password(monkeypatch: pytest.MonkeyPatch) -> None:
    seed_main = importlib.import_module("app.seed.__main__")

    def _boom() -> None:
        raise SeedError("DEMO_CEO_PASSWORD is not set")

    monkeypatch.setattr(seed_main, "run", _boom)
    assert seed_main.main() == 1


def test_seed_main_success_returns_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    seed_main = importlib.import_module("app.seed.__main__")
    monkeypatch.setattr(seed_main, "run", lambda: None)
    assert seed_main.main() == 0


@pytest.mark.integration
def test_reset_and_seed_rebuilds_and_seeds() -> None:
    """Runs the real downgrade→upgrade→seed, then confirms exactly 5/5 (leaves DB at head)."""
    config = get_config().model_copy(update={"demo_mode": True})
    result = reset_module.run(confirmed=False, config=config)
    assert result.roles_total == 5
    assert result.users_total == 5


@pytest.mark.integration
def test_reset_main_with_yes_flag_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--yes`` authorises the destructive reset even with DEMO_MODE off; leaves DB at head."""
    config = get_config().model_copy(update={"demo_mode": False})
    monkeypatch.setattr(reset_module, "get_config", lambda: config)
    assert reset_module.main(["--yes"]) == 0


@pytest.mark.integration
def test_seed_run_entry_point_commits(capsys: pytest.CaptureFixture[str]) -> None:
    result = seed_run()
    out = capsys.readouterr().out
    assert "Seed complete" in out
    assert result.roles_total == 5
    assert result.users_total == 5

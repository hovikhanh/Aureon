"""TC-DATA-001 — Alembic upgrade head → downgrade base → upgrade head (T-004; 05 §12 G2)."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import REPO_ROOT, get_config

ALEMBIC_INI: Path = REPO_ROOT / "alembic.ini"


def _alembic_config() -> Config:
    cfg = Config(str(ALEMBIC_INI))
    # Keep pytest's logging setup intact.
    cfg.attributes["configure_logger"] = False
    return cfg


def _extensions() -> set[str]:
    engine = create_engine(get_config().database_url.get_secret_value())
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname IN ('pgcrypto', 'vector')")
            )
            return {row[0] for row in rows}
    finally:
        engine.dispose()


@pytest.mark.integration
def test_migrations_are_reversible() -> None:
    cfg = _alembic_config()
    command.upgrade(cfg, "head")
    assert _extensions() == {"pgcrypto", "vector"}
    command.downgrade(cfg, "base")
    assert _extensions() == set()
    # Leave the DB at head for the rest of the suite / developers.
    command.upgrade(cfg, "head")
    assert _extensions() == {"pgcrypto", "vector"}

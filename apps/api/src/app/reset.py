"""``uv run python -m app.reset`` — destructive DB reset + seed (DEC-062; T-101).

Drops the schema to ``base``, upgrades to ``head``, then seeds the 5 demo roles + users. This
wipes ALL data, so it is guarded: it runs only when ``DEMO_MODE=true`` (ConfigService) or an
explicit ``--yes`` flag is passed. Without either it refuses and exits non-zero.

Alembic is driven programmatically (same Config as TC-DATA-001) so the command works from the
repo root per CLAUDE.md § Database.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import REPO_ROOT, ConfigService, get_config
from app.db.session import SessionLocal
from app.seed import SeedError, SeedResult, seed_all

ALEMBIC_INI: Path = REPO_ROOT / "alembic.ini"


class ResetRefused(RuntimeError):
    """Raised when reset is invoked without DEMO_MODE and without --yes."""


def _alembic_config() -> Config:
    cfg = Config(str(ALEMBIC_INI))
    # Do not let Alembic reconfigure logging under the CLI / pytest.
    cfg.attributes["configure_logger"] = False
    return cfg


def reset_and_seed(config: ConfigService | None = None) -> SeedResult:
    """Downgrade to base, upgrade to head, seed. Caller guards for DEMO_MODE / --yes."""
    config = config or get_config()
    cfg = _alembic_config()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    with SessionLocal() as db:
        result = seed_all(db, config)
        db.commit()
    return result


def run(*, confirmed: bool, config: ConfigService | None = None) -> SeedResult:
    config = config or get_config()
    if not (config.demo_mode or confirmed):
        raise ResetRefused(
            "Refusing to reset: this drops ALL data. Re-run with DEMO_MODE=true or pass --yes."
        )
    result = reset_and_seed(config)
    print(
        "Reset complete: schema rebuilt to head and seeded "
        f"({result.roles_total} roles, {result.users_total} users)."
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    confirmed = "--yes" in args
    try:
        run(confirmed=confirmed)
    except ResetRefused as exc:
        print(f"Reset refused: {exc}", file=sys.stderr)
        return 2
    except SeedError as exc:
        print(f"Reset failed during seed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

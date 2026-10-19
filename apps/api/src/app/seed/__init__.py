"""Idempotent seed of the 5 demo roles + 5 demo users (DEC-062; T-101).

Run via ``uv run python -m app.seed`` (see ``__main__``). ``seed_all`` is idempotent: it
UPSERTs by the natural key (``roles.code`` / ``users.email``), so a second run changes nothing
observable. Passwords come only from ``ConfigService.demo_*_password`` (08 §2); a missing one is
a hard error. Stored values are argon2id hashes (DEC-116) — plaintext is never logged or stored.

The seed and reset share a transaction with the caller's session so a failure rolls back cleanly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import ConfigService, get_config
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.modules.auth.models import Role, User
from app.seed.data import ROLES, USERS, RoleSeed, UserSeed
from app.seed.dashboard import seed_dashboard

# Deterministic namespace so seeded ids are stable across runs (idempotent upsert keeps the row).
_SEED_NAMESPACE = uuid.UUID("a11e0000-0000-4000-8000-000000000001")

__all__ = ["SeedError", "SeedResult", "seed_all"]


class SeedError(RuntimeError):
    """Raised when the seed cannot run — e.g. a required demo password env var is unset."""


@dataclass(frozen=True)
class SeedResult:
    """What ``seed_all`` touched, for CLI output and TC-DATA-004."""

    roles_created: int
    roles_updated: int
    users_created: int
    users_updated: int
    metrics_created: int = 0
    metric_values_created: int = 0
    alerts_created: int = 0

    @property
    def roles_total(self) -> int:
        return self.roles_created + self.roles_updated

    @property
    def users_total(self) -> int:
        return self.users_created + self.users_updated


def _stable_id(external_id: str) -> uuid.UUID:
    return uuid.uuid5(_SEED_NAMESPACE, external_id)


def _password_for(user: UserSeed, config: ConfigService) -> str:
    """Return the configured plaintext password, or raise a clear error if it is unset."""
    attr = f"demo_{user.account_key}_password"
    env_var = attr.upper()
    secret: SecretStr | None = getattr(config, attr, None)
    if secret is None:
        raise SeedError(
            f"{env_var} is not set — define it in .env before seeding "
            f"(demo account {user.email}). No hard-coded passwords (08 §2)."
        )
    value = secret.get_secret_value()
    if not value:
        raise SeedError(f"{env_var} is empty — set a non-empty password for {user.email}.")
    return value


def _upsert_role(db: Session, seed: RoleSeed) -> bool:
    """Create or update one role by ``code``. Returns True when a new row was inserted."""
    role = db.scalar(select(Role).where(Role.code == seed.code))
    created = role is None
    if role is None:
        role = Role(code=seed.code)
        db.add(role)
    role.key = seed.key
    role.name_i18n_key = seed.name_i18n_key
    role.pillar_scope = list(seed.pillar_scope)
    role.pillar_agg_scope = list(seed.pillar_agg_scope)
    role.review_pillars = list(seed.review_pillars)
    role.can_view_salary = seed.can_view_salary
    role.home_route = seed.home_route
    if created:
        role.id = _stable_id(seed.code)
    return created


def _upsert_user(db: Session, seed: UserSeed, role_id: uuid.UUID, config: ConfigService) -> bool:
    """Create or update one user by ``email``. Returns True when a new row was inserted.

    The password hash is only (re)written on insert so repeated seeds stay idempotent (a fresh
    argon2 hash each run would churn the row); verification against the configured password still
    holds because the plaintext is unchanged.
    """
    user = db.scalar(select(User).where(User.email == seed.email))
    created = user is None
    if user is None:
        user = User(email=seed.email, password_hash=hash_password(_password_for(seed, config)))
        db.add(user)
    user.full_name = seed.full_name
    user.salutation = seed.salutation
    user.role_id = role_id
    user.is_demo_account = seed.is_demo_account
    if created:
        user.id = _stable_id(seed.external_id)
    return created


def seed_all(db: Session, config: ConfigService | None = None) -> SeedResult:
    """Idempotently seed roles then users into ``db``. Caller commits (CLI does, tests may not).

    Validates every demo password BEFORE writing anything, so a missing env var fails without
    leaving a partial seed.
    """
    config = config or get_config()

    # Fail fast on any missing/empty password before touching the DB.
    for user in USERS:
        _password_for(user, config)

    roles_created = 0
    for role_seed in ROLES:
        if _upsert_role(db, role_seed):
            roles_created += 1
    db.flush()

    role_ids = {role.code: role.id for role in db.scalars(select(Role))}

    users_created = 0
    for user_seed in USERS:
        role_id = role_ids[user_seed.role_code]
        if _upsert_user(db, user_seed, role_id, config):
            users_created += 1
    db.flush()

    # Dashboard: 18 metrics + SEED values + 12 open alerts (T-301/T-403).
    dashboard = seed_dashboard(db)
    db.flush()

    return SeedResult(
        roles_created=roles_created,
        roles_updated=len(ROLES) - roles_created,
        users_created=users_created,
        users_updated=len(USERS) - users_created,
        metrics_created=dashboard.metrics,
        metric_values_created=dashboard.values,
        alerts_created=dashboard.alerts,
    )


def run() -> SeedResult:
    """CLI entry point: open a session, seed, commit, print a summary (no secrets)."""
    with SessionLocal() as db:
        result = seed_all(db)
        db.commit()
    print(
        "Seed complete: "
        f"roles {result.roles_total} ({result.roles_created} created, "
        f"{result.roles_updated} updated), "
        f"users {result.users_total} ({result.users_created} created, "
        f"{result.users_updated} updated), "
        f"metrics {result.metrics_created} created, "
        f"metric_values {result.metric_values_created} created, "
        f"alerts {result.alerts_created} created."
    )
    return result

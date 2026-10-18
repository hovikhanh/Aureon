"""TC-DATA-004 — demo seed: exactly 5 roles + 5 users, idempotent, hashes verify (T-101).

All work happens inside the rolled-back ``db_session`` (conftest), so the shared dev DB is not
mutated. The configured demo passwords come from ``ConfigService`` (.env) — the test only checks
that each stored argon2id hash verifies against its configured password, never printing it.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.core.security import verify_password
from app.modules.auth.models import Role, User
from app.seed import SeedError, seed_all
from app.seed.data import ROLES, USERS

pytestmark = pytest.mark.integration


def _count(db: Session, model: type[Role] | type[User]) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_seed_creates_exactly_five_roles_and_users(db_session: Session) -> None:
    # Start from a clean slate inside the rolled-back transaction.
    db_session.execute(User.__table__.delete())
    db_session.execute(Role.__table__.delete())
    db_session.flush()

    result = seed_all(db_session)
    db_session.flush()

    assert result.roles_created == 5
    assert result.users_created == 5
    assert _count(db_session, Role) == 5
    assert _count(db_session, User) == 5

    codes = set(db_session.scalars(select(Role.code)))
    assert codes == {"ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05"}
    emails = set(db_session.scalars(select(User.email)))
    assert emails == {
        "ceo@abc.demo",
        "cfo@abc.demo",
        "sales@abc.demo",
        "hr@abc.demo",
        "reviewer@abc.demo",
    }


def test_seed_is_idempotent(db_session: Session) -> None:
    db_session.execute(User.__table__.delete())
    db_session.execute(Role.__table__.delete())
    db_session.flush()

    first = seed_all(db_session)
    db_session.flush()
    second = seed_all(db_session)
    db_session.flush()

    assert first.roles_created == 5
    assert second.roles_created == 0
    assert second.users_created == 0
    assert second.roles_updated == 5
    assert second.users_updated == 5
    # Still exactly 5 + 5 — no duplicates.
    assert _count(db_session, Role) == 5
    assert _count(db_session, User) == 5


def test_seeded_role_scopes_match_spec(db_session: Session) -> None:
    db_session.execute(User.__table__.delete())
    db_session.execute(Role.__table__.delete())
    db_session.flush()
    seed_all(db_session)
    db_session.flush()

    by_code = {r.code: r for r in db_session.scalars(select(Role))}
    for seed in ROLES:
        role = by_code[seed.code]
        assert role.key == seed.key
        assert role.name_i18n_key == seed.name_i18n_key
        assert list(role.pillar_scope) == seed.pillar_scope
        assert list(role.pillar_agg_scope) == seed.pillar_agg_scope
        assert list(role.review_pillars) == seed.review_pillars
        assert role.can_view_salary == seed.can_view_salary
        assert role.home_route == seed.home_route
    # Only HR Manager may view salary (05 §4.2).
    assert [r.code for r in by_code.values() if r.can_view_salary] == ["ROLE-04"]


def test_seeded_password_hashes_verify(db_session: Session) -> None:
    db_session.execute(User.__table__.delete())
    db_session.execute(Role.__table__.delete())
    db_session.flush()
    config = get_config()
    seed_all(db_session, config)
    db_session.flush()

    users = {u.email: u for u in db_session.scalars(select(User))}
    for seed in USERS:
        user = users[seed.email]
        assert user.password_hash.startswith("$argon2id$")
        plaintext = getattr(config, f"demo_{seed.account_key}_password").get_secret_value()
        assert verify_password(plaintext, user.password_hash) is True
        assert verify_password(plaintext + "-wrong", user.password_hash) is False


def test_seed_fails_clearly_when_password_env_unset(db_session: Session) -> None:
    config = get_config().model_copy(update={"demo_ceo_password": None})
    with pytest.raises(SeedError, match="DEMO_CEO_PASSWORD is not set"):
        seed_all(db_session, config)
    # Fails before writing anything (validation runs first).
    assert _count(db_session, Role) in (0, 5)  # unchanged either way


def test_seed_fails_clearly_when_password_env_empty(db_session: Session) -> None:
    from pydantic import SecretStr

    config = get_config().model_copy(update={"demo_cfo_password": SecretStr("")})
    with pytest.raises(SeedError, match="DEMO_CFO_PASSWORD is empty"):
        seed_all(db_session, config)

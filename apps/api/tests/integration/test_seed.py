"""TC-AUTH-004 / TC-DATA-001 (T-008) — `app.seed` roles + demo users, idempotent.

Runs on the rolled-back `db_session`; the shared dev DB may already be seeded, so the first
run's outcome is "created" or "unchanged" — the second run must be all "unchanged".
"""

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ConfigService
from app.core.security import verify_password
from app.modules.auth.models import Role, User
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS, ROLE_REFS
from app.seed.auth_seed import DEMO_USERS, ROLES, seed_auth

pytestmark = pytest.mark.integration

ALL_CODES = [
    "CEO", "CFO", "VP_SALES", "HR_MANAGER", "REVIEWER", "CPO", "RISK_MANAGER", "MANAGER",
    "EMPLOYEE", "ADMIN",
]  # fmt: skip


def _cfg(**pw: str) -> ConfigService:
    cfg = ConfigService()
    for role in ALL_CODES:
        object.__setattr__(cfg, f"demo_{role.lower()}_password", None)
    object.__setattr__(cfg, "demo_password", None)
    for key, value in pw.items():
        object.__setattr__(cfg, key, SecretStr(value))
    return cfg


def test_specs_cover_10_roles_and_08_accounts() -> None:
    assert [r.code for r in ROLES] == ALL_CODES
    assert set(ROLE_REFS) == set(ALL_CODES)
    assert [u.role for u in DEMO_USERS] == ALL_CODES  # one account per role (08 §2)
    assert all(u.email.endswith("@abc.demo") for u in DEMO_USERS)


async def test_seed_twice_is_idempotent(db_session: AsyncSession) -> None:
    cfg = _cfg(demo_password="demo-Pass-123")
    first = await seed_auth(db_session, cfg)
    assert set(first.roles.values()) <= {"created", "unchanged", "updated"}
    assert set(first.users.values()) <= {"created", "unchanged", "updated"}
    assert len(first.users) == 10
    second = await seed_auth(db_session, cfg)
    assert set(second.roles.values()) == {"unchanged"}
    assert set(second.users.values()) == {"unchanged"}
    assert second.count("created") == 0

    roles = {r.code: r for r in (await db_session.execute(select(Role))).scalars()}
    assert sorted(roles) == sorted(ALL_CODES)
    for code, role in roles.items():
        assert role.permissions == list(ROLE_PERMISSIONS[code])
        assert role.role_ref == ROLE_REFS[code]
    assert roles["CEO"].pillars == ["F", "O", "C", "U", "S"]
    assert roles["ADMIN"].pillars == []
    ceo = (await db_session.execute(select(User).where(User.email == "ceo@abc.demo"))).scalar_one()
    assert ceo.role_id == roles["CEO"].id
    assert ceo.password_hash.startswith("$argon2id$")
    assert verify_password(ceo.password_hash, "demo-Pass-123")


async def test_drift_is_resynced(db_session: AsyncSession) -> None:
    cfg = _cfg(demo_password="demo-Pass-123")
    await seed_auth(db_session, cfg)
    cfo = (await db_session.execute(select(Role).where(Role.code == "CFO"))).scalar_one()
    v = cfo.version
    cfo.permissions = ["finance:read"]
    user = (await db_session.execute(select(User).where(User.email == "hr@abc.demo"))).scalar_one()
    user.is_active = False
    await db_session.flush()

    report = await seed_auth(db_session, _cfg(demo_password="new-Pass-456"))
    assert report.roles["CFO"] == "updated"
    assert cfo.permissions == list(ROLE_PERMISSIONS["CFO"])
    assert cfo.version == v + 1
    assert report.users["hr@abc.demo"] == "updated"
    assert user.is_active is True
    assert verify_password(user.password_hash, "new-Pass-456")


async def test_per_role_password_and_skip_when_unset(db_session: AsyncSession) -> None:
    report = await seed_auth(db_session, _cfg(demo_ceo_password="ceo-Only-1"))
    assert report.users["ceo@abc.demo"] in {"created", "updated", "unchanged"}
    skipped = {e for e, o in report.users.items() if o == "skipped"}
    assert skipped == {u.email for u in DEMO_USERS} - {"ceo@abc.demo"}
    ceo = (await db_session.execute(select(User).where(User.email == "ceo@abc.demo"))).scalar_one()
    assert verify_password(ceo.password_hash, "ceo-Only-1")


def test_v1_env_names_are_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_SALES_PASSWORD", "v1-sales")
    monkeypatch.delenv("DEMO_VP_SALES_PASSWORD", raising=False)
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", "adm")
    cfg = ConfigService()
    assert cfg.demo_password_for("VP_SALES").get_secret_value() == "v1-sales"  # type: ignore[union-attr]
    assert cfg.demo_password_for("ADMIN").get_secret_value() == "adm"  # type: ignore[union-attr]


async def test_seeded_account_can_log_in(db_session: AsyncSession) -> None:
    from collections.abc import AsyncIterator

    import httpx

    from app.core.deps import get_db
    from app.core.security import verify_access_token
    from app.main import create_app

    await seed_auth(db_session, _cfg(demo_risk_manager_password="risk-Pass-1"))
    app = create_app()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test/api/v1"
    ) as c:
        r = await c.post("/auth/login", json={"email": "risk@abc.demo", "password": "risk-Pass-1"})
    assert r.status_code == 200, r.text
    claims = verify_access_token(r.json()["data"]["access_token"])
    assert claims.role == "RISK_MANAGER"
    assert sorted(claims.permissions) == sorted(ROLE_PERMISSIONS["RISK_MANAGER"])


def test_cli_main_logs_counts(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """`python -m app.seed` wiring: opens a session, seeds, commits, logs counts (no secrets)."""
    import logging

    import app.seed as seed_cli
    from app.core import db
    from app.seed.auth_seed import SeedReport

    calls: list[str] = []

    async def fake_seed(session: AsyncSession) -> SeedReport:
        calls.append(type(session).__name__)
        r = SeedReport()
        r.roles["CEO"] = "unchanged"
        r.users["ceo@abc.demo"] = "skipped"
        return r

    monkeypatch.setattr(seed_cli, "seed_auth", fake_seed)
    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()
    with caplog.at_level(logging.INFO):
        seed_cli.main()
    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()
    assert calls == ["AsyncSession"]
    assert "seed unchanged: 1" in caplog.text
    assert "seed skipped: 1" in caplog.text

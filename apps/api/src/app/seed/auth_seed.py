"""Seed `auth.roles` (10 roles, 02 §5.3) and demo users (08 §2) — idempotent upsert.

Roles: keyed by `code`; permissions / scope_rules / pillars / names re-synced from
`permission_matrix` on every run (`version` bumped only when something changed).
Users: keyed by e-mail; password only from env (`DEMO_<ROLE>_PASSWORD`, fallback
`DEMO_PASSWORD`) — an account whose password is not configured is skipped, never created
with a default. The hash is replaced only when the env password no longer verifies.
"""

import logging
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ConfigService, get_config
from app.core.security import hash_password, verify_password
from app.modules.auth.models import Role, User
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS, ROLE_REFS, ROLE_SCOPES

log = logging.getLogger("app.seed")

Outcome = Literal["created", "updated", "unchanged", "skipped"]


@dataclass(frozen=True)
class RoleSpec:
    code: str
    name_vi: str
    name_en: str
    pillars: tuple[str, ...]


# 02 §1 (name, pillars). REVIEWER / MANAGER / EMPLOYEE / ADMIN have no executive pillar.
ROLES: tuple[RoleSpec, ...] = (
    RoleSpec("CEO", "Tổng giám đốc", "Chief Executive Officer", ("F", "O", "C", "U", "S")),
    RoleSpec("CFO", "Giám đốc tài chính", "Chief Financial Officer", ("F", "S")),
    RoleSpec("VP_SALES", "Giám đốc kinh doanh", "VP Sales", ("C",)),
    RoleSpec("HR_MANAGER", "Trưởng phòng nhân sự", "HR Manager", ("O",)),
    RoleSpec("REVIEWER", "Người duyệt dữ liệu", "Data Reviewer", ()),
    RoleSpec("CPO", "Giám đốc sản phẩm", "Chief Product Officer", ("U",)),
    RoleSpec("RISK_MANAGER", "Quản trị rủi ro", "Risk Manager", ("S",)),
    RoleSpec("MANAGER", "Trưởng bộ phận", "Department Manager", ()),
    RoleSpec("EMPLOYEE", "Nhân viên", "Employee", ()),
    RoleSpec("ADMIN", "Quản trị hệ thống", "System Administrator", ()),
)


@dataclass(frozen=True)
class UserSpec:
    role: str
    email: str
    full_name: str


# 08 §2 — 10 demo accounts, one role each. Department link comes with the HR seed (S1).
DEMO_USERS: tuple[UserSpec, ...] = (
    UserSpec("CEO", "ceo@abc.demo", "Nguyễn Văn An"),
    UserSpec("CFO", "cfo@abc.demo", "Trần Thị Minh"),
    UserSpec("VP_SALES", "sales@abc.demo", "Lê Hoàng Giang"),
    UserSpec("HR_MANAGER", "hr@abc.demo", "Phạm Thị Hạnh"),
    UserSpec("REVIEWER", "reviewer@abc.demo", "Vũ Đức Thắng"),
    UserSpec("CPO", "cpo@abc.demo", "Đỗ Quang Huy"),
    UserSpec("RISK_MANAGER", "risk@abc.demo", "Bùi Thu Trang"),
    UserSpec("MANAGER", "manager@abc.demo", "Hoàng Minh Tuấn"),
    UserSpec("EMPLOYEE", "employee@abc.demo", "Ngô Thị Lan"),
    UserSpec("ADMIN", "admin@abc.demo", "Trịnh Văn Khoa"),
)


@dataclass
class SeedReport:
    roles: dict[str, Outcome] = field(default_factory=dict)
    users: dict[str, Outcome] = field(default_factory=dict)

    def count(self, outcome: Outcome) -> int:
        return sum(v == outcome for v in (*self.roles.values(), *self.users.values()))


def _role_values(spec: RoleSpec) -> dict[str, object]:
    return {
        "role_ref": ROLE_REFS[spec.code],
        "name_vi": spec.name_vi,
        "name_en": spec.name_en,
        "permissions": list(ROLE_PERMISSIONS[spec.code]),
        "scope_rules": dict(ROLE_SCOPES.get(spec.code, {})),
        "pillars": list(spec.pillars),
    }


async def seed_roles(session: AsyncSession, report: SeedReport) -> dict[str, Role]:
    existing = {r.code: r for r in (await session.execute(select(Role))).scalars()}
    for spec in ROLES:
        values = _role_values(spec)
        role = existing.get(spec.code)
        if role is None:
            role = Role(code=spec.code, **values)
            session.add(role)
            existing[spec.code] = role
            report.roles[spec.code] = "created"
            continue
        changed = {k: v for k, v in values.items() if getattr(role, k) != v}
        for k, v in changed.items():
            setattr(role, k, v)
        if changed:
            role.version += 1
        report.roles[spec.code] = "updated" if changed else "unchanged"
    await session.flush()
    return existing


async def seed_users(
    session: AsyncSession, roles: dict[str, Role], report: SeedReport, cfg: ConfigService
) -> None:
    for spec in DEMO_USERS:
        secret = cfg.demo_password_for(spec.role)
        if secret is None or not secret.get_secret_value():
            log.warning("seed: skip %s — DEMO_%s_PASSWORD not set", spec.email, spec.role)
            report.users[spec.email] = "skipped"
            continue
        password = secret.get_secret_value()
        role_id = roles[spec.role].id
        stmt = select(User).where(User.email == spec.email)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if user is None:
            session.add(
                User(
                    email=spec.email,
                    password_hash=hash_password(password),
                    full_name=spec.full_name,
                    role_id=role_id,
                )
            )
            report.users[spec.email] = "created"
            continue
        changed = False
        if user.role_id != role_id or user.full_name != spec.full_name:
            user.role_id, user.full_name, changed = role_id, spec.full_name, True
        if user.deleted_at is not None or not user.is_active:
            user.deleted_at, user.is_active, changed = None, True, True
        if not verify_password(user.password_hash, password):
            user.password_hash, changed = hash_password(password), True
        if changed:
            user.version += 1
        report.users[spec.email] = "updated" if changed else "unchanged"
    await session.flush()


async def seed_auth(session: AsyncSession, cfg: ConfigService | None = None) -> SeedReport:
    """Run inside the caller's transaction (no commit)."""
    report = SeedReport()
    roles = await seed_roles(session, report)
    await seed_users(session, roles, report, cfg or get_config())
    return report

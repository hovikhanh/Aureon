"""Seed `auth.roles` (7 roles v3, R-DEC-12) and demo users (08 §2) — idempotent upsert.

Roles: keyed by `code`; permissions / scope_rules / pillars / names re-synced from
`permission_matrix` on every run (`version` bumped only when something changed).
Users: keyed by e-mail; password only from env (`DEMO_<ROLE>_PASSWORD`, fallback
`DEMO_PASSWORD`) — an account whose password is not configured is skipped, never created
with a default. The hash is replaced only when the env password no longer verifies.

R-DEC-12a: 10 demo accounts giữ nguyên (phủ UC demo), nhưng 5 C-level map vào ROLE-DIR và
phân biệt bằng `scope_pillars` (Finance-DIR={F}, Sales-DIR={C}, HR-DIR={O}…). `env_key` giữ
tên biến mật khẩu cũ (`DEMO_CFO_PASSWORD`…) để không phá cấu hình dev.
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


# 02 §1 (name, pillars) — 7 role v3 (R-DEC-12). CEO phủ toàn khối; DIR mang mọi khối
# (phân biệt từng giám đốc ở user.scope_pillars); MGR/EMP/REV/ADM/AI không có khối điều hành.
ROLES: tuple[RoleSpec, ...] = (
    RoleSpec("CEO", "Tổng giám đốc", "Chief Executive Officer", ("F", "O", "C", "U", "S")),
    RoleSpec("DIR", "Giám đốc khối", "Director / Executive", ("F", "O", "C", "U", "S")),
    RoleSpec("MGR", "Trưởng bộ phận", "Department Manager", ()),
    RoleSpec("EMP", "Nhân viên", "Employee", ()),
    RoleSpec("REV", "Người duyệt dữ liệu", "Data Reviewer", ()),
    RoleSpec("ADM", "Quản trị hệ thống", "System Administrator", ()),
    RoleSpec("AI", "Trợ lý AI", "AI Agent", ()),
)


@dataclass(frozen=True)
class UserSpec:
    role: str  # role_code v3 (CEO/DIR/MGR/EMP/REV/ADM)
    email: str
    full_name: str
    env_key: str  # tên biến mật khẩu dev (giữ tên C-level cũ để không phá .env)
    scope_pillars: tuple[str, ...] = ()  # khối phụ trách của DIR (R-DEC-12a)


# 08 §2 — 10 demo accounts. 5 C-level → DIR, phân biệt bằng scope_pillars (R-DEC-12a).
DEMO_USERS: tuple[UserSpec, ...] = (
    UserSpec("CEO", "ceo@abc.demo", "Nguyễn Văn An", "CEO"),
    UserSpec("DIR", "cfo@abc.demo", "Trần Thị Minh", "CFO", ("F",)),
    UserSpec("DIR", "sales@abc.demo", "Lê Hoàng Giang", "VP_SALES", ("C",)),
    UserSpec("DIR", "hr@abc.demo", "Phạm Thị Hạnh", "HR_MANAGER", ("O",)),
    UserSpec("REV", "reviewer@abc.demo", "Vũ Đức Thắng", "REVIEWER"),
    UserSpec("DIR", "cpo@abc.demo", "Đỗ Quang Huy", "CPO", ("U",)),
    UserSpec("DIR", "risk@abc.demo", "Bùi Thu Trang", "RISK_MANAGER", ("S",)),
    UserSpec("MGR", "manager@abc.demo", "Hoàng Minh Tuấn", "MANAGER"),
    UserSpec("EMP", "employee@abc.demo", "Ngô Thị Lan", "EMPLOYEE"),
    UserSpec("ADM", "admin@abc.demo", "Trịnh Văn Khoa", "ADMIN"),
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
        secret = cfg.demo_password_for(spec.env_key)
        if secret is None or not secret.get_secret_value():
            log.warning("seed: skip %s — DEMO_%s_PASSWORD not set", spec.email, spec.env_key)
            report.users[spec.email] = "skipped"
            continue
        password = secret.get_secret_value()
        role_id = roles[spec.role].id
        pillars = list(spec.scope_pillars)
        stmt = select(User).where(User.email == spec.email)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if user is None:
            session.add(
                User(
                    email=spec.email,
                    password_hash=hash_password(password),
                    full_name=spec.full_name,
                    role_id=role_id,
                    scope_pillars=pillars,
                )
            )
            report.users[spec.email] = "created"
            continue
        changed = False
        if user.role_id != role_id or user.full_name != spec.full_name:
            user.role_id, user.full_name, changed = role_id, spec.full_name, True
        if list(user.scope_pillars) != pillars:
            user.scope_pillars, changed = pillars, True
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

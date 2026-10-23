"""Seed `auth.roles` (7 roles v3, R-DEC-12) and demo users (08 §2) — idempotent upsert.

Roles: keyed by `code`; permissions / scope_rules / pillars / names re-synced from
`permission_matrix` on every run (`version` bumped only when something changed).
Users: keyed by e-mail; password only from env (`DEMO_<ROLE>_PASSWORD`, fallback
`DEMO_PASSWORD`) — an account whose password is not configured is skipped, never created
with a default. The hash is replaced only when the env password no longer verifies.

T-603b (08 §2.1, R-DEC-23/27): 10 tài khoản người + 1 actor AI. DIR phân biệt bằng
`scope_pillars` (Kinh doanh {C}, Tài chính {F}, Nhân sự {O}, Sản phẩm/Công nghệ {U}); mỗi tài
khoản gắn `department_id` + `employee_id` của seed HR. `env_key` giữ tên biến mật khẩu cũ
(`DEMO_CFO_PASSWORD`…) để không phá cấu hình dev.
"""

import logging
import secrets
import uuid
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ConfigService, get_config
from app.core.security import hash_password, verify_password
from app.modules.auth.models import Role, User
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS, ROLE_REFS, ROLE_SCOPES
from app.seed.ids import seed_uuid
from app.seed.org_data import BY_NAME

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
    dept: str  # phòng ban (08 §2.1) — `org_data.DEPARTMENTS[*].code`
    scope_pillars: tuple[str, ...] = ()  # khối phụ trách của DIR (R-DEC-12a)


# 08 §2.1 + 09 §6.2 T-603b — 10 tài khoản demo người. Email giữ như M1.0 để không phá E2E;
# `risk@` (DIR {S}) bỏ vì product/risk đóng băng (R-DEC-16), owner rủi ro = CEO.
DEMO_USERS: tuple[UserSpec, ...] = (
    UserSpec("CEO", "ceo@abc.demo", "Nguyễn Văn An", "CEO", "BOD"),
    UserSpec("DIR", "sales@abc.demo", "Lê Hoàng Giang", "VP_SALES", "SAL", ("C",)),
    UserSpec("DIR", "cfo@abc.demo", "Trần Thị Minh", "CFO", "FIN", ("F",)),
    UserSpec("DIR", "hr@abc.demo", "Phạm Thị Hạnh", "HR_MANAGER", "HR", ("O",)),
    UserSpec("DIR", "cpo@abc.demo", "Đỗ Quang Huy", "CPO", "PRD", ("U",)),
    UserSpec("MGR", "manager@abc.demo", "Hoàng Minh Tuấn", "MANAGER", "SVC"),
    UserSpec("MGR", "office@abc.demo", "Lương Thị Mai", "OFFICE_MANAGER", "ADM"),
    UserSpec("EMP", "employee@abc.demo", "Ngô Thị Lan", "EMPLOYEE", "SVC"),
    UserSpec("REV", "reviewer@abc.demo", "Vũ Đức Thắng", "REVIEWER", "ADM"),
    UserSpec("ADM", "admin@abc.demo", "Trịnh Văn Khoa", "ADMIN", "PRD"),
)
# ROLE-AI actor (R-DEC-27): service account, không đăng nhập bằng mật khẩu (hash ngẫu nhiên,
# không bao giờ log), tạo một lần.
AI_AGENT = UserSpec("AI", "ai-agent@abc.demo", "Trợ lý AI Aureon", "AI", "BOD")


def _links(spec: UserSpec) -> tuple[uuid.UUID, uuid.UUID | None]:
    """(department_id, employee_id) — deterministic ids shared with the HR seed."""
    person = BY_NAME.get(spec.full_name)
    emp = seed_uuid("employee", person.code) if person and spec.role != "AI" else None
    return seed_uuid("department", spec.dept), emp


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


async def _upsert(
    session: AsyncSession, spec: UserSpec, role_id: uuid.UUID, password: str | None
) -> Outcome:
    """Create / re-sync one account. `password=None` → service account (random, unusable)."""
    dept, emp = _links(spec)
    want = {"role_id": role_id, "full_name": spec.full_name, "department_id": dept,
            "employee_id": emp, "scope_pillars": list(spec.scope_pillars),
            "is_service_account": password is None}  # fmt: skip
    user = (
        await session.execute(select(User).where(User.email == spec.email))
    ).scalar_one_or_none()
    if user is None:
        secret = password if password is not None else secrets.token_urlsafe(32)
        session.add(User(email=spec.email, password_hash=hash_password(secret), **want))
        return "created"
    changed = {k: v for k, v in want.items() if getattr(user, k) != v}
    for k, v in changed.items():
        setattr(user, k, v)
    if user.deleted_at is not None or not user.is_active:
        user.deleted_at, user.is_active, changed["active"] = None, True, True
    if password is not None and not verify_password(user.password_hash, password):
        user.password_hash, changed["password"] = hash_password(password), True
    if changed:
        user.version += 1
    return "updated" if changed else "unchanged"


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
        report.users[spec.email] = await _upsert(session, spec, roles[spec.role].id, password)
        await session.flush()
    report.users[AI_AGENT.email] = await _upsert(session, AI_AGENT, roles["AI"].id, None)
    await session.flush()


async def seed_auth(session: AsyncSession, cfg: ConfigService | None = None) -> SeedReport:
    """Run inside the caller's transaction (no commit)."""
    report = SeedReport()
    roles = await seed_roles(session, report)
    await seed_users(session, roles, report, cfg or get_config())
    return report

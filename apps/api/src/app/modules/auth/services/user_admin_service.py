"""D02 Admin & Security — user administration EP-ADM-05..11 (M1.2 T-614, 10 §7.2.1).

Rules (R-DEC-36, 02 §7):
* `scope_pillars` only for DIR; `role_code=AI` only for service accounts (never via this API).
* Only CEO grants / revokes role CEO — ADM → `403 FORBIDDEN_SCOPE` (anti privilege escalation).
* Nobody changes their own role or deactivates themself (`422`).
* Role / pillar change and deactivate revoke **every** refresh token of the user.
Every mutation: audit `auth.user_<verb>` (password masked) + outbox `auth.user_access_changed`
(`{user_id, change, role_code}` — no e-mail / name, R-DEC-35) in the request transaction.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import (
    BusinessRuleError,
    ConflictStateError,
    DuplicateResourceError,
    NotFoundError,
    ScopeDeniedError,
)
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.core.security import hash_password
from app.modules.auth.models import Role, User
from app.modules.auth.repositories import RefreshTokenRepository, RoleRepository, UserRepository
from app.modules.auth.schemas import RoleOut, UserAdminOut, UserCreate, UserUpdate


def user_admin_out(u: User, role: Role) -> UserAdminOut:
    return UserAdminOut(
        id=u.id, email=u.email, full_name=u.full_name, role_id=role.id, role_code=role.code,
        scope_pillars=sorted(u.scope_pillars or []), department_id=u.department_id,
        employee_id=u.employee_id, locale=u.locale, is_active=u.is_active,
        is_service_account=u.is_service_account, last_login_at=u.last_login_at,
        locked_until=u.locked_until, created_at=u.created_at, updated_at=u.updated_at,
        version=u.version,
    )  # fmt: skip


def role_out(r: Role) -> RoleOut:
    return RoleOut(id=r.id, code=r.code, role_ref=r.role_ref, name_vi=r.name_vi,
                   name_en=r.name_en, permissions=sorted(r.permissions),
                   scope_rules=dict(r.scope_rules), pillars=list(r.pillars))  # fmt: skip


def _rule(message: str, reason: str, field: str | None = None) -> BusinessRuleError:
    details: dict[str, Any] = {"reason": reason}
    if field:
        details["field"] = field
    return BusinessRuleError(message, details=details)


class UserAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.tokens = RefreshTokenRepository(db)

    # ---------- reads ----------
    async def list_users(
        self, page: PageParams, *, role_code: str | None, is_active: bool | None,
        department_id: uuid.UUID | None, q: str | None,
    ) -> tuple[list[UserAdminOut], int]:  # fmt: skip
        roles = {r.id: r for r in await self.roles.all()}
        role_id = None
        if role_code is not None:
            match = [r for r in roles.values() if r.code == role_code]
            if not match:
                return [], 0
            role_id = match[0].id
        rows, total = await self.users.page(
            role_id=role_id, is_active=is_active, department_id=department_id, q=q,
            sort_by=page.sort_by, order=page.order, limit=page.limit, offset=page.offset,
        )  # fmt: skip
        return [user_admin_out(u, roles[u.role_id]) for u in rows], total

    async def get(self, user_id: uuid.UUID) -> UserAdminOut:
        u = await self._user(user_id)
        return user_admin_out(u, await self._role(u.role_id))

    async def roles_list(self) -> list[RoleOut]:
        return [role_out(r) for r in await self.roles.all()]

    # ---------- helpers ----------
    async def _user(self, user_id: uuid.UUID, *, lock: bool = False) -> User:
        u = await self.users.get(user_id, lock=lock)
        if u is None:
            raise NotFoundError("user not found")
        return u

    async def _role(self, role_id: uuid.UUID) -> Role:
        role = await self.roles.get(role_id)
        if role is None:
            raise NotFoundError("role not found")
        return role

    async def _role_by_code(self, code: str) -> Role:
        role = await self.roles.by_code(code)
        if role is None:
            raise _rule("unknown role", "not_found", "role_code")
        return role

    @staticmethod
    def _check_grant(actor: Principal, role_code: str, pillars: list[str]) -> None:
        if role_code == "AI":
            raise _rule("role AI is reserved for service accounts", "service_account_only",
                        "role_code")  # fmt: skip
        if pillars and role_code != "DIR":
            raise _rule("scope_pillars only apply to role DIR", "pillars_need_dir",
                        "scope_pillars")  # fmt: skip
        if role_code == "CEO" and actor.role != "CEO":
            raise ScopeDeniedError("only CEO may grant role CEO", details={"role_code": "CEO"})

    async def _check_employee(self, employee_id: uuid.UUID | None, own: uuid.UUID | None) -> None:
        if employee_id is None:
            return
        other = await self.users.by_employee(employee_id)
        if other is not None and other.id != own:
            raise DuplicateResourceError("employee already linked to a user",
                                         details={"employee_id": str(employee_id)})  # fmt: skip

    async def _record(
        self, actor: Principal, verb: str, change: str | None, u: User, role: Role,
        before: UserAdminOut | None, reason: str | None = None,
    ) -> UserAdminOut:  # fmt: skip
        await self.db.flush()
        await self.db.refresh(u)
        out = user_admin_out(u, role)
        await record_audit(
            self.db, action=f"auth.user_{verb}", target_schema="auth", target_table="users",
            target_id=u.id, before=None if before is None else before.model_dump(mode="json"),
            after=out.model_dump(mode="json"), why=reason,
        )  # fmt: skip
        if change is not None:
            await publish_in_tx(
                self.db, event_type="auth.user_access_changed", producer="auth",
                aggregate_schema="auth", aggregate_table="users", aggregate_id=u.id,
                payload={"user_id": str(u.id), "change": change, "role_code": role.code},
            )  # fmt: skip
        return out

    def _bump(self, u: User, actor: Principal, **values: Any) -> None:
        for k, v in values.items():
            setattr(u, k, v)
        u.version = (u.version or 0) + 1
        u.updated_by = actor.user_id

    # ---------- writes ----------
    async def create(self, actor: Principal, body: UserCreate) -> UserAdminOut:
        self._check_grant(actor, body.role_code, list(body.scope_pillars))
        role = await self._role_by_code(body.role_code)
        if await self.users.by_email(body.email) is not None:
            raise DuplicateResourceError("email already used", details={"field": "email"})
        await self._check_employee(body.employee_id, None)
        u = User(
            email=body.email.strip().lower(), full_name=body.full_name,
            password_hash=hash_password(body.initial_password), role_id=role.id,
            scope_pillars=sorted(set(body.scope_pillars)), department_id=body.department_id,
            employee_id=body.employee_id, locale=body.locale, created_by=actor.user_id,
        )  # fmt: skip
        self.db.add(u)
        try:
            async with self.db.begin_nested():
                await self.db.flush()
        except IntegrityError as exc:
            raise DuplicateResourceError("email or employee already used") from exc
        return await self._record(actor, "create", "created", u, role, None)

    async def update(
        self, actor: Principal, user_id: uuid.UUID, body: UserUpdate, expected: int
    ) -> UserAdminOut:
        u = await self._user(user_id, lock=True)
        if u.version != expected:
            raise ConflictStateError(
                f"User was modified (version {u.version}, expected {expected})",
                details={"current_version": u.version, "expected_version": expected},
            )
        old_role = await self._role(u.role_id)
        before = user_admin_out(u, old_role)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        role_code = data.pop("role_code", None) or old_role.code
        pillars = sorted(set(data.pop("scope_pillars", u.scope_pillars) or []))
        if role_code != "DIR" and "scope_pillars" not in body.model_fields_set:
            pillars = []  # leaving DIR drops the pillar scope
        access_changed = role_code != old_role.code or pillars != sorted(u.scope_pillars or [])
        if access_changed:
            if u.id == actor.user_id:
                raise _rule("cannot change your own role", "self_change", "role_code")
            self._check_grant(actor, role_code, pillars)
            if old_role.code == "CEO" and actor.role != "CEO":
                raise ScopeDeniedError("only CEO may change a CEO", details={"role_code": "CEO"})
        role = await self._role_by_code(role_code) if role_code != old_role.code else old_role
        if "employee_id" in data:
            await self._check_employee(data["employee_id"], u.id)
        self._bump(u, actor, role_id=role.id, scope_pillars=pillars, **data)
        if access_changed:
            await self.tokens.revoke_all_for_user(u.id, datetime.now(UTC))
        try:
            async with self.db.begin_nested():
                await self.db.flush()
        except IntegrityError as exc:
            raise DuplicateResourceError("employee already linked to a user") from exc
        return await self._record(actor, "update", "role_changed" if access_changed else None,
                                  u, role, before)  # fmt: skip

    async def set_active(
        self, actor: Principal, user_id: uuid.UUID, active: bool, reason: str
    ) -> UserAdminOut:
        u = await self._user(user_id, lock=True)
        role = await self._role(u.role_id)
        if u.id == actor.user_id and not active:
            raise _rule("cannot deactivate yourself", "self_change")
        if role.code == "CEO" and actor.role != "CEO":
            raise ScopeDeniedError(
                "only CEO may lock or unlock a CEO", details={"role_code": "CEO"}
            )
        if u.is_active == active and (not active or u.locked_until is None):
            return user_admin_out(u, role)  # idempotent: already in the requested state
        before = user_admin_out(u, role)
        if active:
            self._bump(u, actor, is_active=True, failed_login_count=0, locked_until=None)
        else:
            self._bump(u, actor, is_active=False)
            await self.tokens.revoke_all_for_user(u.id, datetime.now(UTC))
        verb, change = ("reactivate", "reactivated") if active else ("deactivate", "deactivated")
        return await self._record(actor, verb, change, u, role, before, reason)

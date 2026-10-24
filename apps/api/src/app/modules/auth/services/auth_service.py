"""Public service interface of `auth` — login, refresh rotation, logout, me (FR-AUTH-01..03).

Refresh tokens are opaque, stored as sha256, rotated on every use; re-use of a rotated token
revokes the whole family (CLAUDE.md §5.3, 10 EP-06). Audit rows for `auth.*` actions are
written via `core.audit.record_audit` (T-007): `auth.login`, `auth.logout`,
`auth.refresh_reuse` (10 §1.8).
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import Actor, record_audit
from app.core.base_model import DEFAULT_TENANT_ID
from app.core.config import get_config
from app.core.errors import InvalidCredentialsError, RefreshTokenInvalidError, UnauthenticatedError
from app.core.security import (
    burn_password_check,
    hash_refresh_token,
    new_refresh_token,
    sign_access_token,
    verify_password,
)
from app.modules.auth.models import RefreshToken, Role, User
from app.modules.auth.repositories import RefreshTokenRepository, RoleRepository, UserRepository
from app.modules.auth.schemas import TokenOut, UserOut


@dataclass(frozen=True)
class ClientInfo:
    user_agent: str | None = None
    ip_address: str | None = None


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.tokens = RefreshTokenRepository(db)

    # --- helpers --------------------------------------------------------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def user_out(user: User, role: Role) -> UserOut:
        return UserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role_code=role.code,
            role_id=role.id,
            permissions=sorted(role.permissions),
            department_id=user.department_id,
            locale=user.locale,
            is_active=user.is_active,
            last_login_at=user.last_login_at,
        )

    async def _role_of(self, user: User) -> Role:
        role = await self.roles.get(user.role_id)
        if role is None:  # FK RESTRICT makes this unreachable; fail closed anyway
            raise UnauthenticatedError("user has no role")
        return role

    async def _issue(
        self, user: User, role: Role, client: ClientInfo, family_id: uuid.UUID | None = None
    ) -> TokenOut:
        cfg = get_config()
        now = self._now()
        access, expires_in = sign_access_token(
            user_id=user.id,
            email=user.email,
            role=role.code,
            role_id=str(role.id),
            permissions=role.permissions,
            department_id=user.department_id,
            tenant_id=DEFAULT_TENANT_ID,  # single-tenant MVP (R-DEC-07/13)
            scope_pillars=tuple(user.scope_pillars),  # R-DEC-12a — khối phụ trách của DIR
            employee_id=user.employee_id,  # R-DEC-41
            now=now,
        )
        raw = new_refresh_token()
        await self.tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_refresh_token(raw),
                family_id=family_id or uuid.uuid4(),
                expires_at=now + timedelta(seconds=cfg.jwt_refresh_ttl_seconds),
                user_agent=client.user_agent,
                ip_address=client.ip_address,
            )
        )
        return TokenOut(
            access_token=access,
            expires_in=expires_in,
            refresh_token=raw,
            user=self.user_out(user, role),
        )

    # --- EP-02 login ----------------------------------------------------------------------

    async def login(self, email: str, password: str, client: ClientInfo) -> TokenOut:
        """Same 401 for unknown email / wrong password / inactive / locked (no enumeration)."""
        cfg = get_config()
        now = self._now()
        user = await self.users.by_email(email)
        if user is None:
            burn_password_check(password)
            raise InvalidCredentialsError("invalid credentials")
        if user.locked_until is not None and user.locked_until > now:
            burn_password_check(password)
            raise InvalidCredentialsError("invalid credentials")
        if not user.is_active or not verify_password(user.password_hash, password):
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= cfg.auth_max_failed_logins:
                user.locked_until = now + timedelta(minutes=cfg.auth_lockout_minutes)
                user.failed_login_count = 0
            await self.db.commit()
            raise InvalidCredentialsError("invalid credentials")

        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = now
        role = await self._role_of(user)
        out = await self._issue(user, role, client)
        await record_audit(
            self.db,
            action="auth.login",
            target_schema="auth",
            target_table="users",
            target_id=user.id,
            metadata={"ip_address": client.ip_address},
            actor=Actor(type="USER", user_id=user.id, role=role.code),
        )
        await self.db.commit()
        return out

    # --- EP-06 refresh (rotation + reuse detection) ---------------------------------------

    async def refresh(self, raw_token: str, client: ClientInfo) -> TokenOut:
        now = self._now()
        stored = await self.tokens.by_hash(hash_refresh_token(raw_token))
        if stored is None:
            raise RefreshTokenInvalidError("unknown refresh token")
        if stored.revoked_at is not None:
            # Re-use of a rotated/revoked token → revoke the whole chain (10 EP-06).
            await self.tokens.revoke_family(stored.family_id, now)
            await record_audit(
                self.db,
                action="auth.refresh_reuse",
                target_schema="auth",
                target_table="users",
                target_id=stored.user_id,
                metadata={"family_id": str(stored.family_id), "ip_address": client.ip_address},
                actor=Actor(type="USER", user_id=stored.user_id),
            )
            await self.db.commit()
            raise RefreshTokenInvalidError("refresh token reused")
        if stored.expires_at <= now:
            raise RefreshTokenInvalidError("refresh token expired")

        user = await self.users.get(stored.user_id)
        if user is None or not user.is_active:
            await self.tokens.revoke_family(stored.family_id, now)
            await self.db.commit()
            raise RefreshTokenInvalidError("user inactive")

        await self.tokens.revoke(stored, now)
        role = await self._role_of(user)  # permissions re-derived from current role (02 §4)
        out = await self._issue(user, role, client, family_id=stored.family_id)
        await self.db.commit()
        return out

    # --- EP-07 logout ---------------------------------------------------------------------

    async def logout(self, raw_token: str, user_id: uuid.UUID) -> None:
        """Idempotent: unknown / foreign / already-revoked tokens are a silent no-op (204)."""
        stored = await self.tokens.by_hash(hash_refresh_token(raw_token))
        if stored is None or stored.user_id != user_id or stored.revoked_at is not None:
            return
        await self.tokens.revoke_family(stored.family_id, self._now())
        await record_audit(
            self.db,
            action="auth.logout",
            target_schema="auth",
            target_table="users",
            target_id=user_id,
        )
        await self.db.commit()

    # --- EP-03 me -------------------------------------------------------------------------

    async def me(self, user_id: uuid.UUID) -> UserOut:
        user = await self.users.get(user_id)
        if user is None or not user.is_active:
            raise UnauthenticatedError("user not found or inactive")
        return self.user_out(user, await self._role_of(user))

    async def email_contact(self, user_id: uuid.UUID) -> tuple[str, str] | None:
        """`(email, locale)` of an active user for e-mail notifications (T-616b); else `None`."""
        user = await self.users.get(user_id)
        if user is None or not user.is_active or user.is_service_account:
            return None
        return user.email, user.locale

    async def user_id_for_employee(self, employee_id: uuid.UUID | None) -> uuid.UUID | None:
        """Public employee → active user id (R-DEC-46 notifications). `None` when the employee
        has no (active) account — callers skip the notification and log at info level."""
        if employee_id is None:
            return None
        user = await self.users.by_employee(employee_id)
        if user is None or not user.is_active:
            return None
        return user.id

    async def user_id_for_ref(self, ref: uuid.UUID | None) -> uuid.UUID | None:
        """Task people refs are an employee id or (no employee record) a user id (R-DEC-41)."""
        if ref is None:
            return None
        if (uid := await self.user_id_for_employee(ref)) is not None:
            return uid
        user = await self.users.get(ref)
        return user.id if user is not None and user.is_active else None

    async def user_names(self, user_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, str]:
        """Public `{user_id: full_name}` (EP-WF-01 `requested_by_name`)."""
        return await self.users.names(list(set(user_ids)))

    async def users_with_roles(
        self, role_codes: Sequence[str], *, department_id: uuid.UUID | None = None
    ) -> list[uuid.UUID]:
        """Public: active (non-service) users holding one of `role_codes`, optionally in a
        department — approval notification recipients (R-DEC-45/46)."""
        from sqlalchemy import select

        roles = (await self.db.execute(select(Role.id).where(Role.code.in_(role_codes)))).scalars()
        users = await self.users.active_by_roles(list(roles), department_id)
        return [u.id for u in users]

    async def find_user_by_role(
        self, role_code: str, *, department_id: uuid.UUID | None = None
    ) -> uuid.UUID | None:
        """Public lookup for escalation routing (04 §8.3): an active user with the given role,
        preferring one in `department_id`. Returns a user id or None. Used by IDP SLA escalation
        to pick the manager / department head to notify (DEC-125 — no model import elsewhere)."""
        from sqlalchemy import select

        role = (
            await self.db.execute(select(Role).where(Role.code == role_code))
        ).scalar_one_or_none()
        if role is None:
            return None
        base = select(User).where(User.role_id == role.id, User.is_active.is_(True))
        if department_id is not None:
            scoped = (
                (await self.db.execute(base.where(User.department_id == department_id)))
                .scalars()
                .first()
            )
            if scoped is not None:
                return scoped.id
        user = (await self.db.execute(base)).scalars().first()
        return user.id if user is not None else None

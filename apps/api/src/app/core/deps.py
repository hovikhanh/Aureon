"""Shared FastAPI dependencies: DB session, current principal (RS256), permission guards.

RBAC layer (b) of 10 §2.2: every endpoint declares exactly one `require_permission(...)`.
Identity comes only from the verified JWT — never from body/query (CLAUDE.md §5.3).
"""

from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass, field
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import Actor, set_actor
from app.core.db import get_sessionmaker
from app.core.errors import PermissionDeniedError, UnauthenticatedError
from app.core.permissions import DOMAIN_PILLAR, permission_name, pillar_allows
from app.core.security import verify_access_token
from app.core.tenant import set_tenant


@dataclass(frozen=True)
class Principal:
    """Caller identity built from the JWT."""

    user_id: UUID
    role: str
    permissions: frozenset[str] = field(default_factory=frozenset)
    department_id: UUID | None = None
    email: str = ""
    role_id: str = ""
    jti: str = ""
    tenant_id: UUID | None = None  # always set for a request principal (R-DEC-21)
    scope_pillars: frozenset[str] = field(default_factory=frozenset)

    def has(self, permission: str) -> bool:
        """Effective check: hold the permission AND the domain's pillar is in scope (R-DEC-12a)."""
        return permission in self.permissions and pillar_allows(self.scope_pillars, permission)

    def in_pillar(self, domain: str) -> bool:
        """True nếu caller phụ trách khối của `domain` (R-DEC-12a).

        CEO / non-DIR / DIR scope rỗng (toàn khối) → True; domain cross-pillar → True;
        DIR có scope_pillars → chỉ True khi pillar của domain nằm trong scope.
        """
        if not self.scope_pillars:
            return True
        pillar = DOMAIN_PILLAR.get(domain)
        return pillar is None or pillar in self.scope_pillars


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        raise UnauthenticatedError("missing bearer token")
    claims = verify_access_token(creds.credentials)
    if claims.tenant_id is None:  # R-DEC-21: no tenant → no business data (fail closed)
        raise UnauthenticatedError("token has no tenant_id claim")
    set_tenant(claims.tenant_id)  # reset per request by TenantContextMiddleware
    set_actor(Actor(type="USER", user_id=claims.sub, role=claims.role))  # audit_logs.actor_*
    return Principal(
        user_id=claims.sub,
        role=claims.role,
        permissions=frozenset(claims.permissions),
        department_id=claims.department_id,
        email=claims.email,
        role_id=claims.role_id,
        jti=claims.jti,
        tenant_id=claims.tenant_id,
        scope_pillars=frozenset(claims.scope_pillars),
    )


CurrentUser = Annotated[Principal, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]

Guard = Callable[..., Coroutine[Any, Any, Principal]]


def require_permission(domain: str, action: str | None = None) -> Guard:
    """`require_permission("finance:read")` or `require_permission("finance", "read")`.

    Unknown permissions fail at import time (02 §5.2); missing → `403 FORBIDDEN_ROLE`.
    """
    perm = permission_name(domain, action)

    async def _check(user: CurrentUser) -> Principal:
        if not user.has(perm):
            raise PermissionDeniedError(f"missing permission {perm}", details={"required": perm})
        return user

    return _check


def require_pillar_permission(domain: str, action: str | None = None) -> Guard:
    """Như `require_permission` nhưng CHẶN DIR ngoài khối của `domain` (R-DEC-12a, Option A).

    Dùng cho các endpoint đọc chi-tiết/bản-ghi mà module muốn cô lập theo khối (VD
    sales record list): ở nền v2.1 các vai ngoài khối chỉ có `:query` (tổng hợp), không có
    `:read` (chi tiết). Khi gộp về DIR union, ta tái lập ranh giới đó bằng scope_pillars.
    Các module cho phép đọc liên-miền (VD risk linked-reader) vẫn dùng `require_permission`.
    """
    perm = permission_name(domain, action)
    dom = perm.split(":", 1)[0]

    async def _check(user: CurrentUser) -> Principal:
        if not user.has(perm):
            raise PermissionDeniedError(f"missing permission {perm}", details={"required": perm})
        if not user.in_pillar(dom):
            raise PermissionDeniedError(
                f"{dom} outside your pillar scope", details={"required": perm}
            )
        return user

    return _check


def require_role(*roles: str) -> Guard:
    """v1 compatibility alias only (CLAUDE.md §5.2) — prefer `require_permission`."""

    async def _check(user: CurrentUser) -> Principal:
        if user.role not in roles:
            raise PermissionDeniedError(f"role {user.role} not allowed")
        return user

    return _check

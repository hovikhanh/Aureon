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
from app.core.permissions import permission_name
from app.core.security import verify_access_token


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

    def has(self, permission: str) -> bool:
        return permission in self.permissions


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
    set_actor(Actor(type="USER", user_id=claims.sub, role=claims.role))  # audit_logs.actor_*
    return Principal(
        user_id=claims.sub,
        role=claims.role,
        permissions=frozenset(claims.permissions),
        department_id=claims.department_id,
        email=claims.email,
        role_id=claims.role_id,
        jti=claims.jti,
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


def require_role(*roles: str) -> Guard:
    """v1 compatibility alias only (CLAUDE.md §5.2) — prefer `require_permission`."""

    async def _check(user: CurrentUser) -> Principal:
        if user.role not in roles:
            raise PermissionDeniedError(f"role {user.role} not allowed")
        return user

    return _check

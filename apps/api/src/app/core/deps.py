"""Shared FastAPI dependencies.

`get_current_user`, `require_permission` are wired to RS256 in T-004; until then they
fail closed (default deny — 02 §5) so no endpoint can be accidentally public.
"""

from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass, field
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_sessionmaker


@dataclass(frozen=True)
class Principal:
    """Caller identity built from the JWT — never from body/query (CLAUDE.md §5.3)."""

    user_id: UUID
    role: str
    permissions: frozenset[str] = field(default_factory=frozenset)
    department_id: UUID | None = None


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


async def get_current_user() -> Principal:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHENTICATED")


CurrentUser = Annotated[Principal, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


def require_permission(permission: str) -> Callable[..., Coroutine[Any, Any, Principal]]:
    """`Depends(require_permission("finance:read"))` — exactly one per endpoint."""

    async def _check(user: CurrentUser) -> Principal:
        if permission not in user.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN_ROLE")
        return user

    return _check


def require_role(*roles: str) -> Callable[..., Coroutine[Any, Any, Principal]]:
    """v1 compatibility alias only (CLAUDE.md §5.2) — prefer `require_permission`."""

    async def _check(user: CurrentUser) -> Principal:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN_ROLE")
        return user

    return _check

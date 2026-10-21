"""Data access for schema `auth` (users, roles, refresh_tokens)."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RefreshToken, Role, User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def by_email(self, email: str) -> User | None:
        stmt = select(User).where(
            func.lower(User.email) == email.strip().lower(), User.deleted_at.is_(None)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        return (await self.db.execute(stmt)).scalar_one_or_none()


class RoleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, role_id: uuid.UUID) -> Role | None:
        return await self.db.get(Role, role_id)

    async def by_code(self, code: str) -> Role | None:
        return (await self.db.execute(select(Role).where(Role.code == code))).scalar_one_or_none()

    async def all(self) -> Sequence[Role]:
        return (await self.db.execute(select(Role).order_by(Role.role_ref))).scalars().all()


class RefreshTokenRepository:
    """Append-only table: rows are inserted, then only `revoked_at` is stamped."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        await self.db.flush()
        return token

    async def by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def revoke(self, token: RefreshToken, at: datetime) -> None:
        token.revoked_at = at
        await self.db.flush()

    async def revoke_family(self, family_id: uuid.UUID, at: datetime) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=at)
        )

    async def revoke_all_for_user(self, user_id: uuid.UUID, at: datetime) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=at)
        )

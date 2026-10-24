"""Data access for schema `auth` (users, roles, refresh_tokens)."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, or_, select, update
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

    async def get(self, user_id: uuid.UUID, *, lock: bool = False) -> User | None:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        if lock:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def by_employee(self, employee_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.employee_id == employee_id, User.deleted_at.is_(None))
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def names(self, ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not ids:
            return {}
        rows = await self.db.execute(select(User.id, User.full_name).where(User.id.in_(ids)))
        return {i: n for i, n in rows.all()}

    async def active_by_roles(
        self, role_ids: Sequence[uuid.UUID], department_id: uuid.UUID | None
    ) -> Sequence[User]:
        stmt = select(User).where(
            User.role_id.in_(role_ids), User.is_active.is_(True), User.deleted_at.is_(None),
            User.is_service_account.is_(False),
        )  # fmt: skip
        if department_id is not None:
            stmt = stmt.where(User.department_id == department_id)
        return (await self.db.execute(stmt.order_by(User.id))).scalars().all()

    async def page(
        self, *, role_id: uuid.UUID | None, is_active: bool | None,
        department_id: uuid.UUID | None, q: str | None, sort_by: str, order: str,
        limit: int, offset: int,
    ) -> tuple[Sequence[User], int]:  # fmt: skip
        """EP-ADM-05 list (identity table — global, single-tenant MVP, R-DEC-07)."""
        stmt = select(User).where(User.deleted_at.is_(None))
        if role_id is not None:
            stmt = stmt.where(User.role_id == role_id)
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
        if department_id is not None:
            stmt = stmt.where(User.department_id == department_id)
        if q:
            like = f"%{q.strip().lower()}%"
            stmt = stmt.where(or_(func.lower(User.email).like(like),
                                  func.lower(User.full_name).like(like)))  # fmt: skip
        total = int(await self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        col = getattr(User, sort_by)
        stmt = stmt.order_by(col.asc() if order == "asc" else col.desc(), User.id)
        return (await self.db.execute(stmt.limit(limit).offset(offset))).scalars().all(), total


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

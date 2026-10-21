"""Public service interface of `auth` — the only entry point for other modules."""

from sqlalchemy.ext.asyncio import AsyncSession


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

"""Public service interface of `platform` — the only entry point for other modules."""

from sqlalchemy.ext.asyncio import AsyncSession


class PlatformService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

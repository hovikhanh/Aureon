"""Public service interface of `hr` — the only entry point for other modules."""

from sqlalchemy.ext.asyncio import AsyncSession


class HrService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

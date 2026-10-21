"""Public service interface of `risk` — the only entry point for other modules."""

from sqlalchemy.ext.asyncio import AsyncSession


class RiskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

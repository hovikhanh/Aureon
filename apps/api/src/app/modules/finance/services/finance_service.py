"""Public service interface of `finance` — the only entry point for other modules."""

from sqlalchemy.ext.asyncio import AsyncSession


class FinanceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

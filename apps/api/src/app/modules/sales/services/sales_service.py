"""Public service interface of `sales` — the only entry point for other modules."""

from sqlalchemy.ext.asyncio import AsyncSession


class SalesService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

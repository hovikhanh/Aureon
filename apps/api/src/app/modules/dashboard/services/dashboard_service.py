"""Public service interface of `dashboard` — the only entry point for other modules."""

from sqlalchemy.ext.asyncio import AsyncSession


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

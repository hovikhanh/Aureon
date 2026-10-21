"""Public service interface of `execution` — the only entry point for other modules."""

from sqlalchemy.ext.asyncio import AsyncSession


class ExecutionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

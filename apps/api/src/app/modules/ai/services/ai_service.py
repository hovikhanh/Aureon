"""Public service interface of `ai` — the only entry point for other modules."""

from sqlalchemy.ext.asyncio import AsyncSession


class AiService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

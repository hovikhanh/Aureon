"""BaseService — holds the request `AsyncSession` + the module's repository.

Cross-module calls pass the caller's session in (CLAUDE.md §4.3) — never open a new one.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import Base
from app.core.base_repository import BaseRepository


class BaseService[ModelT: Base]:
    def __init__(self, db: AsyncSession, repo: BaseRepository[ModelT]) -> None:
        self.db = db
        self.repo = repo

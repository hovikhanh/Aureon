"""Generic async CRUD repository. Only the owning module uses its repositories (DEC-125)."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import Base

MAX_LIMIT = 100  # DEC-130


class BaseRepository[ModelT: Base]:
    model: type[ModelT]

    def __init__(self, db: AsyncSession, model: type[ModelT] | None = None) -> None:
        self.db = db
        if model is not None:
            self.model = model

    def _has(self, attr: str) -> bool:
        return hasattr(self.model, attr)

    def _col(self, attr: str) -> Any:
        return getattr(self.model, attr)

    def _live(self) -> Select[ModelT]:
        stmt = select(self.model)
        if self._has("deleted_at"):
            stmt = stmt.where(self._col("deleted_at").is_(None))
        return stmt

    async def get(self, id_: uuid.UUID) -> ModelT | None:
        result = await self.db.execute(self._live().where(self._col("id") == id_))
        return result.scalar_one_or_none()

    async def list(self, *, limit: int = 20, offset: int = 0) -> Sequence[ModelT]:
        stmt = self._live().limit(max(1, min(limit, MAX_LIMIT))).offset(max(0, offset))
        if self._has("created_at"):
            stmt = stmt.order_by(self._col("created_at").desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self._live().subquery())
        return int((await self.db.execute(stmt)).scalar_one())

    async def create(self, **values: Any) -> ModelT:
        obj = self.model(**values)
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def update(self, obj: ModelT, **values: Any) -> ModelT:
        if self._has("version"):
            values["version"] = (getattr(obj, "version", None) or 0) + 1
        for key, value in values.items():
            setattr(obj, key, value)
        await self.db.flush()
        return obj

    async def soft_delete(self, obj: ModelT) -> None:
        if not self._has("deleted_at"):
            raise TypeError(f"{self.model.__name__} is not soft-deletable")
        await self.update(obj, deleted_at=datetime.now(UTC))

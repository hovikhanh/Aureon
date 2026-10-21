"""Generic async CRUD repository. Only the owning module uses its repositories (DEC-125)."""

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import Base
from app.core.errors import ConflictStateError

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

    async def list_page(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "created_at",
        order: str = "desc",
        filters: Mapping[str, Any] | None = None,
        where: Sequence[ColumnElement[bool]] = (),
    ) -> tuple[Sequence[ModelT], int]:
        """`(items, total)` for 10 §1.5. `filters` = exact-match on model columns (AND);
        `where` = extra SQL predicates (ranges, IN, …) built by the module repository.

        `sort_by` must already be whitelisted by the route (`core.pagination.page_params`).
        """
        stmt = self._live()
        for name, value in (filters or {}).items():
            if not self._has(name):
                raise ValueError(f"{self.model.__name__} has no column {name!r}")
            stmt = stmt.where(self._col(name) == value)
        for clause in where:
            stmt = stmt.where(clause)
        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.db.execute(total_stmt)).scalar_one())
        if not self._has(sort_by):
            raise ValueError(f"{self.model.__name__} has no column {sort_by!r}")
        col = self._col(sort_by)
        stmt = stmt.order_by(col.asc() if order == "asc" else col.desc())
        if sort_by != "id" and self._has("id"):
            stmt = stmt.order_by(self._col("id"))  # deterministic tie-break
        stmt = stmt.limit(max(1, min(limit, MAX_LIMIT))).offset(max(0, offset))
        items = (await self.db.execute(stmt)).scalars().all()
        return items, total

    async def create(self, **values: Any) -> ModelT:
        obj = self.model(**values)
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def update(
        self, obj: ModelT, *, expected_version: int | None = None, **values: Any
    ) -> ModelT:
        """Apply `values`; C19 `version` += 1 (10 §1.1).

        `expected_version` (from `If-Match` / body `version`) → the row is re-read under
        `SELECT … FOR UPDATE` and compared, so two concurrent PATCHes with the same version
        cannot both win: the second waits for the lock, sees the bumped version → 409.
        """
        if self._has("version"):
            if expected_version is not None:
                await self.db.refresh(obj, attribute_names=["version"], with_for_update=True)
                current = getattr(obj, "version", None)
                if current != expected_version:
                    raise ConflictStateError(
                        f"{self.model.__name__} was modified (version {current}, "
                        f"expected {expected_version})",
                        details={"current_version": current, "expected_version": expected_version},
                    )
            values["version"] = (getattr(obj, "version", None) or 0) + 1
        elif expected_version is not None:
            raise TypeError(f"{self.model.__name__} has no version column (C19)")
        for key, value in values.items():
            setattr(obj, key, value)
        await self.db.flush()
        return obj

    async def soft_delete(self, obj: ModelT) -> None:
        if not self._has("deleted_at"):
            raise TypeError(f"{self.model.__name__} is not soft-deletable")
        await self.update(obj, deleted_at=datetime.now(UTC))

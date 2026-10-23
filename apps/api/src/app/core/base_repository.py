"""Generic async CRUD repository. Only the owning module uses its repositories (DEC-125)."""

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import Base, TenantMixin
from app.core.errors import ConflictStateError
from app.core.tenant import TenantMismatchError, require_tenant

MAX_LIMIT = 100  # DEC-130


def tenant_ids_where(model: Any, *clauses: ColumnElement[bool]) -> Select[tuple[uuid.UUID]]:
    """Tenant-scoped `SELECT id FROM model WHERE …` for `col.in_(…)` scope predicates.

    Module repositories expose it per model (e.g. `MeetingRepository.ids_where`) so services
    never build SQL on a business entity themselves (R-DEC-21, TC-M11-05).
    """
    stmt = select(model.id)
    if issubclass(model, TenantMixin):
        stmt = stmt.where(model.tenant_id == require_tenant())
    for clause in clauses:
        stmt = stmt.where(clause)
    return stmt


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

    @property
    def _tenant_scoped(self) -> bool:
        return issubclass(self.model, TenantMixin)

    def _scoped[*Ts](self, stmt: Select[*Ts]) -> Select[*Ts]:
        """Layer 1 (R-DEC-21): `WHERE tenant_id = current_tenant`; no context → raise."""
        if self._tenant_scoped:
            stmt = stmt.where(self._col("tenant_id") == require_tenant())
        return stmt

    def _live(self) -> Select[ModelT]:
        stmt: Select[ModelT] = self._scoped(select(self.model))
        if self._has("deleted_at"):
            stmt = stmt.where(self._col("deleted_at").is_(None))
        return stmt

    @classmethod
    def ids_where(cls, *clauses: ColumnElement[bool]) -> Select[tuple[uuid.UUID]]:
        """`tenant_ids_where(cls.model, …)` — subquery for a service-side scope predicate."""
        return tenant_ids_where(cls.model, *clauses)

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
        if self._tenant_scoped:
            tenant = require_tenant()
            if values.setdefault("tenant_id", tenant) != tenant:
                raise TenantMismatchError("create() for another tenant")
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
        if self._tenant_scoped and values.get("tenant_id", require_tenant()) != require_tenant():
            raise TenantMismatchError("update() cannot move a row to another tenant")
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

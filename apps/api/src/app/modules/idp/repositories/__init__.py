"""`idp` repositories — tenant-scoped reads of IDP business entities (R-DEC-21).

Only `idp` services use them (DEC-125). Non-tenant tables (jobs, assignments, catalogs) are
still queried directly by services; their access is reached through a tenant-scoped document.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, func, select

from app.core.base_repository import BaseRepository
from app.core.tenant import require_tenant
from app.modules.idp.models import (
    DocumentAction,
    ExtractedField,
    ImportBatch,
    ImportRow,
    ReviewAssignment,
    SourceDocument,
)


class SourceDocumentRepository(BaseRepository[SourceDocument]):
    model = SourceDocument

    async def by_id(self, document_id: uuid.UUID, *, live: bool = True) -> SourceDocument | None:
        """`live=False` also returns soft-deleted rows (pipeline works on its own document)."""
        stmt = self._live() if live else self._scoped(select(SourceDocument))
        stmt = stmt.where(SourceDocument.id == document_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def first_original_by_sha(self, digest: str) -> SourceDocument | None:
        stmt = (
            self._live()
            .where(
                SourceDocument.sha256 == digest,
                SourceDocument.duplicate_of_id.is_(None),
                SourceDocument.status != "ROLLED_BACK",  # R-DEC-66: resubmission = new document
            )
            .order_by(SourceDocument.submitted_at.asc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def page(
        self, where: Sequence[ColumnElement[bool]], order: Any, *, limit: int, offset: int
    ) -> tuple[Sequence[SourceDocument], int]:
        base = self._live()
        for clause in where:
            base = base.where(clause)
        count = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count)).scalar_one()
        stmt = base.order_by(order).limit(limit).offset(offset)
        return (await self.db.execute(stmt)).scalars().all(), int(total)

    async def status_counts(self, where: Sequence[ColumnElement[bool]]) -> dict[str, int]:
        """`{status: n}` of live documents under `where` (EP-DC-13 `meta.counts`)."""
        stmt = self._scoped(select(SourceDocument.status, func.count())).where(
            SourceDocument.deleted_at.is_(None), *where
        )
        rows = (await self.db.execute(stmt.group_by(SourceDocument.status))).all()
        return {s: int(n) for s, n in rows}

    async def matches(self, document_id: uuid.UUID, clause: ColumnElement[bool]) -> bool:
        stmt = self._live().where(SourceDocument.id == document_id, clause)
        return (await self.db.execute(stmt)).first() is not None

    async def awaiting_review_with_assignment(
        self,
    ) -> list[tuple[SourceDocument, ReviewAssignment]]:
        stmt = (
            self._scoped(select(SourceDocument, ReviewAssignment))
            .join(ReviewAssignment, ReviewAssignment.source_document_id == SourceDocument.id)
            .where(
                SourceDocument.status.in_(("NEEDS_REVIEW", "IN_REVIEW")),
                SourceDocument.deleted_at.is_(None),
                ReviewAssignment.is_current.is_(True),
            )
        )
        return [(d, a) for d, a in (await self.db.execute(stmt)).all()]


class ExtractedFieldRepository(BaseRepository[ExtractedField]):
    model = ExtractedField

    async def for_job(self, job_id: uuid.UUID, *, ordered: bool = False) -> list[ExtractedField]:
        stmt = self._scoped(select(ExtractedField))
        stmt = stmt.where(ExtractedField.extraction_job_id == job_id)
        if ordered:
            stmt = stmt.order_by(ExtractedField.field_name.asc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def by_ids(self, ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, ExtractedField]:
        if not ids:
            return {}
        stmt = self._scoped(select(ExtractedField)).where(ExtractedField.id.in_(list(ids)))
        return {f.id: f for f in (await self.db.execute(stmt)).scalars()}


class DocumentActionRepository(BaseRepository[DocumentAction]):
    """`idp.document_actions` — one row per executed ACT (R-DEC-63, append + status flip)."""

    model = DocumentAction

    async def for_document(
        self, document_id: uuid.UUID, *, newest_first: bool = False
    ) -> list[DocumentAction]:
        order = DocumentAction.seq.desc() if newest_first else DocumentAction.seq
        stmt = self._scoped(select(DocumentAction)).where(
            DocumentAction.source_document_id == document_id
        )
        return list((await self.db.execute(stmt.order_by(order))).scalars())


class ImportRepository(BaseRepository[ImportBatch]):
    """C5 `import_batches` + `import_rows` (R-DEC-62), tenant-scoped."""

    model = ImportBatch

    async def excel_batch(self, batch_id: uuid.UUID) -> ImportBatch | None:
        stmt = self._scoped(select(ImportBatch)).where(
            ImportBatch.id == batch_id, ImportBatch.kind == "excel_import"
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def _rows(self, batch_id: uuid.UUID, status: str | None) -> Any:
        stmt = select(ImportRow).where(
            ImportRow.import_batch_id == batch_id, ImportRow.tenant_id == require_tenant()
        )
        return stmt if status in (None, "all") else stmt.where(ImportRow.status == status)

    async def rows(
        self, batch_id: uuid.UUID, *, status: str | None = None, limit: int | None = None,
        offset: int = 0, desc: bool = False,
    ) -> list[ImportRow]:  # fmt: skip
        key = ImportRow.row_number.desc() if desc else ImportRow.row_number.asc()
        stmt = self._rows(batch_id, status).order_by(key).offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    async def count_rows(self, batch_id: uuid.UUID, status: str | None) -> int:
        sub = self._rows(batch_id, status).subquery()
        return int((await self.db.execute(select(func.count()).select_from(sub))).scalar_one())

    async def replace_rows(self, batch_id: uuid.UUID, rows: list[ImportRow]) -> None:
        from sqlalchemy import delete

        await self.db.execute(delete(ImportRow).where(
            ImportRow.import_batch_id == batch_id, ImportRow.tenant_id == require_tenant()
        ))  # fmt: skip
        self.db.add_all(rows)

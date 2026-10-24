"""`idp` repositories — tenant-scoped reads of IDP business entities (R-DEC-21).

Only `idp` services use them (DEC-125). Non-tenant tables (jobs, assignments, catalogs) are
still queried directly by services; their access is reached through a tenant-scoped document.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, func, select

from app.core.base_repository import BaseRepository
from app.modules.idp.models import (
    DocumentAction,
    ExtractedField,
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
            .where(SourceDocument.sha256 == digest, SourceDocument.duplicate_of_id.is_(None))
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

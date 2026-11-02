"""`idp` repositories — tenant-scoped reads of IDP business entities (R-DEC-21).

Only `idp` services use them (DEC-125). Non-tenant tables (jobs, assignments, catalogs) are
still queried directly by services; their access is reached through a tenant-scoped document.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_repository import BaseRepository
from app.core.tenant import require_tenant
from app.modules.idp.models import (
    CaptureIncident,
    DocumentAction,
    DocumentPage,
    DocumentType,
    ExtractedField,
    ExtractionJob,
    ExtractionReview,
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

    async def by_storage_key(self, storage_key: str) -> SourceDocument | None:
        """EP-DC-14b: the document owning `storage_key` **within the current tenant** (R-DEC-80).

        Scoped by tenant so a signed URL from another tenant never resolves (defense in depth
        on top of the HMAC signature). A rolled-back document keeps its file; `_live()` filters
        soft-deleted rows only, so a committed/rolled-back source is still viewable."""
        stmt = self._live().where(SourceDocument.storage_key == storage_key)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def all_storage_keys(self) -> list[str]:
        """T-1011 — every `storage_key` this tenant references, soft-deleted rows included.

        A rolled-back or archived document keeps its file (it is still the lineage source), so
        the orphan sweep must treat those keys as referenced.
        """
        stmt = self._scoped(select(SourceDocument.storage_key)).where(
            SourceDocument.storage_key.is_not(None)
        )
        return [k for k in (await self.db.execute(stmt)).scalars().all() if k]

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

    async def critical_of_document(self, document_id: uuid.UUID) -> list[ExtractedField]:
        """Critical fields of the latest extraction job of a document (G4 undo incidents)."""
        job = (
            select(ExtractionJob.id).where(ExtractionJob.source_document_id == document_id)
            .order_by(ExtractionJob.attempt_no.desc()).limit(1).scalar_subquery()
        )  # fmt: skip
        stmt = (
            self._scoped(select(ExtractedField))
            .where(ExtractedField.extraction_job_id == job, ExtractedField.is_critical.is_(True))
            .order_by(ExtractedField.field_name, ExtractedField.row_index)
        )
        return list((await self.db.execute(stmt)).scalars())

    async def by_ids(self, ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, ExtractedField]:
        if not ids:
            return {}
        stmt = self._scoped(select(ExtractedField)).where(ExtractedField.id.in_(list(ids)))
        return {f.id: f for f in (await self.db.execute(stmt)).scalars()}


async def approvers_of(db: AsyncSession, document_id: uuid.UUID) -> set[uuid.UUID]:
    """Reviewers who approved this document (`ExtractionReview.decision = APPROVED`)."""
    stmt = select(ExtractionReview.reviewer_id).where(
        ExtractionReview.source_document_id == document_id,
        ExtractionReview.decision == "APPROVED",
    )
    return set((await db.execute(stmt)).scalars())


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


# A batch stops changing in these states; `open`/`processing` rows are still in use (T-1010).
FINAL_BATCH_STATES = ("completed", "partially_failed")


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
        await self.db.execute(delete(ImportRow).where(
            ImportRow.import_batch_id == batch_id, ImportRow.tenant_id == require_tenant()
        ))  # fmt: skip
        self.db.add_all(rows)

    async def batches_past_undo_window(self, now: datetime) -> list[uuid.UUID]:
        """T-1010 — finished batches whose document's undo window has closed (05 §2.7).

        `open`/`processing` batches are still in use; a batch with no `undo_deadline`, or one
        still inside it, keeps its rows so the user can review or undo the import.
        """
        stmt = (
            self._scoped(select(ImportBatch.id))
            .join(SourceDocument, SourceDocument.id == ImportBatch.source_document_id)
            .where(
                ImportBatch.status.in_(FINAL_BATCH_STATES),
                SourceDocument.undo_deadline.is_not(None),
                SourceDocument.undo_deadline < now,
            )
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def count_rows_of(self, batch_ids: Sequence[uuid.UUID]) -> int:
        """Number of `import_rows` belonging to any of `batch_ids` (tenant-scoped)."""
        if not batch_ids:
            return 0
        stmt = select(func.count()).select_from(ImportRow).where(
            ImportRow.import_batch_id.in_(batch_ids), ImportRow.tenant_id == require_tenant()
        )  # fmt: skip
        return int((await self.db.execute(stmt)).scalar_one())

    async def delete_rows_of(self, batch_ids: Sequence[uuid.UUID]) -> None:
        """Hard-delete the `import_rows` of `batch_ids` — `extracted_fields` are untouched."""
        if not batch_ids:
            return
        await self.db.execute(delete(ImportRow).where(
            ImportRow.import_batch_id.in_(batch_ids), ImportRow.tenant_id == require_tenant()
        ))  # fmt: skip


class IncidentRepository(BaseRepository[CaptureIncident]):
    """`idp.capture_incidents` — G4 wrong critical fields after commit (R-DEC-69)."""

    model = CaptureIncident

    async def page_where(
        self, where: Sequence[ColumnElement[bool]], *, limit: int, offset: int, desc: bool
    ) -> tuple[list[CaptureIncident], int]:
        base = self._live().where(*where)
        total = await self.db.execute(select(func.count()).select_from(base.subquery()))
        key = CaptureIncident.reported_at.desc() if desc else CaptureIncident.reported_at.asc()
        rows = await self.db.execute(base.order_by(key).limit(limit).offset(offset))
        return list(rows.scalars()), int(total.scalar_one())


class DocumentPageSearchRepository(BaseRepository[SourceDocument]):
    """Knowledge/RAG page search (M3.4, R-DEC-141) — tenant-scoped join DocumentPage→
    SourceDocument→DocumentType. Keeps the SQL in the repository layer (TC-M11-05); the service
    supplies the caller's visibility filter (EP-DC-13 `inbox_filter`) and the query vector."""

    model = SourceDocument

    def _base(self, scope: ColumnElement[bool] | None) -> Any:
        stmt = (
            select(
                DocumentPage.source_document_id,
                DocumentPage.page_number,
                DocumentPage.text_content,
                SourceDocument.original_filename,
                DocumentType.code,
            )
            .join(SourceDocument, SourceDocument.id == DocumentPage.source_document_id)
            .join(DocumentType, DocumentType.id == SourceDocument.document_type_id, isouter=True)
            .where(
                SourceDocument.deleted_at.is_(None), SourceDocument.tenant_id == require_tenant()
            )
        )
        return stmt.where(scope) if scope is not None else stmt

    async def keyword(
        self, scope: ColumnElement[bool] | None, pattern: str, *, limit: int, offset: int
    ) -> tuple[list[Any], int]:
        from sqlalchemy import literal

        stmt = (
            self._base(scope)
            .add_columns(literal(1.0).label("score"))
            .where(DocumentPage.text_content.ilike(pattern))
        )
        total = (
            await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        stmt = stmt.order_by(DocumentPage.source_document_id, DocumentPage.page_number)
        rows = (await self.db.execute(stmt.limit(limit).offset(offset))).all()
        return list(rows), int(total)

    async def semantic(
        self, scope: ColumnElement[bool] | None, vec: list[float], *, limit: int, offset: int
    ) -> tuple[list[Any], int]:
        distance = DocumentPage.embedding.op("<=>")(vec)  # pgvector cosine; smaller = closer
        stmt = (
            self._base(scope)
            .add_columns((1.0 - distance).label("score"))
            .where(DocumentPage.embedding.isnot(None))
        )
        total = (
            await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = (await self.db.execute(stmt.order_by(distance).limit(limit).offset(offset))).all()
        return list(rows), int(total)

"""EP-DC-13 Data Inbox (SCR-45) + EP-DC-14 "Xem tài liệu gốc" (10 §7.2.4).

Inbox rows = every capture document the caller may see (`scope.inbox_filter`) grouped by
status; `meta.counts` counts each group under the same filters except `group` itself.
Source view returns a 5-minute presigned GET of the stored original (`core.storage`).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import BadRequestError, BusinessRuleError, NotFoundError
from app.core.pagination import PageParams
from app.core.storage import PRESIGN_TTL_SECONDS, presign_get
from app.modules.idp.models import DocumentType, SourceDocument
from app.modules.idp.schemas.capture import InboxItemOut, SourceViewOut
from app.modules.idp.services.capture_common import can_undo, document_out
from app.modules.idp.services.scope import document_visible, inbox_filter, type_in_scope

GROUPS: dict[str, tuple[str, ...]] = {
    "processing": ("UPLOADED", "PREPROCESSING", "CLASSIFYING", "EXTRACTING", "VALIDATING"),
    "needs_review": ("NEEDS_REVIEW", "IN_REVIEW"),
    "approved": ("APPROVED",),
    "committed": ("AUTO_APPROVED", "COMMITTED"),
    "rejected": ("REJECTED",),
    "failed": ("FAILED", "DUPLICATE"),
    "rolled_back": ("ROLLED_BACK",),
}
CAPTURE_CHANNELS = ("C1", "C2", "C3", "C4", "C5")
_TOP_LEVEL = ("SPLIT", "SUPERSEDED")  # replaced by children / newer document → not listed


@dataclass
class InboxFilters:
    group: str | None = None
    channel: str | None = None
    document_type: str | None = None
    mine: bool = False
    q: str | None = None
    date_from: str | None = None
    date_to: str | None = None


def _day(value: str | None, param: str, *, end: bool) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value[:10])
    except ValueError as exc:
        raise BadRequestError("date must be YYYY-MM-DD", details={"param": param}) from exc
    return datetime.combine(parsed, time.max if end else time.min, tzinfo=UTC)


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class InboxService:
    def __init__(self, db: AsyncSession, store: Any = None) -> None:
        self.db = db
        self.store = store

    async def _where(self, user: Principal, f: InboxFilters) -> list[ColumnElement[bool]]:
        where: list[ColumnElement[bool]] = [
            SourceDocument.deleted_at.is_(None),
            SourceDocument.channel.in_(CAPTURE_CHANNELS),
            SourceDocument.status.not_in(_TOP_LEVEL),
        ]
        if (scope := await inbox_filter(self.db, user)) is not None:
            where.append(scope)
        if f.channel:
            where.append(SourceDocument.channel == f.channel)
        if f.document_type:
            sub = select(DocumentType.id).where(DocumentType.code == f.document_type)
            where.append(SourceDocument.document_type_id.in_(sub))
        if f.mine:
            where.append(SourceDocument.submitted_by == user.user_id)
        if f.q:
            pattern = f"%{_escape(f.q.strip())}%"
            where.append(SourceDocument.original_filename.ilike(pattern, escape="\\"))
        if (start := _day(f.date_from, "date_from", end=False)) is not None:
            where.append(SourceDocument.submitted_at >= start)
        if (end := _day(f.date_to, "date_to", end=True)) is not None:
            where.append(SourceDocument.submitted_at <= end)
        return where

    async def inbox(
        self, user: Principal, page: PageParams, f: InboxFilters
    ) -> tuple[list[InboxItemOut], int, dict[str, int]]:
        from app.modules.idp.repositories import SourceDocumentRepository

        where = await self._where(user, f)
        counts = await self._counts(where)
        if f.group:
            where.append(SourceDocument.status.in_(GROUPS[f.group]))
        col = (SourceDocument.committed_at if page.sort_by == "committed_at"
               else SourceDocument.submitted_at)  # fmt: skip
        order = col.asc().nulls_last() if page.order == "asc" else col.desc().nulls_last()
        docs, total = await SourceDocumentRepository(self.db).page(
            where, order, limit=page.limit, offset=page.offset
        )
        return await self._items(list(docs)), int(total), counts

    async def _counts(self, where: list[ColumnElement[bool]]) -> dict[str, int]:
        from app.modules.idp.repositories import SourceDocumentRepository

        by_status = await SourceDocumentRepository(self.db).status_counts(where)
        return {g: sum(by_status.get(s, 0) for s in sts) for g, sts in GROUPS.items()}

    async def _items(self, docs: list[SourceDocument]) -> list[InboxItemOut]:
        from app.modules.auth.services.auth_service import AuthService

        names = await AuthService(self.db).user_names([d.submitted_by for d in docs])
        type_ids = {d.document_type_id for d in docs if d.document_type_id}
        codes: dict[Any, str] = {}
        if type_ids:
            rows = await self.db.execute(
                select(DocumentType.id, DocumentType.code).where(DocumentType.id.in_(type_ids))
            )
            codes = {i: c for i, c in rows.all()}
        out: list[InboxItemOut] = []
        for d in docs:
            code = codes.get(d.document_type_id)
            out.append(InboxItemOut(
                document=document_out(d, code), document_type=code, channel=d.channel,
                submitted_by_name=names.get(d.submitted_by), record_count=d.row_count,
                undo_deadline=d.undo_deadline, can_undo=can_undo(d), batch_id=d.import_batch_id,
            ))  # fmt: skip
        return out

    # ------------------------------------------------------------- EP-DC-14
    async def source(
        self, user: Principal, document_id: uuid.UUID, page: int | None
    ) -> SourceViewOut:
        from app.modules.idp.repositories import SourceDocumentRepository

        doc = await SourceDocumentRepository(self.db).by_id(document_id)
        if doc is None or not await self._may_view(user, doc):
            raise NotFoundError("document not found")
        if doc.kind == "MANUAL" or not doc.storage_key:
            raise BusinessRuleError("document has no source file", details={"reason": "no_file"})
        pages = doc.page_count
        if page is not None and pages is not None and page > pages:
            raise BadRequestError("page out of range", details={"param": "page", "max": pages})
        if doc.sensitivity_level >= 3:
            await record_audit(
                self.db, action="idp.source_view", target_schema="idp",
                target_table="source_documents", target_id=doc.id,
                after={"page": page, "ttl_seconds": PRESIGN_TTL_SECONDS},
            )  # fmt: skip
        return SourceViewOut(url=presign_get(doc.storage_key), mime_type=doc.mime_type,
                             page_count=pages, page=page)  # fmt: skip

    async def _may_view(self, user: Principal, doc: SourceDocument) -> bool:
        """Same visibility as the inbox (scope row filter) + review/type scope."""
        if not await type_in_scope(self.db, user, doc):
            return False
        if document_visible(user, doc):
            return True
        scope = await inbox_filter(self.db, user)
        if scope is None:
            return True
        from app.modules.idp.repositories import SourceDocumentRepository

        return await SourceDocumentRepository(self.db).matches(doc.id, scope)

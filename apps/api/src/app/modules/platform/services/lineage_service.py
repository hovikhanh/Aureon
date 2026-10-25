"""ENT-DataLineage record links (FR-DATA-04, R-DEC-64) — public `platform` service.

Writers (the IDP commit) hand over `LineageLink`s; one `RECORD_FROM_FIELD` row per target column
written from an extracted field, pointing back to the page/sheet and row of the source document.
Undo sets `revoked_at` (rows are never deleted). Readers get plain DTOs — `platform` never
imports `idp`; the IDP side enriches them with document/page/field data and checks scope.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.platform.models import DataLineage
from app.modules.platform.repositories import LineageRepository

# R-DEC-64 whitelist: `<schema>.<table>` entities reachable through EP-DC-26.
LINEAGE_ENTITIES: frozenset[str] = frozenset({
    "hr.departments", "hr.teams", "hr.positions", "hr.employees", "execution.tasks",
    "execution.kpis", "execution.kpi_targets", "execution.kpi_measurements",
    "execution.objectives", "execution.key_results", "execution.check_ins", "finance.invoices",
})  # fmt: skip


@dataclass(frozen=True)
class LineageLink:
    target_schema: str
    target_table: str
    target_id: uuid.UUID
    target_column: str
    source_document_id: uuid.UUID
    extracted_field_id: uuid.UUID | None
    document_page_id: uuid.UUID | None
    document_action_id: uuid.UUID | None
    row_index: int | None
    action_name: str | None


@dataclass(frozen=True)
class LineageRow:
    target_column: str | None
    source_document_id: uuid.UUID | None
    extracted_field_id: uuid.UUID | None
    document_page_id: uuid.UUID | None
    row_index: int | None
    action_name: str | None
    created_at: datetime
    revoked_at: datetime | None


class LineageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = LineageRepository(db)

    @staticmethod
    async def record_many(db: AsyncSession, links: Sequence[LineageLink]) -> int:
        """Append one row per link inside the caller's transaction (no commit)."""
        db.add_all(
            DataLineage(
                link_kind="RECORD_FROM_FIELD", target_schema=lk.target_schema,
                target_table=lk.target_table, target_id=lk.target_id,
                target_column=lk.target_column, source_document_id=lk.source_document_id,
                extracted_field_id=lk.extracted_field_id, document_page_id=lk.document_page_id,
                document_action_id=lk.document_action_id, row_index=lk.row_index,
                action_name=lk.action_name,
            )
            for lk in links
        )  # fmt: skip
        await db.flush()
        return len(links)

    async def for_record(self, entity: str, record_id: uuid.UUID) -> list[LineageRow]:
        schema, table = entity.split(".", 1)
        rows = await self.repo.for_target(schema, table, record_id)
        return [
            LineageRow(r.target_column, r.source_document_id, r.extracted_field_id,
                       r.document_page_id, r.row_index, r.action_name, r.created_at,
                       r.revoked_at)
            for r in rows
        ]  # fmt: skip

    async def revoke(self, document_action_ids: Sequence[uuid.UUID]) -> int:
        """Undo (R-DEC-66): mark the links of reversed actions `revoked_at = now`."""
        return await self.repo.revoke_for_actions(document_action_ids, datetime.now(UTC))

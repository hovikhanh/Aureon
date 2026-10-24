"""G4 capture incidents (R-DEC-69) — EP-DC-36/37 + the automatic undo source.

An incident = a wrong field found after commit. `undetected=true` means review let it through
(reported post-commit or by an undo `critical_field_wrong`); G4 counts
`undetected AND is_critical` per period (target 0; the page is T-902, M1.5 only records + reads).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import NotFoundError, ValidationError
from app.core.pagination import PageParams
from app.core.periods import resolve_period
from app.modules.idp.models import CaptureIncident
from app.modules.idp.repositories import (
    ExtractedFieldRepository,
    IncidentRepository,
    SourceDocumentRepository,
)
from app.modules.idp.schemas.capture import IncidentCreate, IncidentOut
from app.modules.idp.services.critical import CRITICAL_FIELD_NAMES
from app.modules.idp.services.scope import document_visible, lineage_visible


class IncidentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncidentRepository(db)

    async def report(self, user: Principal, body: IncidentCreate) -> IncidentOut:
        """EP-DC-36 — reviewer/DIR reports a wrong value found after commit."""
        doc = await SourceDocumentRepository(self.db).by_id(body.source_document_id)
        if doc is None or not (document_visible(user, doc)
                               or await lineage_visible(self.db, user, doc)):  # fmt: skip
            raise NotFoundError("document not found")
        critical = body.field_name in CRITICAL_FIELD_NAMES
        if body.extracted_field_id is not None:
            f = await ExtractedFieldRepository(self.db).get(body.extracted_field_id)
            if f is None or f.field_name != body.field_name:
                raise ValidationError("field does not match document",
                                      details={"fields": ["extracted_field_id"]})  # fmt: skip
            critical = critical or f.is_critical
        inc = await self.record(
            doc.id, body.extracted_field_id, body.field_name, critical=critical,
            detected_by="post_commit", target_table=body.target_table,
            target_id=body.target_id, description=body.description, user=user,
        )  # fmt: skip
        await record_audit(
            self.db, action="idp.incident_report", target_schema="idp",
            target_table="capture_incidents", target_id=inc.id,
            after={"source_document_id": str(doc.id), "field_name": inc.field_name,
                   "is_critical": inc.is_critical, "detected_by": inc.detected_by},
        )  # fmt: skip
        return IncidentOut.model_validate(inc)

    async def record(
        self, document_id: uuid.UUID, field_id: uuid.UUID | None, field_name: str, *,
        critical: bool, detected_by: str, description: str, user: Principal,
        target_table: str | None = None, target_id: uuid.UUID | None = None,
    ) -> CaptureIncident:  # fmt: skip
        inc = CaptureIncident(
            source_document_id=document_id, extracted_field_id=field_id, field_name=field_name,
            is_critical=critical, detected_by=detected_by, undetected=detected_by != "review",
            target_table=target_table, target_id=target_id, description=description,
            reported_by=user.user_id, reported_at=datetime.now(UTC), source="MANUAL",
        )  # fmt: skip
        self.db.add(inc)
        await self.db.flush()
        return inc

    async def list(
        self, page: PageParams, *, period: str | None, undetected_only: bool
    ) -> tuple[list[IncidentOut], int]:
        """EP-DC-37 — `period` (10 §1.5 values) on `reported_at`; G4 view = undetected_only."""
        where: list[ColumnElement[bool]] = []
        if period is not None:
            try:
                p = resolve_period(period, datetime.now(UTC).date())
            except ValueError as exc:
                raise ValidationError(str(exc), details={"fields": ["period"]}) from exc
            start = datetime.combine(p.start, time.min, UTC)
            end = datetime.combine(p.end, time.max, UTC)
            where += [CaptureIncident.reported_at >= start, CaptureIncident.reported_at <= end]
        if undetected_only:
            where.append(CaptureIncident.undetected.is_(True))
        rows, total = await self.repo.page_where(
            where, limit=page.limit, offset=page.offset, desc=page.order != "asc")  # fmt: skip
        return [IncidentOut.model_validate(r) for r in rows], total

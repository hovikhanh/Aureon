"""IDP commit via the Action Registry (04 §10; 10 EP-31). On approve, the extracted fields are
written into the owning domain module through its **public service** (DEC-125) in the caller's
transaction, so the domain row + `ENT-SourceDocument.status=COMMITTED` + audit + the
`idp.document_committed` event commit together (04 §10.4).

v2.0 wires the reference commit path: `INVOICE → finance.Invoice`. Other doc types without a
mapped domain entity (`OTHER`, meeting minutes, …) are marked `COMMITTED` with no domain row
(the SOP/knowledge metadata path, 04 §6) — `actions` is empty. The full catalogue (sales
report → deals, employee list → hr, risk register → risks) lands in S4c.

Reversible: each `ACT-*` records `result_refs`; the 7-day undo (EP-33) is S4c and rolls the
domain row back through the same public service.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import ActionRejectedError, ConflictStateError, NotFoundError
from app.modules.idp.models import (
    DocumentType,
    ExtractedField,
    ExtractionJob,
    ExtractionReview,
    SourceDocument,
)
from app.modules.idp.repositories import ExtractedFieldRepository, SourceDocumentRepository
from app.modules.idp.schemas import ActionRefOut, ApproveOut, DocumentOut
from app.modules.idp.services.scope import document_visible

UNDO_DAYS = 7
_DEFAULT_PAYMENT_TERM_DAYS = 30

EVT_COMMITTED = "idp.document_committed"


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


@dataclass
class _CommitResult:
    actions: list[ActionRefOut] = field(default_factory=list)


class CommitService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def approve(
        self,
        user: Principal,
        document_id: uuid.UUID,
        *,
        comment: str | None = None,
        expected_version: int | None = None,
    ) -> ApproveOut:
        """EP-31 — approve the review and commit to the domain via the Action Registry."""
        doc = await self._doc(document_id)
        if not self._visible(user, doc):
            raise NotFoundError("document not found")
        if doc.status not in ("NEEDS_REVIEW", "IN_REVIEW", "AUTO_APPROVED"):
            raise ConflictStateError(
                f"cannot approve a {doc.status} document", details={"status": doc.status}
            )
        if (
            doc.locked_by is not None
            and doc.locked_by != user.user_id
            and doc.locked_until is not None
            and _aware(doc.locked_until) > _now()
        ):
            from app.core.errors import ReviewLockedError

            raise ReviewLockedError(
                "document locked by another reviewer",
                details={"locked_by": str(doc.locked_by)},
            )
        if expected_version is not None and doc.version != expected_version:
            raise ConflictStateError(
                f"document was modified (version {doc.version}, expected {expected_version})",
                details={"version": doc.version},
            )

        job = await self._latest_job(document_id)
        fields = await self._fields(job.id) if job else []
        type_code = await self._doc_type_code(doc.document_type_id)

        doc.status = "APPROVED"
        await self.db.flush()

        result = await self._commit_to_domain(user, doc, type_code, fields)

        doc.status = "COMMITTED"
        doc.committed_at = _now()
        doc.undo_deadline = _now() + timedelta(days=UNDO_DAYS)
        doc.locked_by = None
        doc.locked_until = None
        if job is not None:
            self.db.add(
                ExtractionReview(
                    source_document_id=doc.id,
                    extraction_job_id=job.id,
                    reviewer_id=user.user_id,
                    reviewer_role=user.role,
                    decision="APPROVED",
                    reject_note=comment,
                    fields_total=len(fields),
                    fields_corrected=sum(1 for f in fields if f.corrected_by is not None),
                    opened_at=_now(),
                    decided_at=_now(),
                )
            )
        await self._deactivate_assignments(doc.id)
        await self.db.flush()

        await record_audit(
            self.db,
            action="idp.document.committed",
            target_schema="idp",
            target_table="source_documents",
            target_id=doc.id,
            after={
                "status": "COMMITTED",
                "actions": [a.action_name for a in result.actions],
            },
            why=comment,
        )
        await self._emit_committed(doc, type_code, result.actions)
        return ApproveOut(
            document=DocumentOut.model_validate(doc),
            actions=result.actions,
            undo_deadline=doc.undo_deadline,
        )

    # ---------------------------------------------------- domain dispatch
    async def _commit_to_domain(
        self,
        user: Principal,
        doc: SourceDocument,
        type_code: str | None,
        fields: list[ExtractedField],
    ) -> _CommitResult:
        if type_code == "INVOICE":
            return await self._commit_invoice(user, doc, fields)
        # No domain mapping for this doc type in v2.0 → metadata-only commit (04 §6 knowledge).
        return _CommitResult()

    async def _commit_invoice(
        self, user: Principal, doc: SourceDocument, fields: list[ExtractedField]
    ) -> _CommitResult:
        """ACT-create_invoice → finance.Invoice via the finance public service (DEC-125)."""
        from app.modules.finance.schemas import InvoiceCreate, InvoiceLineIn
        from app.modules.finance.services.invoice_service import InvoiceService

        v = {f.field_name: _effective(f) for f in fields}
        number = _as_str(v.get("invoice_number")) or f"IDP-{doc.id.hex[:8]}"
        issued = _as_date(v.get("issue_date")) or date.today()
        subtotal = _as_int(v.get("subtotal"))
        vat_amount = _as_int(v.get("vat_amount"))
        vat_pct = _as_vat(v.get("vat_rate_pct"))
        if subtotal <= 0:
            raise ActionRejectedError(
                "invoice subtotal must be positive to commit",
                details={"action_name": "ACT-create_invoice", "reason": "subtotal<=0"},
            )
        unit_price = subtotal  # one aggregate line; detailed line items land in S4c
        body = InvoiceCreate(
            direction="IN",  # a received supplier invoice (IDP ingest, 04 UC-08)
            counterparty_name=_as_str(v.get("seller_name")),
            counterparty_tax_code=_as_str(v.get("seller_tax_code")),
            number=number,
            issued_on=issued,
            due_date=issued + timedelta(days=_DEFAULT_PAYMENT_TERM_DAYS),
            status="sent",
            lines=[
                InvoiceLineIn(
                    description=f"IDP invoice {number}",
                    quantity=1,
                    unit_price=unit_price,
                    vat_pct=vat_pct,
                )
            ],
            notes=f"Committed from IDP document {doc.id}",
        )
        try:
            out = await InvoiceService(self.db).create(user, body)
        except Exception as exc:  # business-rule / duplicate → ACTION_REJECTED (04 §10, IDP-E11)
            from app.core.errors import AppError

            reason = exc.code if isinstance(exc, AppError) else type(exc).__name__
            raise ActionRejectedError(
                "finance rejected the invoice commit",
                details={"action_name": "ACT-create_invoice", "reason": reason},
            ) from exc
        # vat_amount is recomputed by finance from pct; keep the extracted value for lineage.
        _ = vat_amount
        return _CommitResult(
            actions=[
                ActionRefOut(
                    action_name="ACT-create_invoice",
                    ids=[str(out.id)],
                    table="finance.invoices",
                )
            ]
        )

    # ------------------------------------------------------------- event
    async def _emit_committed(
        self, doc: SourceDocument, type_code: str | None, actions: list[ActionRefOut]
    ) -> None:
        from app.core.events.outbox import publish_in_tx

        await publish_in_tx(
            self.db,
            event_type=EVT_COMMITTED,
            producer="idp",
            aggregate_schema="idp",
            aggregate_table="source_documents",
            aggregate_id=doc.id,
            payload={
                "document_id": str(doc.id),
                "document_type": type_code,
                "actions": [
                    {"action_name": a.action_name, "ids": a.ids, "table": a.table} for a in actions
                ],
            },
        )

    # ----------------------------------------------------------- helpers
    async def _doc(self, document_id: uuid.UUID) -> SourceDocument:
        doc = await SourceDocumentRepository(self.db).by_id(document_id)
        if doc is None:
            raise NotFoundError("document not found")
        return doc

    async def _latest_job(self, document_id: uuid.UUID) -> ExtractionJob | None:
        return (
            (
                await self.db.execute(
                    select(ExtractionJob)
                    .where(ExtractionJob.source_document_id == document_id)
                    .order_by(ExtractionJob.attempt_no.desc())
                )
            )
            .scalars()
            .first()
        )

    async def _fields(self, job_id: uuid.UUID) -> list[ExtractedField]:
        return await ExtractedFieldRepository(self.db).for_job(job_id)

    async def _doc_type_code(self, dt_id: uuid.UUID | None) -> str | None:
        if dt_id is None:
            return None
        return (
            await self.db.execute(select(DocumentType.code).where(DocumentType.id == dt_id))
        ).scalar_one_or_none()

    async def _deactivate_assignments(self, document_id: uuid.UUID) -> None:
        from app.modules.idp.models import ReviewAssignment

        current = (
            await self.db.execute(
                select(ReviewAssignment).where(
                    ReviewAssignment.source_document_id == document_id,
                    ReviewAssignment.is_current.is_(True),
                )
            )
        ).scalar_one_or_none()
        if current is not None:
            current.is_current = False

    @staticmethod
    def _visible(user: Principal, doc: SourceDocument) -> bool:
        return document_visible(user, doc)


def _effective(field_: ExtractedField) -> Any:
    if field_.corrected_by is not None:
        return field_.corrected_value
    return field_.value


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None


def _as_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip().replace(" ", "")
    # VN grouping: "1.234.567" → 1234567 ; "1,234,567" → 1234567
    s = s.replace(".", "").replace(",", "")
    try:
        return int(s)
    except ValueError:
        return 0


def _as_vat(value: Any) -> int:
    pct = _as_int(value)
    return pct if pct in (0, 5, 8, 10) else 10


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None

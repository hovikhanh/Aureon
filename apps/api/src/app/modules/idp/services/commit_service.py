"""IDP commit through the Action Registry v2 (04 §10; 10 §7.2.4 EP-DC-08/23; R-DEC-60/61/63).

Approve (EP-DC-08): the reviewed fields are mapped onto the published schema's `action_names`
(`actions.executor.build_plan`). Caller holds every ACT `required_permission` → all ACTs run in one
SAVEPOINT of the request transaction (target rows + their audit/outbox + `idp.document_actions`
+ `COMMITTED` + `idp.document_committed` commit together). Caller lacks ≥ 1 → `APPROVED` with
`pending_permissions` (no write); a holder commits it later via EP-DC-23 (`commit`).
Doc types without actions (OTHER, …) commit metadata-only (`actions=[]`).
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import (
    ConflictStateError,
    NotFoundError,
    PermissionDeniedError,
    ReviewLockedError,
)
from app.modules.idp.models import (
    DocumentType,
    ExtractedField,
    ExtractionJob,
    ExtractionReview,
    ExtractionSchema,
    SourceDocument,
)
from app.modules.idp.repositories import ExtractedFieldRepository, SourceDocumentRepository
from app.modules.idp.schemas import ActionRefOut, ApproveOut, DocumentOut
from app.modules.idp.services.actions import ActionContext
from app.modules.idp.services.actions.executor import (
    Step,
    build_plan,
    missing_permissions,
    run_all,
)
from app.modules.idp.services.scope import document_visible

UNDO_DAYS = 7
EVT_COMMITTED = "idp.document_committed"
_APPROVABLE = ("NEEDS_REVIEW", "IN_REVIEW", "AUTO_APPROVED")
_SOURCE_BY_CHANNEL = {"C1": "MANUAL", "C5": "IMPORT"}  # else IDP (10 §7.2.4 `ctx.source`)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


@dataclass
class ApproveResult:
    out: ApproveOut
    pending_permissions: list[str] = field(default_factory=list)


@dataclass
class _Loaded:
    job: ExtractionJob | None
    fields: list[ExtractedField]
    type_code: str | None
    steps: list[Step]


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
    ) -> ApproveResult:
        """EP-DC-08 — approve the review; commit now if the caller may run every ACT."""
        doc = await self._guarded(user, document_id, _APPROVABLE, expected_version)
        if (
            doc.locked_by is not None
            and doc.locked_by != user.user_id
            and doc.locked_until is not None
            and _aware(doc.locked_until) > _now()
        ):
            raise ReviewLockedError(
                "document locked by another reviewer", details={"locked_by": str(doc.locked_by)}
            )
        loaded = await self._load(doc)
        stp = doc.status == "AUTO_APPROVED"
        self._add_review(doc, loaded, user, comment)
        doc.status = "APPROVED"
        doc.locked_by = None
        doc.locked_until = None
        await self._deactivate_assignments(doc.id)
        await self.db.flush()
        pending = missing_permissions(user, loaded.steps)
        if pending:  # R-DEC-61: approval ≠ write permission → wait for EP-DC-23
            await record_audit(
                self.db, action="idp.document_approve", target_schema="idp",
                target_table="source_documents", target_id=doc.id,
                after={"status": "APPROVED", "pending_permissions": pending}, why=comment,
            )  # fmt: skip
            out = ApproveOut(document=DocumentOut.model_validate(doc), actions=[],
                             undo_deadline=None)  # fmt: skip
            return ApproveResult(out, pending)
        return ApproveResult(await self._commit(user, doc, loaded, comment, stp=stp))

    async def commit(
        self, user: Principal, document_id: uuid.UUID, *, expected_version: int
    ) -> ApproveOut:
        """EP-DC-23 — commit an `APPROVED` document (step 2, caller holds the target perms)."""
        doc = await self._guarded(user, document_id, ("APPROVED",), expected_version)
        loaded = await self._load(doc)
        missing = missing_permissions(user, loaded.steps)
        if missing:
            raise PermissionDeniedError("missing target permission", details={"missing": missing})
        return await self._commit(user, doc, loaded, None, stp=False)

    async def planned(self, user: Principal, doc: SourceDocument) -> list[Step]:
        """ACT plan of a document (EP-DC-05 `planned_actions`, no write)."""
        return (await self._load(doc)).steps

    # ---------------------------------------------------- commit
    async def _commit(
        self,
        user: Principal,
        doc: SourceDocument,
        loaded: _Loaded,
        comment: str | None,
        *,
        stp: bool,
    ) -> ApproveOut:
        ctx = ActionContext(source=_SOURCE_BY_CHANNEL.get(doc.channel, "IDP"),
                            source_document_id=doc.id)  # fmt: skip
        done = await run_all(self.db, user, loaded.steps, ctx)
        refs: dict[tuple[str, str], list[str]] = {}
        for step, outcome in done:
            for r in outcome.result_refs:
                refs.setdefault((step.act.name, f"{r['schema']}.{r['table']}"), []).append(r["id"])
        actions = [ActionRefOut(action_name=a, table=t, ids=ids) for (a, t), ids in refs.items()]
        now = _now()
        doc.status = "COMMITTED"
        doc.committed_at = now
        doc.committed_by = user.user_id
        doc.undo_deadline = now + timedelta(days=UNDO_DAYS)
        doc.locked_by = None
        doc.locked_until = None
        if loaded.steps:
            doc.row_count = len({s.row_index for s in loaded.steps if s.row_index is not None})
        await self.db.flush()
        await record_audit(
            self.db, action="idp.document.committed", target_schema="idp",
            target_table="source_documents", target_id=doc.id,
            after={"status": "COMMITTED", "actions": [a.action_name for a in actions],
                   "warnings": sorted(set(ctx.warnings))},
            why=comment,
        )  # fmt: skip
        await self._emit_committed(doc, loaded, done, user, stp=stp)
        return ApproveOut(document=DocumentOut.model_validate(doc), actions=actions,
                          undo_deadline=doc.undo_deadline)  # fmt: skip

    async def _emit_committed(
        self, doc: SourceDocument, loaded: _Loaded, done: list[Any], user: Principal, *,
        stp: bool,
    ) -> None:  # fmt: skip
        """10 §9.2 v1 payload (R-DEC-67): no PII — counts, tables, ids only; `tenant_id` rides
        on the outbox envelope."""
        from app.core.events.outbox import publish_in_tx

        counts = Counter(step.act.name for step, _ in done)
        tables = sorted({f"{r['schema']}.{r['table']}" for _, o in done for r in o.result_refs})
        await publish_in_tx(
            self.db, event_type=EVT_COMMITTED, producer="idp", aggregate_schema="idp",
            aggregate_table="source_documents", aggregate_id=doc.id,
            payload={
                "document_id": str(doc.id), "document_type": loaded.type_code,
                "channel": doc.channel, "kind": doc.kind, "row_count": doc.row_count or 0,
                "actions": [{"action_name": a, "count": n} for a, n in counts.items()],
                "target_tables": tables, "committed_by": str(user.user_id), "stp": stp,
                "critical_field_count": sum(1 for f in loaded.fields if f.is_critical),
            },
        )  # fmt: skip

    # ----------------------------------------------------------- helpers
    async def _guarded(
        self, user: Principal, document_id: uuid.UUID, states: tuple[str, ...],
        expected_version: int | None,
    ) -> SourceDocument:  # fmt: skip
        doc = await self._doc(document_id)
        if not document_visible(user, doc):
            raise NotFoundError("document not found")
        if doc.status not in states:
            raise ConflictStateError(f"cannot commit a {doc.status} document",
                                     details={"status": doc.status})  # fmt: skip
        if expected_version is not None and doc.version != expected_version:
            raise ConflictStateError(
                f"document was modified (version {doc.version}, expected {expected_version})",
                details={"version": doc.version},
            )
        return doc

    async def _load(self, doc: SourceDocument) -> _Loaded:
        job = await self._latest_job(doc.id)
        fields = await ExtractedFieldRepository(self.db).for_job(job.id) if job else []
        type_code = await self._doc_type_code(doc.document_type_id)
        schema = await self._schema(job.extraction_schema_id) if job else None
        names = list(schema.action_names) if schema is not None else []
        if not names and type_code == "INVOICE":  # v2.1 catalog row predates `action_names`
            names = ["ACT-create_invoice"]
        values = [(f.field_name, f.row_index, _effective(f)) for f in fields]
        steps = build_plan(names, list(schema.fields) if schema is not None else [], values)
        return _Loaded(job, fields, type_code, steps)

    def _add_review(
        self, doc: SourceDocument, loaded: _Loaded, user: Principal, comment: str | None
    ) -> None:
        if loaded.job is None:
            return
        self.db.add(ExtractionReview(
            source_document_id=doc.id, extraction_job_id=loaded.job.id,
            reviewer_id=user.user_id, reviewer_role=user.role, decision="APPROVED",
            reject_note=comment, fields_total=len(loaded.fields),
            fields_corrected=sum(1 for f in loaded.fields if f.corrected_by is not None),
            opened_at=_now(), decided_at=_now(),
        ))  # fmt: skip

    async def _doc(self, document_id: uuid.UUID) -> SourceDocument:
        doc = await SourceDocumentRepository(self.db).by_id(document_id)
        if doc is None:
            raise NotFoundError("document not found")
        return doc

    async def _latest_job(self, document_id: uuid.UUID) -> ExtractionJob | None:
        stmt = (
            select(ExtractionJob)
            .where(ExtractionJob.source_document_id == document_id)
            .order_by(ExtractionJob.attempt_no.desc())
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def _schema(self, schema_id: uuid.UUID) -> ExtractionSchema | None:
        stmt = select(ExtractionSchema).where(ExtractionSchema.id == schema_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _doc_type_code(self, dt_id: uuid.UUID | None) -> str | None:
        if dt_id is None:
            return None
        stmt = select(DocumentType.code).where(DocumentType.id == dt_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _deactivate_assignments(self, document_id: uuid.UUID) -> None:
        from app.modules.idp.models import ReviewAssignment

        stmt = select(ReviewAssignment).where(
            ReviewAssignment.source_document_id == document_id,
            ReviewAssignment.is_current.is_(True),
        )
        current = (await self.db.execute(stmt)).scalar_one_or_none()
        if current is not None:
            current.is_current = False


def _effective(field_: ExtractedField) -> Any:
    if field_.corrected_by is not None:
        return field_.corrected_value
    return field_.value

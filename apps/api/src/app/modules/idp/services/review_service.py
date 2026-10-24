"""IDP review workflow service (04 §8, §12.1; 10 EP-28..35, EP-126/127).

Covers the human-review side of the pipeline, operating on documents the pipeline left in
`NEEDS_REVIEW`:

* `queue`            EP-28 — paginated, filterable Data Inbox, department-scoped (04 §8.2).
* `detail`          EP-25/30 — document + pages + fields (effective value) + validation + assign.
* `open` / `release` EP-29/35 — soft lock (15 min) acquire / drop.
* `patch_fields`    EP-30 — confirm/correct/clear fields, optional doc-type change, recompute
                     validation; `reason` required for money fields (FR-DC-05).
* `reject`          EP-32 — `REJECTED` with a mandatory reason, `ENT-ExtractionReview` row.
* `reassign`        EP-126 — `ACT-reassign_review`, keeps SLA, notifies the new reviewer.
* `merge`           EP-127 — `ACT-merge_review`, child docs nested under one parent review.

Approve + commit (EP-31) lives in `commit_service.py`; SLA escalation (EP-412 beat job) in
`sla_service.py`. All mutations write `ENT-AuditLog` in the caller's transaction; the route
commits once at the end (CLAUDE.md §5.4).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import (
    ConflictStateError,
    NotFoundError,
    ReviewLockedError,
    ValidationError,
)
from app.core.field_policy import STRUCTURE_ONLY_ROLES
from app.core.pagination import PageParams
from app.modules.idp.models import (
    DocumentPage,
    DocumentType,
    ExtractedField,
    ExtractionJob,
    ExtractionReview,
    ReviewAssignment,
    SourceDocument,
    ValidationRule,
)
from app.modules.idp.repositories import ExtractedFieldRepository, SourceDocumentRepository
from app.modules.idp.schemas import (
    DocumentOut,
    DocumentPageOut,
    FieldPatchIn,
    FieldPatchOut,
    ReassignOut,
    ReviewAssignmentOut,
    ReviewDetailOut,
    ReviewFieldOut,
    ReviewOpenOut,
    ReviewQueueItemOut,
)
from app.modules.idp.services.scope import (
    document_visible,
    sees_all_departments,
    structure_type_ids,
    type_in_scope,
)
from app.modules.idp.services.validator import Validator

SOFT_LOCK_MINUTES = 15
_MONEY_TYPES = frozenset({"money"})


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class QueueFilters:
    status: str | None = None
    document_type: str | None = None
    assigned_to: uuid.UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class ReviewService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------ queue
    async def queue(
        self, user: Principal, page: PageParams, filters: QueueFilters
    ) -> tuple[list[ReviewQueueItemOut], int]:
        """EP-28 — review queue. Default status set = documents awaiting a human
        (`NEEDS_REVIEW`, `IN_REVIEW`). Department-scoped per 04 §8.2 unless the caller has
        `idp:admin` or no department (CEO/ADMIN-style)."""
        where: list[ColumnElement[bool]] = []
        if filters.status:
            where.append(SourceDocument.status == filters.status)
        else:
            where.append(SourceDocument.status.in_(("NEEDS_REVIEW", "IN_REVIEW")))
        if filters.date_from:
            where.append(SourceDocument.submitted_at >= filters.date_from)
        if filters.date_to:
            where.append(SourceDocument.submitted_at <= filters.date_to)
        if filters.document_type:
            dt_id = await self._doc_type_id(filters.document_type)
            where.append(SourceDocument.document_type_id == dt_id)
        if user.role in STRUCTURE_ONLY_ROLES:  # R-DEC-76 scope `s`: only #4 HR_ROSTER
            where.append(SourceDocument.document_type_id.in_(await structure_type_ids(self.db)))
        if not sees_all_departments(user):
            where.append(
                (SourceDocument.department_id == user.department_id)
                | (SourceDocument.submitted_by == user.user_id)
            )
        if filters.assigned_to is not None:
            sub = select(ReviewAssignment.source_document_id).where(
                ReviewAssignment.is_current.is_(True),
                ReviewAssignment.to_user_id == filters.assigned_to,
            )
            where.append(SourceDocument.id.in_(sub))

        sort_col = {
            "created_at": SourceDocument.submitted_at,
            "submitted_at": SourceDocument.submitted_at,
        }.get(page.sort_by, SourceDocument.submitted_at)
        order = sort_col.asc() if page.order == "asc" else sort_col.desc()
        docs, total = await SourceDocumentRepository(self.db).page(
            where, order, limit=page.limit, offset=page.offset
        )
        items = [await self._queue_item(d) for d in docs]
        return items, int(total)

    async def _queue_item(self, doc: SourceDocument) -> ReviewQueueItemOut:
        job = await self._latest_job(doc.id)
        fields: list[ExtractedField] = []
        if job is not None:
            fields = await ExtractedFieldRepository(self.db).for_job(job.id)
        confs = [float(f.confidence) for f in fields]
        avg = round(sum(confs) / len(confs), 4) if confs else None
        critical = sum(1 for f in fields if f.is_critical)
        verrs = (job.xd_results or {}).get("validation_errors", []) if job else []
        assignment = await self._current_assignment(doc.id)
        age_hours = round((_now() - _aware(doc.submitted_at)).total_seconds() / 3600, 2)
        return ReviewQueueItemOut(
            document_id=doc.id,
            filename=doc.original_filename,
            document_type=await self._doc_type_code(doc.document_type_id),
            status=doc.status,
            confidence_avg=avg,
            critical_fields_count=critical,
            validation_error_count=len(verrs),
            routing_reason=doc.routing_reason,
            age_hours=age_hours,
            assigned_to=assignment.to_user_id if assignment else None,
            due_at=assignment.due_at if assignment else None,
            locked_by=doc.locked_by,
            locked_until=doc.locked_until,
        )

    # ----------------------------------------------------------------- detail
    async def detail(self, user: Principal, document_id: uuid.UUID) -> ReviewDetailOut:
        doc = await self._visible_doc(user, document_id)
        job = await self._latest_job(document_id)
        pages = (
            (
                await self.db.execute(
                    select(DocumentPage)
                    .where(DocumentPage.source_document_id == document_id)
                    .order_by(DocumentPage.page_number.asc())
                )
            )
            .scalars()
            .all()
        )
        fields = await self._fields(job.id) if job else []
        xd = (job.xd_results or {}) if job else {}
        assignment = await self._current_assignment(document_id)
        return ReviewDetailOut(
            document=DocumentOut.model_validate(doc),
            job_id=job.id if job else None,
            pages=[DocumentPageOut.model_validate(p) for p in pages],
            fields=[_field_out(f) for f in fields],
            validation_errors=list(xd.get("validation_errors", [])),
            document_confidence=float(job.document_confidence)
            if job and job.document_confidence
            else None,
            routing_decision=job.routing_decision if job else None,
            routing_reasons=list(job.routing_reasons or []) if job else [],
            assigned_to=assignment.to_user_id if assignment else None,
            locked_by=doc.locked_by,
            locked_until=doc.locked_until,
        )

    # ------------------------------------------------------------ open/release
    async def open(self, user: Principal, document_id: uuid.UUID) -> ReviewOpenOut:
        """EP-29 — acquire the 15-min soft lock and mark `IN_REVIEW`."""
        doc = await self._visible_doc(user, document_id)
        if doc.status not in ("NEEDS_REVIEW", "IN_REVIEW"):
            raise ConflictStateError(f"document is {doc.status}", details={"status": doc.status})
        self._check_lock(doc, user)
        doc.locked_by = user.user_id
        doc.locked_until = _now() + timedelta(minutes=SOFT_LOCK_MINUTES)
        doc.status = "IN_REVIEW"
        await self.db.flush()
        await record_audit(
            self.db,
            action="idp.review.open",
            target_schema="idp",
            target_table="source_documents",
            target_id=doc.id,
            after={"locked_until": doc.locked_until.isoformat()},
        )
        return ReviewOpenOut(
            locked_until=doc.locked_until, document=DocumentOut.model_validate(doc)
        )

    async def release(self, user: Principal, document_id: uuid.UUID) -> None:
        """EP-35 — drop the lock without saving; return to `NEEDS_REVIEW`."""
        doc = await self._visible_doc(user, document_id)
        self._check_lock(doc, user)
        doc.locked_by = None
        doc.locked_until = None
        if doc.status == "IN_REVIEW":
            doc.status = "NEEDS_REVIEW"
        await self.db.flush()
        await record_audit(
            self.db,
            action="idp.review.release",
            target_schema="idp",
            target_table="source_documents",
            target_id=doc.id,
        )

    # ------------------------------------------------------- field correction
    async def patch_fields(
        self, user: Principal, document_id: uuid.UUID, body: FieldPatchIn
    ) -> FieldPatchOut:
        """EP-30 — confirm/correct/clear fields, recompute validation. A money field edit
        requires `reason` (FR-DC-05). Holds (or renews) the caller's soft lock."""
        doc = await self._visible_doc(user, document_id)
        self._require_lock(doc, user)
        doc.locked_until = _now() + timedelta(minutes=SOFT_LOCK_MINUTES)
        job = await self._latest_job(document_id)
        if job is None:
            raise NotFoundError("no extraction job to review")
        fields = await self._fields(job.id)
        by_id = {f.id: f for f in fields}

        if body.accept_all_high:
            for f in fields:
                if f.confidence_band == "HIGH" and not f.is_critical and f.corrected_by is None:
                    # confirm = accept the AI value → persist it as the effective (corrected) value
                    f.corrected_value = f.value
                    f.corrected_by = user.user_id
                    f.corrected_at = _now()

        for edit in body.fields:
            field = by_id.get(edit.field_id)
            if field is None:
                raise NotFoundError(f"field {edit.field_id} not on this document")
            if edit.action == "confirm":
                field.corrected_value = field.value  # accepted AI value stays effective
                field.corrected_by = user.user_id
                field.corrected_at = _now()
                continue
            new_value = None if edit.action == "clear" else edit.value
            if field.value_type in _MONEY_TYPES and not (edit.reason and edit.reason.strip()):
                raise ValidationError(
                    "reason is required when correcting a financial field (FR-DC-05)",
                    details={"fields": [{"field": field.field_name, "reason": "required"}]},
                )
            field.corrected_value = new_value
            field.corrected_by = user.user_id
            field.corrected_at = _now()
            field.correction_reason = edit.reason

        await self.db.flush()
        validation = await self._recompute(job, fields)
        # persist per-field validation + job-level errors
        for f in fields:
            f.validation = validation.for_field(f.field_name)
        job.xd_results = {
            **(job.xd_results or {}),
            "validation_errors": validation.errors,
        }
        await self.db.flush()
        await record_audit(
            self.db,
            action="idp.field.corrected",
            target_schema="idp",
            target_table="extracted_fields",
            target_id=doc.id,
            after={
                "corrections": len(body.fields),
                "accept_all_high": body.accept_all_high,
                "validations_ok": validation.ok,
            },
            why=next((e.reason for e in body.fields if e.reason), None),
        )
        return FieldPatchOut(
            fields=[_field_out(f) for f in fields],
            validation_errors=validation.errors,
            validations_ok=validation.ok,
        )

    # -------------------------------------------------------------- reject
    async def reject(self, user: Principal, document_id: uuid.UUID, reason: str) -> DocumentOut:
        """EP-32 — reject with a mandatory reason; `ENT-ExtractionReview` row; emit event."""
        doc = await self._visible_doc(user, document_id)
        if doc.status not in ("NEEDS_REVIEW", "IN_REVIEW"):
            raise ConflictStateError(
                f"cannot reject a {doc.status} document", details={"status": doc.status}
            )
        self._require_lock(doc, user, allow_unlocked=True)
        job = await self._latest_job(document_id)
        fields = await self._fields(job.id) if job else []
        opened = (
            _aware(doc.locked_until) - timedelta(minutes=SOFT_LOCK_MINUTES)
            if doc.locked_until
            else _now()
        )
        self.db.add(
            ExtractionReview(
                source_document_id=doc.id,
                extraction_job_id=job.id if job else uuid.uuid4(),
                reviewer_id=user.user_id,
                reviewer_role=user.role,
                decision="REJECTED",
                reject_reason_code="MANUAL",
                reject_note=reason,
                fields_total=len(fields),
                fields_corrected=sum(1 for f in fields if f.corrected_by is not None),
                opened_at=opened,
                decided_at=_now(),
            )
        )
        doc.status = "REJECTED"
        doc.status_reason = reason
        doc.locked_by = None
        doc.locked_until = None
        await self._deactivate_assignments(doc.id)
        await self.db.flush()
        await record_audit(
            self.db,
            action="idp.review.reject",
            target_schema="idp",
            target_table="source_documents",
            target_id=doc.id,
            after={"status": "REJECTED"},
            why=reason,
        )
        return DocumentOut.model_validate(doc)

    # ------------------------------------------------------------ reassign
    async def reassign(
        self,
        user: Principal,
        document_id: uuid.UUID,
        *,
        to_user_id: uuid.UUID | None,
        to_role_code: str | None,
        reason: str,
    ) -> ReassignOut:
        """EP-126 / `ACT-reassign_review` — hand review to another reviewer, keep SLA."""
        doc = await self._visible_doc(user, document_id)
        if doc.status not in ("NEEDS_REVIEW", "IN_REVIEW"):
            raise ConflictStateError(
                f"cannot reassign a {doc.status} document", details={"status": doc.status}
            )
        if not reason.strip():
            raise ValidationError("reason is required", details={"field": "reason"})
        if (to_user_id is None) == (to_role_code is None):
            raise ValidationError(
                "exactly one of to_user_id / to_role_code is required",
                details={"fields": ["to_user_id", "to_role_code"]},
            )
        # Someone else holds the soft lock → cannot steal the review (409 REVIEW_LOCKED).
        if (
            doc.locked_by is not None
            and doc.locked_by != user.user_id
            and doc.locked_until is not None
            and _aware(doc.locked_until) > _now()
        ):
            raise ReviewLockedError(
                "document locked by another reviewer",
                details={"locked_by": str(doc.locked_by)},
            )
        current = await self._current_assignment(doc.id)
        due_at = current.due_at if current else _now() + timedelta(hours=24)
        await self._deactivate_assignments(doc.id)
        assignment = ReviewAssignment(
            source_document_id=doc.id,
            kind="REASSIGN",
            from_user_id=current.to_user_id if current else user.user_id,
            to_user_id=to_user_id,
            to_role_code=to_role_code,
            reason=reason,
            due_at=due_at,
            is_current=True,
        )
        self.db.add(assignment)
        # Reassigning drops any existing lock so the new reviewer can open.
        doc.locked_by = None
        doc.locked_until = None
        if doc.status == "IN_REVIEW":
            doc.status = "NEEDS_REVIEW"
        await self.db.flush()
        if to_user_id is not None:
            await self._notify(
                to_user_id,
                kind="review_assigned",
                title="Tài liệu được chuyển cho bạn duyệt",
                body=reason,
                ref_id=doc.id,
            )
        await record_audit(
            self.db,
            action="idp.review.reassign",
            target_schema="idp",
            target_table="review_assignments",
            target_id=assignment.id,
            after={
                "to_user_id": str(to_user_id) if to_user_id else None,
                "to_role_code": to_role_code,
            },
            why=reason,
        )
        return ReassignOut(
            document=DocumentOut.model_validate(doc),
            assignment=ReviewAssignmentOut.model_validate(assignment),
        )

    # --------------------------------------------------------------- merge
    async def merge(
        self,
        user: Principal,
        document_ids: list[uuid.UUID],
        primary_id: uuid.UUID | None,
    ) -> tuple[DocumentOut, list[DocumentOut]]:
        """EP-127 / `ACT-merge_review` — nest 2..20 docs of one doc type/batch under one parent.
        Reverse of a split (EP-37). All must be `NEEDS_REVIEW`."""
        docs: list[SourceDocument] = []
        for did in document_ids:
            docs.append(await self._visible_doc(user, did))
        if len({d.status for d in docs} - {"NEEDS_REVIEW", "IN_REVIEW"}):
            raise ConflictStateError(
                "all documents must be in review",
                details={"statuses": sorted({d.status for d in docs})},
            )
        types = {d.document_type_id for d in docs}
        if len(types) > 1:
            raise ConflictStateError(
                "documents must share one document type",
                details={"document_type_ids": [str(t) for t in types if t]},
            )
        parent_id = primary_id or document_ids[0]
        parent = next((d for d in docs if d.id == parent_id), None)
        if parent is None:
            raise ValidationError(
                "primary_id must be one of document_ids", details={"field": "primary_id"}
            )
        children = [d for d in docs if d.id != parent.id]
        for child in children:
            child.parent_id = parent.id
            child.status = "NEEDS_REVIEW"
            child.locked_by = None
            child.locked_until = None
            await self._deactivate_assignments(child.id)
        await self.db.flush()
        await record_audit(
            self.db,
            action="idp.review.merge",
            target_schema="idp",
            target_table="source_documents",
            target_id=parent.id,
            after={"children": [str(c.id) for c in children]},
        )
        return (
            DocumentOut.model_validate(parent),
            [DocumentOut.model_validate(c) for c in children],
        )

    # ------------------------------------------------------------- helpers
    async def _recompute(self, job: ExtractionJob, fields: list[ExtractedField]) -> Any:
        rules = await self._rules(job.extraction_schema_id)
        required = await self._required_fields(job.extraction_schema_id)
        values = {f.field_name: _effective(f) for f in fields}
        return Validator(rules).validate(values, required=required)

    async def _rules(self, schema_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = (
            (
                await self.db.execute(
                    select(ValidationRule).where(
                        ValidationRule.extraction_schema_id == schema_id,
                        ValidationRule.is_active.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
        return [
            {"code": r.code, "kind": r.kind, "expression": r.expression, "severity": r.severity}
            for r in rows
        ]

    async def _required_fields(self, schema_id: uuid.UUID) -> set[str]:
        from app.modules.idp.models import ExtractionSchema

        schema = (
            await self.db.execute(select(ExtractionSchema).where(ExtractionSchema.id == schema_id))
        ).scalar_one()
        return {f["name"] for f in (schema.fields or []) if f.get("required")}

    async def _fields(self, job_id: uuid.UUID) -> list[ExtractedField]:
        return await ExtractedFieldRepository(self.db).for_job(job_id, ordered=True)

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

    async def _current_assignment(self, document_id: uuid.UUID) -> ReviewAssignment | None:
        return (
            await self.db.execute(
                select(ReviewAssignment).where(
                    ReviewAssignment.source_document_id == document_id,
                    ReviewAssignment.is_current.is_(True),
                )
            )
        ).scalar_one_or_none()

    async def _deactivate_assignments(self, document_id: uuid.UUID) -> None:
        current = await self._current_assignment(document_id)
        if current is not None:
            current.is_current = False
            await self.db.flush()

    async def _doc_type_id(self, code: str) -> uuid.UUID | None:
        return (
            await self.db.execute(select(DocumentType.id).where(DocumentType.code == code))
        ).scalar_one_or_none()

    async def _doc_type_code(self, dt_id: uuid.UUID | None) -> str | None:
        if dt_id is None:
            return None
        return (
            await self.db.execute(select(DocumentType.code).where(DocumentType.id == dt_id))
        ).scalar_one_or_none()

    async def _visible_doc(self, user: Principal, document_id: uuid.UUID) -> SourceDocument:
        doc = await SourceDocumentRepository(self.db).by_id(document_id)
        if (
            doc is None
            or not self._visible(user, doc)
            or not await type_in_scope(self.db, user, doc)
        ):
            raise NotFoundError("document not found")
        return doc

    @staticmethod
    def _visible(user: Principal, doc: SourceDocument) -> bool:
        return document_visible(user, doc)

    @staticmethod
    def _check_lock(doc: SourceDocument, user: Principal) -> None:
        """Raise REVIEW_LOCKED if another user holds a live lock."""
        if (
            doc.locked_by is not None
            and doc.locked_by != user.user_id
            and doc.locked_until is not None
            and _aware(doc.locked_until) > _now()
        ):
            raise ReviewLockedError(
                "document locked by another reviewer",
                details={
                    "locked_by": str(doc.locked_by),
                    "locked_until": _aware(doc.locked_until).isoformat(),
                },
            )

    @staticmethod
    def _require_lock(
        doc: SourceDocument, user: Principal, *, allow_unlocked: bool = False
    ) -> None:
        """The caller must hold a live lock to mutate (EP-30). `allow_unlocked` lets reject
        proceed when no one holds the lock (direct reject from the queue)."""
        held_by_self = (
            doc.locked_by == user.user_id
            and doc.locked_until is not None
            and _aware(doc.locked_until) > _now()
        )
        if held_by_self:
            return
        if (
            doc.locked_by is not None
            and doc.locked_by != user.user_id
            and doc.locked_until is not None
            and _aware(doc.locked_until) > _now()
        ):
            raise ReviewLockedError(
                "document locked by another reviewer",
                details={"locked_by": str(doc.locked_by)},
            )
        if not allow_unlocked:
            raise ReviewLockedError(
                "open the review first (EP-29) to acquire the soft lock",
                details={"required": "open"},
            )

    async def _notify(
        self,
        recipient_id: uuid.UUID,
        *,
        kind: str,
        title: str,
        body: str,
        ref_id: uuid.UUID,
    ) -> None:
        """Create an in-app notification via the platform public service (DEC-125)."""
        from app.modules.platform.services.notification_service import NotificationService

        await NotificationService(self.db).create(
            recipient_id=recipient_id,
            kind=kind,
            title=title,
            body=body,
            ref_schema="idp",
            ref_table="source_documents",
            ref_id=ref_id,
        )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _effective(field: ExtractedField) -> Any:
    """Corrected value wins once a reviewer touched it; else the AI value."""
    if field.corrected_by is not None:
        return field.corrected_value
    return field.value


def _field_out(field: ExtractedField) -> ReviewFieldOut:
    return ReviewFieldOut(
        id=field.id,
        field_name=field.field_name,
        row_index=field.row_index,
        value_type=field.value_type,
        ai_value=field.value,
        corrected_value=field.corrected_value,
        effective_value=_effective(field),
        confidence=float(field.confidence),
        confidence_band=field.confidence_band,
        is_critical=field.is_critical,
        is_confirmed=field.corrected_by is not None,
        source_location=field.source_location,
        validation=list(field.validation or []),
        correction_reason=field.correction_reason,
    )

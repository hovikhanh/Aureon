"""S4b review workflow at the service layer (T-406..T-412).

Covers queue (EP-28), detail, open/release (EP-29/35), field correction (EP-30), approve +
commit to finance.Invoice (EP-31), reject (EP-32), reassign (EP-126), merge (EP-127) and the
SLA escalation beat job (T-412). Each test drives a real document through the pipeline to
`NEEDS_REVIEW`, then exercises the review services on the rolled-back `db_session`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import pytest
from sqlalchemy import select

from app.core.deps import Principal
from app.core.model_gateway import ChatResponse
from app.core.pagination import PageParams
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.idp.models import ExtractedField, ReviewAssignment, SourceDocument
from app.modules.idp.schemas import FieldCorrectionIn, FieldPatchIn
from app.modules.idp.services.commit_service import CommitService
from app.modules.idp.services.pipeline import Pipeline
from app.modules.idp.services.review_service import QueueFilters, ReviewService
from app.modules.idp.services.sla_service import SlaService
from app.modules.idp.services.upload_service import UploadFile, UploadService
from tests.integration.idp import sample_docs as s

pytestmark = pytest.mark.integration


def _reviewer(dept: uuid.UUID | None = None, uid: uuid.UUID | None = None) -> Principal:
    return Principal(
        user_id=uid or uuid.uuid4(),
        role="REVIEWER",
        permissions=frozenset(ROLE_PERMISSIONS["REVIEWER"]),
        department_id=dept,
    )


def _file(name: str, mime: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, content_type=mime, chunks=iter([data]))


class _InvoiceGateway:
    DATA: ClassVar[dict[str, Any]] = {
        "invoice_number": {"value": "0001234", "raw_text": "0001234", "confidence": 0.98},
        "issue_date": {"value": "2026-09-15", "confidence": 0.95},
        "seller_name": {"value": "Cong ty ABC", "confidence": 0.93},
        "seller_tax_code": {"value": "0301234567", "confidence": 0.92},
        "subtotal": {"value": 10000000, "confidence": 0.96},
        "vat_rate_pct": {"value": 10, "confidence": 0.95},
        "vat_amount": {"value": 1000000, "confidence": 0.95},
        "total_amount": {"value": 11000000, "confidence": 0.96},
    }

    async def chat(self, req: Any) -> ChatResponse:
        return ChatResponse(content="", provider="fake", model="m", data=self.DATA)


async def _ingest_invoice(db, user: Principal) -> uuid.UUID:
    """Upload + run the pipeline → a document in NEEDS_REVIEW; returns its id."""
    r = await UploadService(db).upload(
        user, [_file("invoice.pdf", "application/pdf", s.invoice_pdf())]
    )
    doc_id = r.document_ids[0]
    outcome = await Pipeline(db, _InvoiceGateway()).run(doc_id)
    assert outcome.status == "NEEDS_REVIEW"  # critical fields force review
    return doc_id


# --------------------------------------------------------------- T-406 queue
async def test_queue_returns_needs_review_documents(db_session, idp_store) -> None:
    user = _reviewer()
    ids = [await _ingest_invoice(db_session, user) for _ in range(3)]
    items, total = await ReviewService(db_session).queue(
        user, PageParams(limit=20, offset=0), QueueFilters()
    )
    assert total == 3
    assert {i.document_id for i in items} == set(ids)
    first = items[0]
    assert first.status == "NEEDS_REVIEW"
    assert first.critical_fields_count == 3  # subtotal, vat_amount, total_amount
    assert first.confidence_avg is not None
    assert first.age_hours >= 0
    assert first.due_at is not None  # pipeline created the ASSIGN row with an SLA clock


async def test_queue_filter_by_document_type(db_session, idp_store) -> None:
    user = _reviewer()
    await _ingest_invoice(db_session, user)
    inv, _ = await ReviewService(db_session).queue(
        user, PageParams(), QueueFilters(document_type="INVOICE")
    )
    assert len(inv) == 1
    _other, total = await ReviewService(db_session).queue(
        user, PageParams(), QueueFilters(document_type="CONTRACT")
    )
    assert total == 0


async def test_queue_department_scoping(db_session, idp_store) -> None:
    dept_a, dept_b = uuid.uuid4(), uuid.uuid4()
    owner_a = _reviewer(dept=dept_a)
    await _ingest_invoice(db_session, owner_a)
    # a reviewer in another department sees nothing
    _, total_b = await ReviewService(db_session).queue(
        _reviewer(dept=dept_b), PageParams(), QueueFilters()
    )
    assert total_b == 0
    # admin / no-department sees it
    admin = Principal(
        user_id=uuid.uuid4(), role="ADMIN",
        permissions=frozenset(ROLE_PERMISSIONS["ADMIN"]), department_id=None,
    )  # fmt: skip
    _, total_admin = await ReviewService(db_session).queue(admin, PageParams(), QueueFilters())
    assert total_admin == 1


# -------------------------------------------------------------- T-407 detail
async def test_detail_shows_fields_validation_lineage(db_session, idp_store) -> None:
    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    detail = await ReviewService(db_session).detail(user, doc_id)
    assert len(detail.fields) == 8
    critical = [f for f in detail.fields if f.is_critical]
    assert {f.field_name for f in critical} == {"subtotal", "vat_amount", "total_amount"}
    # every field carries lineage (source_location with page)
    for f in detail.fields:
        assert "page" in f.source_location or "kind" in f.source_location
    assert detail.pages  # document pages present
    assert detail.routing_decision == "REVIEW"


# --------------------------------------------------- T-408 field correction
async def test_open_then_correct_field_recomputes_validation(db_session, idp_store) -> None:
    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    svc = ReviewService(db_session)
    await svc.open(user, doc_id)
    field = await _field(db_session, doc_id, "seller_name")
    out = await svc.patch_fields(
        user,
        doc_id,
        FieldPatchIn(
            fields=[
                FieldCorrectionIn(field_id=field.id, action="correct", value="Cong ty ABC (sua)")
            ]
        ),
    )
    assert out.validations_ok is True
    edited = next(f for f in out.fields if f.field_name == "seller_name")
    assert edited.effective_value == "Cong ty ABC (sua)"
    assert edited.is_confirmed is True


async def test_correct_financial_field_requires_reason(db_session, idp_store) -> None:
    from app.core.errors import ValidationError

    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    svc = ReviewService(db_session)
    await svc.open(user, doc_id)
    money = await _field(db_session, doc_id, "total_amount")
    with pytest.raises(ValidationError):
        await svc.patch_fields(
            user,
            doc_id,
            FieldPatchIn(fields=[FieldCorrectionIn(field_id=money.id, value=12000000)]),
        )
    # with a reason it succeeds
    out = await svc.patch_fields(
        user,
        doc_id,
        FieldPatchIn(
            fields=[FieldCorrectionIn(field_id=money.id, value=12000000, reason="OCR mismatch")]
        ),
    )
    edited = next(f for f in out.fields if f.field_name == "total_amount")
    assert edited.effective_value == 12000000
    assert edited.correction_reason == "OCR mismatch"


async def test_patch_without_lock_is_rejected(db_session, idp_store) -> None:
    from app.core.errors import ReviewLockedError

    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    field = await _field(db_session, doc_id, "seller_name")
    with pytest.raises(ReviewLockedError):
        await ReviewService(db_session).patch_fields(
            user,
            doc_id,
            FieldPatchIn(fields=[FieldCorrectionIn(field_id=field.id, value="x")]),
        )


async def test_lock_blocks_other_reviewer(db_session, idp_store) -> None:
    from app.core.errors import ReviewLockedError

    owner = _reviewer()
    doc_id = await _ingest_invoice(db_session, owner)
    await ReviewService(db_session).open(owner, doc_id)
    other = _reviewer()
    with pytest.raises(ReviewLockedError):
        await ReviewService(db_session).open(other, doc_id)


# ------------------------------------------------ T-409 approve / reject
async def test_approve_commits_finance_invoice(db_session, idp_store) -> None:
    from app.modules.finance.models import Invoice

    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    await ReviewService(db_session).open(user, doc_id)
    out = await CommitService(db_session).approve(user, doc_id, comment="looks good")
    assert out.document.status == "COMMITTED"
    assert out.undo_deadline is not None
    assert len(out.actions) == 1
    assert out.actions[0].action_name == "ACT-create_invoice"
    inv_id = uuid.UUID(out.actions[0].ids[0])
    inv = (await db_session.execute(select(Invoice).where(Invoice.id == inv_id))).scalar_one()
    assert inv.number == "0001234"
    assert inv.subtotal == 10000000
    assert inv.vat_rate_pct == 10
    # event emitted
    assert await _has_outbox(db_session, "idp.document_committed", doc_id)


async def test_approve_uses_corrected_value(db_session, idp_store) -> None:
    from app.modules.finance.models import Invoice

    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    svc = ReviewService(db_session)
    await svc.open(user, doc_id)
    num = await _field(db_session, doc_id, "invoice_number")
    await svc.patch_fields(
        user,
        doc_id,
        FieldPatchIn(fields=[FieldCorrectionIn(field_id=num.id, value="0009999")]),
    )
    out = await CommitService(db_session).approve(user, doc_id)
    inv = (
        await db_session.execute(
            select(Invoice).where(Invoice.id == uuid.UUID(out.actions[0].ids[0]))
        )
    ).scalar_one()
    assert inv.number == "0009999"


async def test_reject_marks_document_rejected(db_session, idp_store) -> None:
    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    out = await ReviewService(db_session).reject(user, doc_id, "blurry scan, cannot verify")
    assert out.status == "REJECTED"
    doc = (
        await db_session.execute(select(SourceDocument).where(SourceDocument.id == doc_id))
    ).scalar_one()
    assert doc.status == "REJECTED"
    assert doc.status_reason == "blurry scan, cannot verify"


# --------------------------------------------------------- T-410 reassign
async def test_reassign_moves_assignment(db_session, idp_store) -> None:
    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    target = uuid.uuid4()
    out = await ReviewService(db_session).reassign(
        user, doc_id, to_user_id=target, to_role_code=None, reason="OOO"
    )
    assert out.assignment.to_user_id == target
    assert out.assignment.kind == "REASSIGN"
    # exactly one current assignment, pointing at the new reviewer
    rows = (
        (
            await db_session.execute(
                select(ReviewAssignment).where(
                    ReviewAssignment.source_document_id == doc_id,
                    ReviewAssignment.is_current.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].to_user_id == target
    # the new reviewer's queue now sees the document
    items, _ = await ReviewService(db_session).queue(
        user, PageParams(), QueueFilters(assigned_to=target)
    )
    assert [i.document_id for i in items] == [doc_id]


async def test_reassign_requires_reason(db_session, idp_store) -> None:
    from app.core.errors import ValidationError

    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    with pytest.raises(ValidationError):
        await ReviewService(db_session).reassign(
            user, doc_id, to_user_id=uuid.uuid4(), to_role_code=None, reason="   "
        )


# ------------------------------------------------------------ T-411 merge
async def test_merge_nests_children_under_parent(db_session, idp_store) -> None:
    user = _reviewer()
    a = await _ingest_invoice(db_session, user)
    b = await _ingest_invoice(db_session, user)
    parent, children = await ReviewService(db_session).merge(user, [a, b], primary_id=a)
    assert parent.id == a
    assert [c.id for c in children] == [b]
    child = (
        await db_session.execute(select(SourceDocument).where(SourceDocument.id == b))
    ).scalar_one()
    assert child.parent_id == a


async def test_merge_rejects_mixed_types(db_session, idp_store) -> None:
    from app.core.errors import ConflictStateError

    user = _reviewer()
    inv = await _ingest_invoice(db_session, user)
    # an OTHER document (contract docx classifies as OTHER)
    r = await UploadService(db_session).upload(
        user, [_file("contract.docx", "application/octet-stream", s.contract_docx())]
    )
    await Pipeline(db_session, _InvoiceGateway()).run(r.document_ids[0])
    with pytest.raises(ConflictStateError):
        await ReviewService(db_session).merge(user, [inv, r.document_ids[0]], primary_id=inv)


# ------------------------------------------------------ T-412 SLA escalation
async def test_sla_escalation_emits_event(db_session, idp_store) -> None:
    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    # backdate the assignment's due_at to 25h ago → overdue
    current = (
        await db_session.execute(
            select(ReviewAssignment).where(
                ReviewAssignment.source_document_id == doc_id,
                ReviewAssignment.is_current.is_(True),
            )
        )
    ).scalar_one()
    current.due_at = datetime.now(UTC) - timedelta(hours=25)
    await db_session.flush()

    escalated = await SlaService(db_session).check_review_sla()
    assert doc_id in escalated
    assert await _has_outbox(db_session, "idp.review_escalated", doc_id)
    # a new ESCALATE assignment is current
    esc = (
        await db_session.execute(
            select(ReviewAssignment).where(
                ReviewAssignment.source_document_id == doc_id,
                ReviewAssignment.is_current.is_(True),
            )
        )
    ).scalar_one()
    assert esc.kind == "ESCALATE"


async def test_sla_idempotent_second_run(db_session, idp_store) -> None:
    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    current = (
        await db_session.execute(
            select(ReviewAssignment).where(
                ReviewAssignment.source_document_id == doc_id,
                ReviewAssignment.is_current.is_(True),
            )
        )
    ).scalar_one()
    current.due_at = datetime.now(UTC) - timedelta(hours=25)
    await db_session.flush()
    svc = SlaService(db_session)
    first = await svc.check_review_sla()
    second = await svc.check_review_sla()
    assert doc_id in first
    assert doc_id not in second  # already at DEPT_HEAD level → no re-escalation


# -------------------------------------------------- extra coverage paths
async def _ingest_other(db, user: Principal) -> uuid.UUID:
    r = await UploadService(db).upload(
        user, [_file("contract.docx", "application/octet-stream", s.contract_docx())]
    )
    await Pipeline(db, _InvoiceGateway()).run(r.document_ids[0])
    return r.document_ids[0]


async def test_approve_other_doctype_is_metadata_only(db_session, idp_store) -> None:
    """A doc type without a domain mapping (OTHER) commits with no domain row (04 §6)."""
    user = _reviewer()
    doc_id = await _ingest_other(db_session, user)
    doc = (
        await db_session.execute(select(SourceDocument).where(SourceDocument.id == doc_id))
    ).scalar_one()
    if doc.status == "AUTO_APPROVED":  # OTHER may route either way; force a review state
        doc.status = "NEEDS_REVIEW"
        await db_session.flush()
    out = await CommitService(db_session).approve(user, doc_id)
    assert out.document.status == "COMMITTED"
    assert out.actions == []


async def test_approve_version_conflict(db_session, idp_store) -> None:
    from app.core.errors import ConflictStateError

    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    with pytest.raises(ConflictStateError):
        await CommitService(db_session).approve(user, doc_id, expected_version=999)


async def test_approve_blocked_by_other_lock(db_session, idp_store) -> None:
    from app.core.errors import ReviewLockedError

    owner = _reviewer()
    doc_id = await _ingest_invoice(db_session, owner)
    await ReviewService(db_session).open(owner, doc_id)
    other = _reviewer()
    with pytest.raises(ReviewLockedError):
        await CommitService(db_session).approve(other, doc_id)


async def test_approve_wrong_state_conflict(db_session, idp_store) -> None:
    from app.core.errors import ConflictStateError

    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    await ReviewService(db_session).reject(user, doc_id, "nope")
    with pytest.raises(ConflictStateError):
        await CommitService(db_session).approve(user, doc_id)


async def test_commit_invoice_duplicate_number_rejected(db_session, idp_store) -> None:
    """A finance business-rule failure surfaces as ACTION_REJECTED (04 §10, IDP-E11)."""
    from app.core.errors import ActionRejectedError

    user = _reviewer()
    a = await _ingest_invoice(db_session, user)
    await CommitService(db_session).approve(user, a)  # first commit wins the number UQ
    b = await _ingest_invoice(db_session, user)  # same fixture → same invoice_number
    with pytest.raises(ActionRejectedError):
        await CommitService(db_session).approve(user, b)
    doc_b = (
        await db_session.execute(select(SourceDocument).where(SourceDocument.id == b))
    ).scalar_one()
    assert doc_b.status == "APPROVED"  # not committed; commit raised before COMMITTED


async def test_release_returns_to_needs_review(db_session, idp_store) -> None:
    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    svc = ReviewService(db_session)
    await svc.open(user, doc_id)
    await svc.release(user, doc_id)
    doc = (
        await db_session.execute(select(SourceDocument).where(SourceDocument.id == doc_id))
    ).scalar_one()
    assert doc.status == "NEEDS_REVIEW"
    assert doc.locked_by is None


async def test_accept_all_high_confirms_non_critical(db_session, idp_store) -> None:
    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    svc = ReviewService(db_session)
    await svc.open(user, doc_id)
    out = await svc.patch_fields(user, doc_id, FieldPatchIn(accept_all_high=True))
    confirmed = {f.field_name for f in out.fields if f.is_confirmed}
    assert "invoice_number" in confirmed
    assert "subtotal" not in confirmed  # critical


async def test_confirm_action_marks_field(db_session, idp_store) -> None:
    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    svc = ReviewService(db_session)
    await svc.open(user, doc_id)
    f = await _field(db_session, doc_id, "seller_tax_code")
    out = await svc.patch_fields(
        user, doc_id, FieldPatchIn(fields=[FieldCorrectionIn(field_id=f.id, action="confirm")])
    )
    edited = next(x for x in out.fields if x.field_name == "seller_tax_code")
    assert edited.is_confirmed is True
    assert edited.effective_value == edited.ai_value  # confirm keeps the AI value


async def test_reassign_to_role(db_session, idp_store) -> None:
    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    out = await ReviewService(db_session).reassign(
        user, doc_id, to_user_id=None, to_role_code="MANAGER", reason="escalate manually"
    )
    assert out.assignment.to_role_code == "MANAGER"


async def test_reassign_requires_exactly_one_target(db_session, idp_store) -> None:
    from app.core.errors import ValidationError

    user = _reviewer()
    doc_id = await _ingest_invoice(db_session, user)
    with pytest.raises(ValidationError):
        await ReviewService(db_session).reassign(
            user, doc_id, to_user_id=uuid.uuid4(), to_role_code="MANAGER", reason="both"
        )


async def test_merge_bad_primary_id(db_session, idp_store) -> None:
    from app.core.errors import ValidationError

    user = _reviewer()
    a = await _ingest_invoice(db_session, user)
    b = await _ingest_invoice(db_session, user)
    with pytest.raises(ValidationError):
        await ReviewService(db_session).merge(user, [a, b], primary_id=uuid.uuid4())


async def test_commit_parse_helpers() -> None:
    from datetime import date

    from app.modules.idp.services.commit_service import _as_date, _as_int, _as_str, _as_vat

    assert _as_int("1.234.567") == 1234567
    assert _as_int("1,234,567") == 1234567
    assert _as_int(None) == 0
    assert _as_int("abc") == 0
    assert _as_int(True) == 0
    assert _as_vat(8) == 8
    assert _as_vat(13) == 10  # not an allowed rate → default 10
    assert _as_str("  x  ") == "x"
    assert _as_str(None) is None
    assert _as_date("15/09/2026") == date(2026, 9, 15)
    assert _as_date("2026-09-15") == date(2026, 9, 15)
    assert _as_date("bad") is None
    assert _as_date(date(2026, 1, 1)) == date(2026, 1, 1)


async def test_detail_not_found(db_session, idp_store) -> None:
    from app.core.errors import NotFoundError

    with pytest.raises(NotFoundError):
        await ReviewService(db_session).detail(_reviewer(), uuid.uuid4())


# --------------------------------------------------------------- helpers
async def _field(db, doc_id: uuid.UUID, name: str) -> ExtractedField:
    from app.modules.idp.models import ExtractionJob

    job = (
        (
            await db.execute(
                select(ExtractionJob)
                .where(ExtractionJob.source_document_id == doc_id)
                .order_by(ExtractionJob.attempt_no.desc())
            )
        )
        .scalars()
        .first()
    )
    return (
        await db.execute(
            select(ExtractedField).where(
                ExtractedField.extraction_job_id == job.id,
                ExtractedField.field_name == name,
            )
        )
    ).scalar_one()


async def _has_outbox(db, event_type: str, aggregate_id: uuid.UUID) -> bool:
    from app.modules.platform.models import OutboxEvent

    rows = (
        (
            await db.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_type == event_type,
                    OutboxEvent.aggregate_id == aggregate_id,
                )
            )
        )
        .scalars()
        .all()
    )
    return len(rows) >= 1

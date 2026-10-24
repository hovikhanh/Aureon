"""T-636 — commit through the Action Registry v2: APPROVED + pending permissions (R-DEC-61),
EP-DC-23 commit, `idp.document_actions` rows (R-DEC-63), `idp.document_committed` v1 payload
(TC-M15-11: tenant on the envelope, no PII)."""

import json
import uuid

import pytest
from sqlalchemy import select

from app.core.deps import Principal
from app.core.errors import ConflictStateError, PermissionDeniedError
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.idp.models import DocumentAction, SourceDocument
from app.modules.idp.services.commit_service import CommitService
from app.modules.idp.services.review_service import ReviewService
from tests.integration.idp.test_review_workflow import _ingest_invoice

pytestmark = pytest.mark.integration


def _p(role: str, pillars: tuple[str, ...] = ()) -> Principal:
    return Principal(user_id=uuid.uuid4(), role=role, scope_pillars=pillars,
                     permissions=frozenset(ROLE_PERMISSIONS[role]))  # fmt: skip


async def _approved(db) -> tuple[uuid.UUID, int]:
    rev = _p("REV")
    doc_id = await _ingest_invoice(db, rev)
    await ReviewService(db).open(rev, doc_id)
    res = await CommitService(db).approve(rev, doc_id)
    assert res.out.document.status == "APPROVED"
    assert res.out.actions == [] and res.pending_permissions == ["finance:write"]
    assert res.out.document.version >= 1  # R-DEC-60bis
    doc = (await db.execute(select(SourceDocument).where(SourceDocument.id == doc_id))).scalar_one()
    return doc_id, doc.version


async def test_reviewer_without_target_permission_leaves_approved(db_session, idp_store) -> None:
    doc_id, _ = await _approved(db_session)
    rows = (await db_session.execute(select(DocumentAction).where(
        DocumentAction.source_document_id == doc_id))).scalars().all()  # fmt: skip
    assert rows == []


async def test_commit_ep_dc_23_writes_actions_and_event(db_session, idp_store) -> None:
    from app.modules.platform.models import OutboxEvent

    doc_id, version = await _approved(db_session)
    cfo = _p("DIR", ("F",))
    out = await CommitService(db_session).commit(cfo, doc_id, expected_version=version)
    assert out.document.status == "COMMITTED" and out.undo_deadline is not None
    assert out.actions[0].table == "finance.invoices"
    rows = (await db_session.execute(select(DocumentAction).where(
        DocumentAction.source_document_id == doc_id))).scalars().all()  # fmt: skip
    assert [(r.seq, r.action_name, r.status) for r in rows] == [
        (1, "ACT-create_invoice", "applied")
    ]
    assert rows[0].result_refs[0]["schema"] == "finance"
    ev = (await db_session.execute(select(OutboxEvent).where(
        OutboxEvent.event_type == "idp.document_committed",
        OutboxEvent.aggregate_id == doc_id))).scalar_one()  # fmt: skip
    assert ev.tenant_id is not None
    p = ev.payload
    assert set(p) == {"document_id", "document_type", "channel", "kind", "row_count", "actions",
                      "target_tables", "committed_by", "stp", "critical_field_count"}  # fmt: skip
    assert p["actions"] == [{"action_name": "ACT-create_invoice", "count": 1}]
    assert p["target_tables"] == ["finance.invoices"] and p["stp"] is False
    blob = json.dumps(p)
    assert "Cong ty ABC" not in blob and "0301234567" not in blob  # no seller name / MST


async def test_commit_requires_target_permission_and_state(db_session, idp_store) -> None:
    doc_id, version = await _approved(db_session)
    with pytest.raises(PermissionDeniedError) as exc:
        await CommitService(db_session).commit(_p("REV"), doc_id, expected_version=version)
    assert exc.value.details["missing"] == ["finance:write"]
    cfo = _p("DIR", ("F",))
    with pytest.raises(ConflictStateError):  # stale version
        await CommitService(db_session).commit(cfo, doc_id, expected_version=version + 5)
    await CommitService(db_session).commit(cfo, doc_id, expected_version=version)
    with pytest.raises(ConflictStateError):  # COMMITTED ≠ APPROVED
        await CommitService(db_session).commit(cfo, doc_id, expected_version=None)  # type: ignore[arg-type]

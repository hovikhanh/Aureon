"""EP-DC-24/25 — undo a committed document within 7 days (DEC-134, R-DEC-66).

Guard order: visible → state `COMMITTED` (409) → deadline (410) → caller is submitter /
approver / committer or `sees_all_departments`, and holds every ACT permission (403) → no target
row modified since commit (409 `conflicts[]`, nothing reverted). Then every `applied` action is
reversed in `seq DESC` (reused refs wrote nothing → skipped), lineage links get `revoked_at`,
`critical_field_wrong` opens a G4 incident per critical field, audit + `idp.document_rolled_back`
in the same transaction.
"""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import (
    ConflictStateError,
    NotFoundError,
    PermissionDeniedError,
    UndoExpiredError,
)
from app.core.events.outbox import publish_in_tx
from app.modules.idp.models import DocumentAction, SourceDocument
from app.modules.idp.repositories import (
    DocumentActionRepository,
    SourceDocumentRepository,
    approvers_of,
)
from app.modules.idp.schemas import ActionRefOut
from app.modules.idp.schemas.capture import DocumentActionOut, UndoIn, UndoOut
from app.modules.idp.services.actions import get_action
from app.modules.idp.services.actions.executor import outcome_of
from app.modules.idp.services.capture_common import document_out, type_code
from app.modules.idp.services.scope import document_visible, sees_all_departments
from app.modules.idp.services.undo_versions import current_version
from app.modules.platform.services.lineage_service import LineageService

EVT_ROLLED_BACK = "idp.document_rolled_back"


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(ts: datetime) -> datetime:
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


class UndoService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.actions = DocumentActionRepository(db)

    async def _doc(self, user: Principal, document_id: uuid.UUID) -> SourceDocument:
        doc = await SourceDocumentRepository(self.db).by_id(document_id)
        if doc is None or not document_visible(user, doc):
            raise NotFoundError("document not found")
        return doc

    async def actions_of(self, user: Principal, document_id: uuid.UUID) -> list[DocumentActionOut]:
        """EP-DC-25 — the Action Registry log of one document (seq ASC)."""
        doc = await self._doc(user, document_id)
        rows = await self.actions.for_document(doc.id)
        return [
            DocumentActionOut(seq=a.seq, action_name=a.action_name,
                              result_refs=list(a.result_refs or []), status=a.status,
                              reverted_at=a.reverted_at)
            for a in rows
        ]  # fmt: skip

    async def undo(self, user: Principal, document_id: uuid.UUID, body: UndoIn) -> UndoOut:
        doc = await self._doc(user, document_id)
        if doc.status != "COMMITTED":
            raise ConflictStateError(f"cannot undo a {doc.status} document",
                                     details={"status": doc.status})  # fmt: skip
        if doc.undo_deadline is None or _aware(doc.undo_deadline) <= _now():
            raise UndoExpiredError(
                "undo window elapsed",
                details={
                    "undo_deadline": doc.undo_deadline.isoformat() if doc.undo_deadline else None
                },
            )
        await self._authorize(user, doc)
        applied = [a for a in await self.actions.for_document(doc.id, newest_first=True)
                   if a.status == "applied"]  # fmt: skip
        missing = sorted(
            {
                p
                for a in applied
                if (act := get_action(a.action_name)) is not None and not act.permitted(user)
                for p in act.required_permission
            }
        )
        if missing:
            raise PermissionDeniedError("missing target permission", details={"missing": missing})
        if conflicts := await self._conflicts(user, applied):
            raise ConflictStateError("target modified after commit",
                                     details={"conflicts": conflicts})  # fmt: skip
        now = _now()
        for a in applied:  # seq DESC
            act = get_action(a.action_name)
            outcome = outcome_of(a)
            if act is not None and any(not r.get("reused") for r in outcome.result_refs):
                await act.undo(self.db, user, outcome)
            a.status, a.reverted_at, a.reverted_by = "reverted", now, user.user_id
        await LineageService(self.db).revoke([a.id for a in applied])
        doc.status = "ROLLED_BACK"
        doc.version += 1
        doc.rolled_back_at, doc.rolled_back_by = now, user.user_id
        doc.rollback_reason_code = body.reason_code
        await self.db.flush()
        if body.reason_code == "critical_field_wrong":
            await self._incidents(user, doc, applied)
        return await self._finish(user, doc, applied, body)

    async def _authorize(self, user: Principal, doc: SourceDocument) -> None:
        """R-DEC-66: submitter, an approver, the committer, or `sees_all_departments`."""
        if sees_all_departments(user) or user.user_id in {doc.submitted_by, doc.committed_by}:
            return
        if user.user_id in await approvers_of(self.db, doc.id):
            return
        raise PermissionDeniedError("only the submitter, approver or committer may undo")

    async def _conflicts(
        self, user: Principal, applied: list[DocumentAction]
    ) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for a in applied:
            if a.target_version is None:
                continue
            for r in a.result_refs or []:
                if r.get("reused"):
                    continue
                table = f"{r['schema']}.{r['table']}"
                now = await current_version(self.db, user, table, uuid.UUID(str(r["id"])))
                if now is not None and now != a.target_version:
                    out.append({"table": table, "id": str(r["id"])})
        return out

    async def _incidents(
        self, user: Principal, doc: SourceDocument, applied: list[DocumentAction]
    ) -> None:
        from app.modules.idp.repositories import ExtractedFieldRepository
        from app.modules.idp.services.incident_service import IncidentService

        fields = await ExtractedFieldRepository(self.db).critical_of_document(doc.id)
        seen: set[str] = set()
        svc = IncidentService(self.db)
        for f in fields:
            if f.field_name in seen:
                continue
            seen.add(f.field_name)
            await svc.record(doc.id, f.id, f.field_name, critical=True, detected_by="undo",
                             description="undo: critical_field_wrong", user=user)  # fmt: skip

    async def _finish(
        self, user: Principal, doc: SourceDocument, applied: list[DocumentAction], body: UndoIn
    ) -> UndoOut:
        code = await type_code(self.db, doc.document_type_id)
        counts = Counter(a.action_name for a in applied)
        refs: dict[tuple[str, str], list[str]] = {}
        for a in reversed(applied):  # seq ASC in the response
            for r in a.result_refs or []:
                refs.setdefault((a.action_name, f"{r['schema']}.{r['table']}"), []).append(
                    str(r["id"])
                )
        reverted = [ActionRefOut(action_name=n, table=t, ids=i) for (n, t), i in refs.items()]
        tables = sorted({t for _, t in refs})
        await record_audit(
            self.db, action="idp.document_rollback", target_schema="idp",
            target_table="source_documents", target_id=doc.id,
            before={"status": "COMMITTED"},
            after={"status": "ROLLED_BACK", "reason_code": body.reason_code,
                   "reverted": [a.seq for a in applied]},
            why=body.reason,
        )  # fmt: skip
        await publish_in_tx(
            self.db, event_type=EVT_ROLLED_BACK, producer="idp", aggregate_schema="idp",
            aggregate_table="source_documents", aggregate_id=doc.id,
            payload={
                "document_id": str(doc.id), "document_type": code, "channel": doc.channel,
                "reverted_actions": [{"action_name": n, "count": c} for n, c in counts.items()],
                "target_tables": tables, "rolled_back_by": str(user.user_id),
                "reason_code": body.reason_code,
            },
        )  # fmt: skip
        return UndoOut(document=document_out(doc, code), reverted_actions=reverted)

"""C1 manual capture — EP-DC-15 form + EP-DC-16 submit (10 §7.2.4, 04 §2.1, R-DEC-65).

The form is the published `ExtractionSchema` of the doc type (never hard-coded). Submit
normalises + validates every value (Validator `fail/blocking` → `422 VALIDATION_ERROR`
`details.fields[]`, nothing written), then records `SourceDocument(kind=MANUAL, channel=C1)`
+ one `ExtractionJob` + `ExtractedField`s (confidence 1.0, `source=MANUAL`). The entrant is
the confirmer (R-DEC-65): holding every ACT permission → commit now through the Action
Registry; otherwise — or when a target service refuses the caller's scope (EMP sending a
department KPI) — the document waits in `NEEDS_REVIEW` for someone who may write it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import ActionRejectedError, ConflictStateError, ScopeDeniedError
from app.core.errors import ValidationError as AppValidationError
from app.core.field_policy import Masked
from app.modules.idp.models import ExtractedField, ExtractionJob, SourceDocument
from app.modules.idp.schemas.capture import FormFieldOut, FormOut, ManualSubmitIn, ManualSubmitOut
from app.modules.idp.services.actions import get_action
from app.modules.idp.services.actions.executor import build_plan, missing_permissions
from app.modules.idp.services.capture_common import (
    Published,
    assign_initial_review,
    classification_of,
    document_out,
    normalize,
    published_schema,
    required_errors,
    row_error,
)
from app.modules.idp.services.critical import is_critical
from app.modules.idp.services.scope import ensure_doc_type_scope, sees_all_departments
from app.modules.idp.services.validator import Validator

_FORBIDDEN = frozenset({"FORBIDDEN_ROLE", "FORBIDDEN_SCOPE", "FORBIDDEN_SALARY"})
Row = tuple[int | None, dict[str, Any]]


def required_permissions(action_names: list[str]) -> list[str]:
    """First `required_permission` of every ACT of the schema (any-of shown by its head)."""
    out: list[str] = []
    for name in action_names:
        act = get_action(name)
        if act is not None and act.required_permission[0] not in out:
            out.append(act.required_permission[0])
    return out


def _permitted(user: Principal, action_names: list[str]) -> bool:
    acts = [get_action(n) for n in action_names]
    return all(a is not None and a.permitted(user) for a in acts)


class ManualService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------- EP-DC-15
    async def form(self, user: Principal, code: str) -> FormOut:
        ensure_doc_type_scope(user, code)  # R-DEC-76
        pub = await published_schema(self.db, code)
        names = list(pub.schema.action_names or [])
        fields = [
            FormFieldOut(
                name=f["name"], label_key=f.get("label_key") or f"idp.field.{f['name']}",
                value_type=f.get("value_type", "text"), required=bool(f.get("required")),
                is_critical=is_critical(f),
                sensitivity_level=int(f.get("sensitivity_level", 2)), enum=f.get("enum"),
                master_ref=f.get("master_ref"),
                repeatable_group="rows" if f.get("group") == "row" else None,
            )
            for f in pub.fields
        ]  # fmt: skip
        return FormOut(document_type=code, schema_version=pub.schema.schema_version,
                       fields=fields, required_permissions=required_permissions(names),
                       permitted=_permitted(user, names))  # fmt: skip

    # ------------------------------------------------------------- EP-DC-16
    async def submit(self, user: Principal, body: ManualSubmitIn) -> ManualSubmitOut:
        ensure_doc_type_scope(user, body.document_type)  # R-DEC-76
        pub = await published_schema(self.db, body.document_type)
        if pub.schema.schema_version != body.schema_version:  # stale form
            raise ConflictStateError(
                "form schema changed", details={"schema_version": pub.schema.schema_version}
            )
        department_id = self._department(user, body.department_id)
        rows = self._normalised(pub, body)
        names = list(pub.schema.action_names or [])
        steps = build_plan(names, pub.fields, [(n, r, v) for r, vals in rows
                                               for n, v in vals.items()])  # fmt: skip
        doc, job = await self._record(user, pub, body, rows, department_id)
        commit_now = not missing_permissions(user, steps)
        out = await self._commit_or_queue(user, doc, job, commit_now)
        await record_audit(
            self.db, action="idp.manual_submit", target_schema="idp",
            target_table="source_documents", target_id=doc.id,
            after={"document_type": body.document_type, "status": doc.status,
                   "row_count": doc.row_count, "fields": sum(len(v) for _, v in rows)},
        )  # fmt: skip
        return out

    def _department(self, user: Principal, wanted: uuid.UUID | None) -> uuid.UUID | None:
        if wanted is None or wanted == user.department_id:
            return user.department_id
        if not sees_all_departments(user):
            raise ScopeDeniedError("department outside your scope",
                                   details={"department_id": str(wanted)})  # fmt: skip
        return wanted

    def _normalised(self, pub: Published, body: ManualSubmitIn) -> list[Row]:
        """`[(row_index, {field: value})]` — header fields at `None`, repeatable rows at 1..n.

        Every format/required/rule error of every row is collected → one `422`.
        """
        header = [f for f in pub.fields if f.get("group") != "row"]
        grouped = [f for f in pub.fields if f.get("group") == "row"]
        raw_rows = body.rows if body.rows is not None else ([body.values] if grouped else [])
        errors: list[dict[str, Any]] = []
        rows: list[Row] = []
        if header:
            rows.append((None, self._row(header, body.values, None, errors)))
        for i, raw in enumerate(raw_rows, start=1):
            rows.append((i, self._row(grouped, raw, i, errors)))
        if grouped and not raw_rows:
            errors.append({**row_error("rows", "REQUIRED"), "row_index": None})
        rules = pub.rules
        if not errors:
            context = rows[0][1] if header else {}
            for idx, vals in rows:
                res = Validator(rules).validate({**context, **vals}) if rules else None
                for e in res.errors if res else []:
                    errors.append({**row_error(e["field"], e["rule"]), "row_index": idx})
        if errors:
            raise AppValidationError("manual form invalid", details={"fields": errors})
        return rows

    @staticmethod
    def _row(
        specs: list[dict[str, Any]], raw: dict[str, Any], idx: int | None,
        errors: list[dict[str, Any]],
    ) -> dict[str, Any]:  # fmt: skip
        known = {f["name"] for f in specs}
        out: dict[str, Any] = {}
        mine: list[dict[str, Any]] = []
        for name in sorted(set(raw) - known):
            errors.append({**row_error(name, "UNKNOWN_FIELD"), "row_index": idx})
        for spec in specs:
            value, err = normalize(spec, raw.get(spec["name"]))
            if err is not None:
                mine.append(err)
            elif value is not None:
                out[spec["name"]] = value
        mine += required_errors(specs, out, mine)
        errors += [{**e, "row_index": idx} for e in mine]
        return out

    async def _record(
        self, user: Principal, pub: Published, body: ManualSubmitIn, rows: list[Row],
        department_id: uuid.UUID | None,
    ) -> tuple[SourceDocument, ExtractionJob]:  # fmt: skip
        now = datetime.now(UTC)
        dt = pub.doc_type
        doc = SourceDocument(
            channel="C1", kind="MANUAL", scan_status="SKIPPED", document_type_id=dt.id,
            type_preselected=True, classification_confidence=1, pillars=list(dt.pillars or []),
            status="VALIDATING", sensitivity_level=dt.sensitivity_level,
            manual_payload=self._payload(user, pub, body), source="MANUAL",
            data_classification=classification_of(dt.sensitivity_level),
            submitted_by=user.user_id, submitted_at=now, department_id=department_id,
            row_count=sum(1 for r, _ in rows if r is not None) or None,
        )  # fmt: skip
        self.db.add(doc)
        await self.db.flush()
        job = ExtractionJob(
            source_document_id=doc.id, extraction_schema_id=pub.schema.id, attempt_no=1,
            status="SUCCEEDED", document_confidence=1, routing_decision="REVIEW",
            routing_reasons=[], xd_results={"validation_errors": []}, started_at=now,
            finished_at=now,
        )  # fmt: skip
        self.db.add(job)
        await self.db.flush()
        specs = {f["name"]: f for f in pub.fields}
        for idx, values in rows:
            for name, value in values.items():
                spec = specs[name]
                level = int(spec.get("sensitivity_level", 2))
                self.db.add(ExtractedField(
                    extraction_job_id=job.id, document_page_id=None, field_name=name,
                    row_index=idx, value_type=spec.get("value_type", "text"), value=value,
                    raw_text=None if level >= 4 else str(value), confidence=1,
                    confidence_band="HIGH", is_critical=is_critical(spec),
                    sensitivity_level=level,
                    source_location={"kind": "manual", "row_index": idx},
                    validation=[], source="MANUAL",
                    data_classification=classification_of(level),
                ))  # fmt: skip
        await self.db.flush()
        return doc, job

    @staticmethod
    def _payload(user: Principal, pub: Published, body: ManualSubmitIn) -> dict[str, Any]:
        """Original form body; level-4 values are not kept in clear (05 §2.7)."""
        lvl4 = {f["name"] for f in pub.fields if int(f.get("sensitivity_level", 2)) >= 4}

        def scrub(values: dict[str, Any]) -> dict[str, Any]:
            return {k: (Masked().model_dump() if k in lvl4 else v) for k, v in values.items()}

        rows = [scrub(r) for r in body.rows] if body.rows is not None else None
        return {"schema_version": body.schema_version, "values": scrub(body.values),
                "rows": rows}  # fmt: skip

    async def _commit_or_queue(
        self, user: Principal, doc: SourceDocument, job: ExtractionJob, commit_now: bool
    ) -> ManualSubmitOut:
        from app.modules.idp.services.capture_common import type_code
        from app.modules.idp.services.commit_service import CommitService

        code = await type_code(self.db, doc.document_type_id)
        if commit_now:
            try:
                out = await CommitService(self.db).commit_direct(user, doc)
            except ActionRejectedError as exc:
                if exc.details.get("cause_code") not in _FORBIDDEN:
                    raise  # data error → 422, the request transaction is not committed
                await self.db.refresh(doc)  # target scope refused → wait for a writer
            else:
                return ManualSubmitOut(document=out.document, status=out.document.status,
                                       actions=out.actions, validation_errors=[],
                                       undo_deadline=out.undo_deadline)  # fmt: skip
        doc.status = "NEEDS_REVIEW"
        doc.routing_reason = "MISSING_TARGET_PERMISSION"
        await self.db.flush()
        await assign_initial_review(self.db, doc)
        return ManualSubmitOut(document=document_out(doc, code), status=doc.status, actions=[],
                               validation_errors=[], undo_deadline=None)  # fmt: skip

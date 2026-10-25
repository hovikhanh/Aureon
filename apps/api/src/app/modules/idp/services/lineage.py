"""T-637 — record lineage on every commit (FR-DATA-04, R-DEC-64).

After `run_all` the `idp.document_actions` rows exist (seq = order of `done`). Each applied step
links every target column it wrote back to the extracted field that fed it: a targeted field
(`target.param`) or an untargeted row-context field filling a same-named param (`period_key`,
`owner_code`, …). Reused refs (an existing master row matched by code) wrote nothing → no link.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.idp.models import ExtractedField
from app.modules.idp.repositories import DocumentActionRepository
from app.modules.platform.services.lineage_service import LineageLink, LineageService


def _columns(
    step: Any, single: str | None, defs: dict[str, dict[str, Any]],
    row_fields: dict[str, ExtractedField],
) -> dict[str, ExtractedField]:  # fmt: skip
    """`{target_column: field}` for one (ACT, row) step."""
    out: dict[str, ExtractedField] = {}
    for name, f in row_fields.items():
        target = (defs.get(name) or {}).get("target")
        action, param = (target["action"], target["param"]) if target else (single, name)
        if action == step.act.name and param in step.params:
            out.setdefault(param, f)
    for name, f in row_fields.items():  # row context shared across the row's steps
        if name in step.params and name not in out and not (defs.get(name) or {}).get("target"):
            out[name] = f
    return out


async def record_commit_lineage(
    db: AsyncSession, document_id: uuid.UUID, fields: list[ExtractedField],
    schema_fields: list[dict[str, Any]], done: list[Any],
) -> int:  # fmt: skip
    if not done:
        return 0
    defs = {f["name"]: f for f in schema_fields}
    names = list(dict.fromkeys(step.act.name for step, _ in done))
    single = names[0] if len(names) == 1 else None
    by_row: dict[int | None, dict[str, ExtractedField]] = {}
    for f in fields:
        by_row.setdefault(f.row_index, {})[f.field_name] = f
    actions = await DocumentActionRepository(db).for_document(document_id)
    action_ids = {a.seq: a.id for a in actions}
    links: list[LineageLink] = []
    for seq, (step, outcome) in enumerate(done, start=1):
        cols = _columns(step, single, defs, by_row.get(step.row_index, {}))
        for ref in outcome.result_refs:
            if ref.get("reused"):
                continue
            for column, f in sorted(cols.items()):
                links.append(LineageLink(
                    target_schema=ref["schema"], target_table=ref["table"],
                    target_id=uuid.UUID(str(ref["id"])), target_column=column,
                    source_document_id=document_id, extracted_field_id=f.id,
                    document_page_id=f.document_page_id, document_action_id=action_ids.get(seq),
                    row_index=step.row_index, action_name=step.act.name,
                ))  # fmt: skip
    return await LineageService.record_many(db, links)


# ---------------------------------------------------------------- EP-DC-26 reader
async def _target_visible(db: AsyncSession, user: Any, entity: str, rid: uuid.UUID) -> None:
    """Scoped read through the owning module's public service (raises 403/404 outside scope).

    `hr:read` / `execution:read` / `finance:read` (+ DIR pillar) are required first — lineage
    never widens what the caller could read on the target endpoint (R-DEC-64)."""
    from app.core.errors import PermissionDeniedError

    domain = entity.split(".", 1)[0]
    if not user.has(f"{domain}:read") or not user.in_pillar(domain):
        raise PermissionDeniedError(f"missing {domain}:read")
    if domain == "hr":
        await _hr_visible(db, user, entity, rid)
    elif domain == "finance":
        from app.modules.finance.services.invoice_service import InvoiceService

        await InvoiceService(db).get(rid)
    else:
        await _execution_visible(db, user, entity, rid)


async def _hr_visible(db: AsyncSession, user: Any, entity: str, rid: uuid.UUID) -> None:
    from app.modules.hr.services.hr_service import HrService
    from app.modules.hr.services.structure_service import StructureService

    if entity == "hr.employees":
        await HrService(db).get_employee_row(user, rid)
    elif entity == "hr.departments":
        await StructureService(db).get_department_visible(user, rid)
    elif entity == "hr.teams":
        await StructureService(db).get_team(user, rid)
    else:
        await StructureService(db).get_position(user, rid)


async def _execution_visible(db: AsyncSession, user: Any, entity: str, rid: uuid.UUID) -> None:
    from app.modules.execution.services.kpi_service import KpiService
    from app.modules.execution.services.okr_service import OkrService
    from app.modules.execution.services.task_service import TaskService

    table = entity.split(".", 1)[1]
    if table == "tasks":
        await TaskService(db).get(user, rid)
    elif table == "objectives":
        await OkrService(db).get_objective(user, rid)
    elif table == "key_results":
        await OkrService(db).get_kr(user, rid)
    elif table == "kpis":
        await KpiService(db).get_kpi(user, rid)
    elif table == "kpi_targets":
        await KpiService(db).get_target(user, rid)
    elif table == "kpi_measurements":
        await KpiService(db).get_measurement(user, rid)
    else:
        await KpiService(db).get_check_in(user, rid)


async def read_lineage(db: AsyncSession, user: Any, entity: str, rid: uuid.UUID) -> Any:
    """EP-DC-26: `LineageOut` — `{restricted, reason}` when either side is out of scope."""
    from sqlalchemy import select

    from app.core.errors import AppError
    from app.core.errors import ValidationError as AppValidationError
    from app.core.field_policy import Masked, sees_level4
    from app.modules.idp.models import DocumentPage, DocumentType
    from app.modules.idp.repositories import ExtractedFieldRepository, SourceDocumentRepository
    from app.modules.idp.schemas.capture import LineageLinkOut, LineageOut
    from app.modules.idp.services.scope import lineage_visible
    from app.modules.platform.services.lineage_service import LINEAGE_ENTITIES

    if entity not in LINEAGE_ENTITIES:
        raise AppValidationError("unknown lineage entity", details={
            "fields": ["entity"], "allowed": sorted(LINEAGE_ENTITIES)})  # fmt: skip
    try:
        await _target_visible(db, user, entity, rid)
    except AppError as exc:
        if exc.status_code not in (403, 404):
            raise
        return LineageOut(restricted=True, reason="target_out_of_scope")
    rows = await LineageService(db).for_record(entity, rid)
    docs = SourceDocumentRepository(db)
    by_doc = {d: await docs.by_id(d) for d in {r.source_document_id for r in rows} if d}
    for doc in by_doc.values():
        if doc is None or not await lineage_visible(db, user, doc):
            return LineageOut(restricted=True, reason="source_out_of_scope")
    fields = await ExtractedFieldRepository(db).by_ids(
        [r.extracted_field_id for r in rows if r.extracted_field_id]
    )
    page_ids = [r.document_page_id for r in rows if r.document_page_id]
    pages = (
        {
            p.id: p
            for p in (
                await db.execute(select(DocumentPage).where(DocumentPage.id.in_(page_ids)))
            ).scalars()
        }
        if page_ids
        else {}
    )
    type_ids = {d.document_type_id for d in by_doc.values() if d and d.document_type_id}
    codes = dict((await db.execute(select(DocumentType.id, DocumentType.code).where(
        DocumentType.id.in_(type_ids)))).tuples().all()) if type_ids else {}  # fmt: skip
    level4 = sees_level4(user)
    links = []
    for r in rows:
        doc = by_doc.get(r.source_document_id) if r.source_document_id else None
        f = fields.get(r.extracted_field_id) if r.extracted_field_id else None
        p = pages.get(r.document_page_id) if r.document_page_id else None
        raw: Any = f.raw_text if f is not None else None
        if f is not None and f.sensitivity_level >= 4 and not level4:
            raw = Masked()
        links.append(LineageLinkOut(
            target_column=r.target_column, source_document_id=r.source_document_id,
            document_type=codes.get(doc.document_type_id) if doc and doc.document_type_id else None,
            original_filename=doc.original_filename if doc else None,
            page_number=p.page_number if p else None, sheet_name=p.sheet_name if p else None,
            row_index=r.row_index, field_name=f.field_name if f else None, raw_text=raw,
            confidence=float(f.confidence) if f is not None and f.confidence is not None else None,
            action_name=r.action_name, committed_at=doc.committed_at if doc else None,
            revoked_at=r.revoked_at,
        ))  # fmt: skip
    return LineageOut(entity=entity, id=rid, links=links)

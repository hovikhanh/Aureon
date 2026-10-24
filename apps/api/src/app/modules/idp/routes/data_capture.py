"""`/data-capture/*` — D03 Data Capture M1.5: EP-DC-13..25, EP-DC-27..37 (10 §7.2.4, R-DEC-39).

Each endpoint holds exactly one `idp:*` permission; the domain write permission of every ACT is
checked inside the Action Registry v2 (R-DEC-61). Endpoints whose behaviour lands in a later
M1.5 task answer `501` (`core/stub.py`). Static paths (`/inbox`, `/imports`, …) come before
`{id}` paths.
"""

import uuid
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import Depends, File, Form, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_db, require_permission
from app.core.envelope import Page
from app.core.errors import DuplicateResourceError
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.core.stub import not_implemented
from app.modules.idp.schemas import ApproveOut
from app.modules.idp.schemas.capture import (
    DocumentActionOut,
    DocumentTypeOut,
    DocumentTypePatch,
    ExtractionSchemaCreate,
    ExtractionSchemaOut,
    ExtractionSchemaPatch,
    FormOut,
    ImportMappingIn,
    ImportPreviewOut,
    ImportRowOut,
    ImportSubmitOut,
    InboxGroup,
    InboxItemOut,
    IncidentCreate,
    IncidentOut,
    ManualSubmitIn,
    ManualSubmitOut,
    RuleKind,
    SchemaStatus,
    SourceViewOut,
    UndoIn,
    UndoOut,
    ValidationRuleCreate,
    ValidationRuleOut,
    ValidationRulePatch,
    VersionIn,
)
from app.modules.idp.services.admin_service import CaptureAdminService
from app.modules.idp.services.commit_service import CommitService
from app.modules.idp.services.import_parse import XLSX
from app.modules.idp.services.import_service import ImportService
from app.modules.idp.services.inbox_service import InboxFilters, InboxService
from app.modules.idp.services.manual_service import ManualService
from app.modules.idp.services.scope import ensure_doc_type_scope
from app.modules.idp.services.upload_service import UploadFile as SvcUploadFile

router = EnvelopeRouter(prefix="/data-capture", tags=["data-capture"])

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_permission("idp:read"))]
Writer = Annotated[Principal, Depends(require_permission("idp:write"))]
Approver = Annotated[Principal, Depends(require_permission("idp:approve"))]
Admin = Annotated[Principal, Depends(require_permission("idp:admin"))]
_CHUNK = 1024 * 1024  # stream 1 MB chunks (04 §15.1)


def _svc_file(upload: UploadFile) -> SvcUploadFile:
    def _chunks() -> Iterator[bytes]:
        upload.file.seek(0)
        while data := upload.file.read(_CHUNK):
            yield data

    return SvcUploadFile(filename=upload.filename, content_type=upload.content_type,
                         chunks=_chunks())  # fmt: skip


# ---------- EP-DC-13 inbox ----------
@router.get("/inbox", response_model=list[InboxItemOut], summary="EP-DC-13 Data inbox")
async def inbox(
    user: Reader,
    page: Annotated[PageParams, Depends(page_params("submitted_at", "committed_at"))],
    group: InboxGroup | None = None, channel: str | None = None,
    document_type: str | None = None, mine: bool = False, q: str | None = None,
    date_from: str | None = None, date_to: str | None = None,
    *, db: Db,
) -> Any:  # fmt: skip
    filters = InboxFilters(group=group, channel=channel, document_type=document_type, mine=mine,
                           q=q, date_from=date_from, date_to=date_to)  # fmt: skip
    items, total, counts = await InboxService(db).inbox(user, page, filters)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset, counts=counts)


# ---------- EP-DC-15/16 C1 manual ----------
@router.get("/forms/{document_type}", response_model=FormOut, summary="EP-DC-15 C1 form schema")
async def get_form(document_type: str, user: Writer, db: Db) -> Any:
    return await ManualService(db).form(user, document_type)  # R-DEC-76 scope inside


@router.post(
    "/manual", response_model=ManualSubmitOut, status_code=201,
    summary="EP-DC-16 C1 manual submit",
)  # fmt: skip
async def manual_submit(body: ManualSubmitIn, user: Writer, db: Db, idem: Idem) -> Any:
    ensure_doc_type_scope(user, body.document_type)  # R-DEC-76
    if (hit := await idem.replay(body)) is not None:
        return ManualSubmitOut.model_validate(hit)
    out = await ManualService(db).submit(user, body)
    await db.commit()
    await idem.remember(out)
    return out


# ---------- EP-DC-17..22 C5 import ----------
@router.post(
    "/imports", response_model=ImportPreviewOut, status_code=201,
    summary="EP-DC-17 C5 import upload + preview",
)  # fmt: skip
async def import_upload(
    user: Writer, db: Db, idem: Idem,
    file: Annotated[UploadFile, File(description="one .xlsx / .csv file")],
    document_type: Annotated[str | None, Form()] = None,
) -> Any:  # fmt: skip
    ensure_doc_type_scope(user, document_type)  # R-DEC-76
    key = {"filename": file.filename, "size": file.size, "document_type": document_type}
    if (hit := await idem.replay(key)) is not None:
        return ImportPreviewOut.model_validate(hit)
    outcome = await ImportService(db).upload(user, _svc_file(file), document_type)
    await db.commit()  # a DUPLICATE document is kept (05 §6) before answering 409
    if outcome.preview is None:
        raise DuplicateResourceError("file already imported", details={
            "duplicate_of_id": str(outcome.duplicate_of_id),
            "document_id": str(outcome.document_id)})  # fmt: skip
    await idem.remember(outcome.preview)
    return outcome.preview


@router.get(
    "/imports/{batch_id}", response_model=ImportPreviewOut, summary="EP-DC-18 C5 import preview"
)
async def import_get(batch_id: uuid.UUID, user: Reader, db: Db) -> Any:
    return await ImportService(db).preview(user, batch_id)


@router.patch(
    "/imports/{batch_id}/mapping", response_model=ImportPreviewOut,
    summary="EP-DC-19 C5 update column mapping",
)  # fmt: skip
async def import_mapping(batch_id: uuid.UUID, body: ImportMappingIn, user: Writer, db: Db) -> Any:
    ensure_doc_type_scope(user, body.document_type)  # R-DEC-76
    out = await ImportService(db).update_mapping(user, batch_id, body)
    await db.commit()
    return out


@router.get(
    "/imports/{batch_id}/rows", response_model=list[ImportRowOut],
    summary="EP-DC-20 C5 import rows",
)  # fmt: skip
async def import_rows(
    batch_id: uuid.UUID, user: Reader,
    page: Annotated[PageParams, Depends(page_params("row_number"))],
    status: Annotated[str, Query(pattern="^(valid|invalid|all)$")] = "all",
    *, db: Db,
) -> Any:  # fmt: skip
    items, total = await ImportService(db).rows(
        user, batch_id, status, page.limit, page.offset, page.order
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get(
    "/imports/{batch_id}/error-file", response_class=Response,
    summary="EP-DC-21 C5 error rows file (.xlsx)",
    responses={200: {"content": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}}}},
)  # fmt: skip
async def import_error_file(batch_id: uuid.UUID, user: Reader, db: Db) -> Response:
    content = await ImportService(db).error_file(user, batch_id)
    return Response(content=content, media_type=XLSX, headers={
        "Content-Disposition": f'attachment; filename="import-errors-{batch_id}.xlsx"',
        "Cache-Control": "no-store"})  # fmt: skip


@router.post(
    "/imports/{batch_id}/submit", response_model=ImportSubmitOut,
    summary="EP-DC-22 C5 submit valid rows for review",
)  # fmt: skip
async def import_submit(
    batch_id: uuid.UUID, body: VersionIn, user: Writer, db: Db, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ImportSubmitOut.model_validate(hit)
    out = await ImportService(db).submit(user, batch_id, body.version)
    await db.commit()
    await idem.remember(out)
    return out


# ---------- EP-DC-14, 23..25 per-document ----------
@router.get(
    "/documents/{document_id}/source", response_model=SourceViewOut,
    summary="EP-DC-14 View source document (presigned 5 min)",
)  # fmt: skip
async def document_source(
    document_id: uuid.UUID, user: Reader, db: Db,
    page: Annotated[int | None, Query(ge=1)] = None,
) -> Any:  # fmt: skip
    out = await InboxService(db).source(user, document_id, page)
    await db.commit()  # `idp.source_view` audit (level ≥ 3)
    return out


@router.post(
    "/documents/{document_id}/commit", response_model=ApproveOut,
    summary="EP-DC-23 Commit an APPROVED document (domain write permission)",
)  # fmt: skip
async def document_commit(
    document_id: uuid.UUID, body: VersionIn, user: Writer, db: Db, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ApproveOut.model_validate(hit)
    out = await CommitService(db).commit(user, document_id, expected_version=body.version)
    await db.commit()
    await idem.remember(out)
    return out


@router.post(
    "/documents/{document_id}/undo", response_model=UndoOut,
    summary="EP-DC-24 Undo a committed document (7 days)",
)  # fmt: skip
async def document_undo(document_id: uuid.UUID, body: UndoIn, user: Writer, idem: Idem) -> Any:
    not_implemented("EP-DC-24", "T-638")


@router.get(
    "/documents/{document_id}/actions", response_model=list[DocumentActionOut],
    summary="EP-DC-25 Document actions (Action Registry log)",
)  # fmt: skip
async def document_actions(document_id: uuid.UUID, user: Reader) -> Any:
    not_implemented("EP-DC-25", "T-638")


# ---------- EP-DC-27/28 document types ----------
@router.get(
    "/document-types", response_model=list[DocumentTypeOut],
    summary="EP-DC-27 List document types",
)  # fmt: skip
async def list_document_types(user: Reader, db: Db, include_inactive: bool = False) -> Any:
    return await CaptureAdminService(db).list_types(user, include_inactive=include_inactive)


@router.patch(
    "/document-types/{type_id}", response_model=DocumentTypeOut,
    summary="EP-DC-28 Update document type",
)  # fmt: skip
async def patch_document_type(
    type_id: uuid.UUID, body: DocumentTypePatch, user: Admin, db: Db
) -> Any:
    out = await CaptureAdminService(db).patch_type(user, type_id, body)
    await db.commit()
    return out


# ---------- EP-DC-29..32 extraction schemas ----------
@router.get(
    "/extraction-schemas", response_model=list[ExtractionSchemaOut],
    summary="EP-DC-29 List extraction schemas",
)  # fmt: skip
async def list_schemas(
    user: Admin, db: Db, document_type: str | None = None, status: SchemaStatus | None = None
) -> Any:
    return await CaptureAdminService(db).list_schemas(document_type=document_type, status=status)


@router.post(
    "/extraction-schemas", response_model=ExtractionSchemaOut, status_code=201,
    summary="EP-DC-30 Create extraction schema draft",
)  # fmt: skip
async def create_schema(body: ExtractionSchemaCreate, user: Admin, db: Db, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ExtractionSchemaOut.model_validate(hit)
    out = await CaptureAdminService(db).create_schema(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.patch(
    "/extraction-schemas/{schema_id}", response_model=ExtractionSchemaOut,
    summary="EP-DC-31 Update extraction schema draft",
)  # fmt: skip
async def patch_schema(
    schema_id: uuid.UUID, body: ExtractionSchemaPatch, user: Admin, db: Db
) -> Any:
    out = await CaptureAdminService(db).patch_schema(user, schema_id, body)
    await db.commit()
    return out


@router.post(
    "/extraction-schemas/{schema_id}/publish", response_model=ExtractionSchemaOut,
    summary="EP-DC-32 Publish extraction schema",
)  # fmt: skip
async def publish_schema(
    schema_id: uuid.UUID, body: VersionIn, user: Admin, db: Db, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ExtractionSchemaOut.model_validate(hit)
    out = await CaptureAdminService(db).publish_schema(user, schema_id, body.version)
    await db.commit()
    await idem.remember(out)
    return out


# ---------- EP-DC-33..35 validation rules ----------
@router.get(
    "/validation-rules", response_model=list[ValidationRuleOut],
    summary="EP-DC-33 List validation rules",
)  # fmt: skip
async def list_rules(
    user: Admin, db: Db, extraction_schema_id: uuid.UUID | None = None,
    kind: RuleKind | None = None,
) -> Any:  # fmt: skip
    return await CaptureAdminService(db).list_rules(schema_id=extraction_schema_id, kind=kind)


@router.post(
    "/validation-rules", response_model=ValidationRuleOut, status_code=201,
    summary="EP-DC-34 Create validation rule",
)  # fmt: skip
async def create_rule(body: ValidationRuleCreate, user: Admin, db: Db, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ValidationRuleOut.model_validate(hit)
    out = await CaptureAdminService(db).create_rule(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.patch(
    "/validation-rules/{rule_id}", response_model=ValidationRuleOut,
    summary="EP-DC-35 Update validation rule",
)  # fmt: skip
async def patch_rule(rule_id: uuid.UUID, body: ValidationRulePatch, user: Admin, db: Db) -> Any:
    out = await CaptureAdminService(db).patch_rule(user, rule_id, body)
    await db.commit()
    return out


# ---------- EP-DC-36/37 incidents (G4) ----------
@router.post(
    "/incidents", response_model=IncidentOut, status_code=201,
    summary="EP-DC-36 Report capture incident",
)  # fmt: skip
async def create_incident(body: IncidentCreate, user: Approver, idem: Idem) -> Any:
    not_implemented("EP-DC-36", "T-640")


@router.get(
    "/incidents", response_model=list[IncidentOut], summary="EP-DC-37 List capture incidents"
)
async def list_incidents(
    user: Approver,
    page: Annotated[PageParams, Depends(page_params("reported_at"))],
    period: str | None = None, undetected_only: bool = False,
) -> Any:  # fmt: skip
    not_implemented("EP-DC-37", "T-640")

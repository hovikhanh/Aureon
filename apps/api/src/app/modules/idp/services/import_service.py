"""C5 Excel/CSV import — EP-DC-17..22 (10 §7.2.4, FR-DC-17/18, R-DEC-62/65/76).

One file = one `ImportBatch(kind=excel_import)` = one `SourceDocument(channel=C5)`. Upload
streams the file to the object store, parses it (`import_parse`, limits → 413), suggests the
doc type from the header row (`Classifier` tier 2, `header_score`) and maps every column whose
header equals a field name/alias (`fold`). Every row is normalised + validated (format,
required, schema rules, master-data reference present in the DB **or** in the same file) and
kept in `idp.import_rows` for the preview, row list and error file. Submit writes the valid
rows as `ExtractedField`s (`row_index` = Excel row number, `document_page_id` = the sheet's
page) and sends the document to review — C5 always goes through a reviewer in M1.5.

Level-4 columns (salary, national id, …): a caller without level-4 access (02 §6.2) gets the
column dropped — not mapped, not stored, not in any prompt — plus the audit warning
`idp.warn.level4_dropped` (R-DEC-76).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.core.field_policy import Masked
from app.modules.idp.repositories import ImportRepository
from app.modules.idp.services.critical import is_critical
from app.modules.idp.services.import_parse import Sheet, too_large
from app.modules.idp.services.prompt_safety import fold

WARN_LEVEL4 = "idp.warn.level4_dropped"
PREVIEW_ROWS = 20
MAPPED_CONFIDENCE = 1.0  # exact header/alias match (heuristic tier)


@dataclass
class Column:
    index: int
    header: str
    key: str  # unique `column_mapping` key (header, de-duplicated)
    field: str | None
    confidence: float
    origin: str  # HEURISTIC | USER | DROPPED_LEVEL4 | NONE

    def as_json(self) -> dict[str, Any]:
        return {
            "index": self.index, "header": self.header, "key": self.key, "field": self.field,
            "confidence": self.confidence, "origin": self.origin,
        }  # fmt: skip


def column_keys(headers: list[str]) -> list[str]:
    keys: list[str] = []
    for i, h in enumerate(headers, start=1):
        key = h or f"#{i}"
        keys.append(key if key not in keys else f"{key} ({i})")
    return keys


def _aliases(spec: dict[str, Any]) -> set[str]:
    return {fold(a) for a in [spec["name"], *spec.get("header_aliases", [])] if a}


def level4_names(fields: list[dict[str, Any]]) -> set[str]:
    return {f["name"] for f in fields if int(f.get("sensitivity_level", 2)) >= 4}


def auto_map(headers: list[str], fields: list[dict[str, Any]], *, level4: bool) -> list[Column]:
    """Header ↔ field by exact folded name/alias; a field maps at most once (first column)."""
    taken: set[str] = set()
    hidden = level4_names(fields)
    cols: list[Column] = []
    for i, (header, key) in enumerate(zip(headers, column_keys(headers), strict=True), start=1):
        h = fold(header)
        spec = next((f for f in fields if h and h in _aliases(f) and f["name"] not in taken), None)
        if spec is None:
            cols.append(Column(i, header, key, None, 0.0, "NONE"))
        elif spec["name"] in hidden and not level4:
            cols.append(Column(i, header, key, None, 0.0, "DROPPED_LEVEL4"))
        else:
            taken.add(spec["name"])
            cols.append(Column(i, header, key, spec["name"], MAPPED_CONFIDENCE, "HEURISTIC"))
    return cols


def mask_values(values: dict[str, Any], hidden: set[str], level4: bool) -> dict[str, Any]:
    if level4:
        return dict(values)
    return {k: (Masked() if k in hidden else v) for k, v in values.items()}


def raw_of(cells: list[Any], cols: list[Column]) -> dict[str, Any]:
    """Original cells by column key — dropped level-4 columns are never stored."""
    from app.modules.idp.services.import_parse import json_cell

    return {c.key: json_cell(cells[c.index - 1]) for c in cols
            if c.origin != "DROPPED_LEVEL4" and c.index <= len(cells)
            and cells[c.index - 1] is not None}  # fmt: skip


def best_sheet(sheets: list[Sheet]) -> Sheet:
    """Default sheet = the first with data rows."""
    return next((s for s in sheets if s.data(s.header_row())), sheets[0])


# ---------------------------------------------------------------- row validation
_SELF_KEYS = frozenset({"code", "employee_code"})  # target param = natural key of its own ACT


def _creates_master(spec: dict[str, Any]) -> bool:
    target = spec.get("target") or {}
    return bool(spec.get("master_ref")) and target.get("param") in _SELF_KEYS


async def _master_exists(db: Any, ref: str, code: str) -> bool:
    if ref == "hr.department_code":
        from app.modules.hr.services.hr_service import HrService

        return await HrService(db).department_id_by_code(code) is not None
    if ref == "hr.employee_code":
        from app.modules.hr.services.hr_service import HrService

        return await HrService(db).employee_id_by_code(code) is not None
    if ref == "execution.kpi_code":
        from app.modules.execution.services.kpi_service import KpiService

        return await KpiService(db).kpi_id_by_code(code) is not None
    return True  # unknown reference kind: nothing to check against


@dataclass
class CheckedRow:
    row_number: int
    raw: dict[str, Any]
    values: dict[str, Any]
    errors: list[dict[str, Any]]


async def check_rows(
    db: Any, rows: list[tuple[int, list[Any]]], cols: list[Column],
    fields: list[dict[str, Any]], rules: list[dict[str, Any]],
) -> list[CheckedRow]:  # fmt: skip
    """Normalise + validate every row; master refs resolve against the DB or the same file."""
    from app.modules.idp.services.capture_common import normalize, required_errors, row_error
    from app.modules.idp.services.validator import Validator

    specs = {f["name"]: f for f in fields}
    out: list[CheckedRow] = []
    for number, cells in rows:
        values: dict[str, Any] = {}
        errors: list[dict[str, Any]] = []
        for c in cols:
            if c.field is None or c.index > len(cells):
                continue
            value, err = normalize(specs[c.field], cells[c.index - 1])
            if err is not None:
                errors.append(err)
            elif value is not None:
                values[c.field] = value
        errors += required_errors(fields, values, errors)
        for e in Validator(rules).validate(values).errors:
            errors.append(row_error(e["field"], e["rule"]))
        out.append(CheckedRow(number, raw_of(cells, cols), values, errors))
    await _check_masters(db, out, fields)
    return out


async def _check_masters(db: Any, rows: list[CheckedRow], fields: list[dict[str, Any]]) -> None:
    from app.modules.idp.services.capture_common import row_error

    in_file: dict[str, set[str]] = {}
    for f in fields:
        if _creates_master(f):
            in_file.setdefault(f["master_ref"], set()).update(
                str(r.values[f["name"]]) for r in rows if not r.errors and f["name"] in r.values
            )
    cache: dict[tuple[str, str], bool] = {}
    for f in fields:
        ref = f.get("master_ref")
        if not ref or _creates_master(f):
            continue
        for r in rows:
            code = r.values.get(f["name"])
            if code is None or str(code) in in_file.get(ref, set()):
                continue
            key = (ref, str(code))
            if key not in cache:
                cache[key] = await _master_exists(db, ref, str(code))
            if not cache[key]:
                r.errors.append(row_error(f["name"], "MASTER_NOT_FOUND", value=str(code)))


@dataclass
class UploadOutcome:
    preview: Any  # ImportPreviewOut, or None for a duplicate
    duplicate_of_id: Any = None
    document_id: Any = None


class ImportService:
    def __init__(self, db: Any, store: Any = None) -> None:
        from app.core.storage import get_object_store

        self.db = db
        self.store = store or get_object_store()

    # ------------------------------------------------------------- EP-DC-17
    async def upload(self, user: Any, f: Any, document_type: str | None) -> UploadOutcome:
        from app.core.config import get_config
        from app.core.errors import AppError
        from app.modules.idp.services.import_parse import CSV, XLSX, parse
        from app.modules.idp.services.scope import ensure_doc_type_scope
        from app.modules.idp.services.upload_service import store_stream

        ensure_doc_type_scope(user, document_type)  # R-DEC-76
        stored = store_stream(self.store, f, get_config().idp_max_file_size_mb)
        fake_xlsx = stored.mime == XLSX and not stored.prefix.startswith(b"PK\x03\x04")
        if stored.mime not in (XLSX, CSV) or fake_xlsx:  # .xls (OLE) / pdf / fake OOXML
            raise AppError("C5 import accepts one .xlsx or .csv file",
                           code="UNSUPPORTED_MEDIA_TYPE", status_code=415,
                           details={"filename": f.filename})  # fmt: skip
        original = await self._duplicate(stored.sha256)
        if original is not None:
            doc = self._new_doc(user, f.filename, stored, status="DUPLICATE")
            doc.duplicate_of_id = original.id
            doc.status_reason = "DUPLICATE_SHA256"
            self.db.add(doc)
            await self.db.flush()
            await self._audit(doc.id, "idp.import_upload", {"status": "DUPLICATE"})
            return UploadOutcome(None, original.id, doc.id)
        sheets = parse(self.store.open(stored.storage_key), stored.mime)
        return UploadOutcome(await self._create(user, f.filename, stored, sheets, document_type))

    async def _duplicate(self, digest: str) -> Any:
        from app.modules.idp.repositories import SourceDocumentRepository

        return await SourceDocumentRepository(self.db).first_original_by_sha(digest)

    def _new_doc(self, user: Any, filename: str | None, stored: Any, *, status: str) -> Any:
        from app.modules.idp.models import SourceDocument

        return SourceDocument(
            channel="C5", kind="FILE", original_filename=filename, mime_type=stored.mime,
            size_bytes=stored.size, storage_key=stored.storage_key, sha256=stored.sha256,
            scan_status="SKIPPED", pillars=[], status=status, sensitivity_level=2,
            source="IMPORT", data_classification="INTERNAL", submitted_by=user.user_id,
            submitted_at=datetime.now(UTC), department_id=user.department_id,
        )  # fmt: skip

    async def _audit(self, target_id: Any, action: str, after: dict[str, Any]) -> None:
        from app.core.audit import record_audit

        await record_audit(
            self.db, action=action, target_schema="idp", target_table="source_documents",
            target_id=target_id, after=after,
        )  # fmt: skip

    async def _create(
        self, user: Any, filename: str | None, stored: Any, sheets: list[Sheet],
        document_type: str | None,
    ) -> Any:  # fmt: skip
        from app.modules.idp.models import DocumentPage, ImportBatch
        from app.modules.idp.services.malware_scan import MalwareScanService

        scan = MalwareScanService(self.store).scan(stored.storage_key)
        if scan.status == "INFECTED":
            from app.core.errors import BusinessRuleError

            self.store.move(stored.storage_key, to_bucket="quarantine")
            raise BusinessRuleError("file rejected by malware scan", details={"reason": "malware"})
        doc = self._new_doc(user, filename, stored, status="VALIDATING")
        doc.scan_status = scan.status
        doc.page_count = len(sheets)
        self.db.add(doc)
        await self.db.flush()
        for s in sheets:  # one page per sheet → lineage `document_page_id` (R-DEC-64)
            self.db.add(DocumentPage(
                source_document_id=doc.id, page_number=s.index, sheet_name=s.name,
                text_layer_exists=True, ocr_used=False,
                text_content=None,  # rows live in import_rows (level-4 cells never in clear)
            ))  # fmt: skip
        batch = ImportBatch(
            kind="excel_import", title=filename, submitted_by=user.user_id, total_documents=1,
            status="open", source_document_id=doc.id,
        )  # fmt: skip
        self.db.add(batch)
        await self.db.flush()
        doc.import_batch_id = batch.id
        sheet = best_sheet(sheets)
        header_row = sheet.header_row()
        code, conf = await self._suggest(sheet.headers(header_row), document_type)
        batch.column_mapping = {"suggested": {"code": code, "confidence": conf}, "columns": []}
        if code is not None:
            await self._apply(user, batch, doc, sheets, code, sheet.name, header_row, None)
        await self.db.flush()
        await self._audit(doc.id, "idp.import_upload", {
            "batch_id": str(batch.id), "sheets": len(sheets), "document_type": code,
            "rows_total": batch.rows_total, "rows_invalid": batch.rows_invalid,
        })  # fmt: skip
        return await self.preview(user, batch.id, sheets=sheets)

    async def _suggest(self, headers: list[str], chosen: str | None) -> tuple[str | None, float]:
        """Preselected type wins (1.0); else header heuristic (R-DEC-65 tier 2, ≥ 60%)."""
        from app.modules.idp.services.classifier import Classifier

        if chosen:
            return chosen, 1.0
        res = await Classifier(self.db).classify("", headers=headers)
        if res.tier != "header":
            return None, 0.0
        return res.code, res.confidence

    async def _apply(
        self, user: Any, batch: Any, doc: Any, sheets: list[Sheet], code: str, sheet_name: str,
        header_row: int, mapping: dict[str, str | None] | None,
    ) -> None:  # fmt: skip
        """(Re)map + re-validate **every** row of `sheet_name`; replaces `import_rows`."""

        from app.core.config import get_config
        from app.core.errors import ValidationError as AppValidationError
        from app.core.field_policy import sees_level4
        from app.modules.idp.models import ImportRow
        from app.modules.idp.services.capture_common import published_schema

        pub = await published_schema(self.db, code)
        sheet = next((s for s in sheets if s.name == sheet_name), None)
        if sheet is None:
            raise AppValidationError("unknown sheet", details={"fields": ["sheet"]})
        fields, level4 = pub.fields, sees_level4(user)
        cols = auto_map(sheet.headers(header_row), fields, level4=level4)
        if mapping is not None:
            cols = self._override(cols, mapping, fields, level4)
            mapped = {c.field for c in cols if c.field}
            missing = [f["name"] for f in fields if f.get("required") and f["name"] not in mapped]
            if missing:
                raise AppValidationError("required field not mapped",
                                         details={"unmapped_required": missing})  # fmt: skip
        data = sheet.data(header_row)
        limit = get_config().idp_import_max_rows
        if len(data) > limit:  # exact data-row limit once the header row is known
            raise too_large("rows", limit)
        checked = await check_rows(self.db, data, cols, fields, pub.rules)
        new_rows = [
            ImportRow(import_batch_id=batch.id, row_number=r.row_number, raw=r.raw,
                      values=r.values, errors=r.errors,
                      status="invalid" if r.errors else "valid")
            for r in checked
        ]  # fmt: skip
        await ImportRepository(self.db).replace_rows(batch.id, new_rows)
        dropped = [c.header for c in cols if c.origin == "DROPPED_LEVEL4"]
        batch.column_mapping = {
            **(batch.column_mapping or {}),
            "columns": [c.as_json() for c in cols],
            "warnings": [{"code": WARN_LEVEL4, "columns": dropped}] if dropped else [],
        }
        batch.document_type_id, batch.sheet_name, batch.header_row = (
            pub.doc_type.id,
            sheet.name,
            header_row,
        )
        batch.rows_total = len(checked)
        batch.rows_invalid = sum(1 for r in checked if r.errors)
        batch.rows_valid = batch.rows_total - batch.rows_invalid
        doc.document_type_id = pub.doc_type.id
        doc.pillars = list(pub.doc_type.pillars or [])
        doc.sensitivity_level = pub.doc_type.sensitivity_level
        await self.db.flush()

    @staticmethod
    def _override(
        cols: list[Column], mapping: dict[str, str | None], fields: list[dict[str, Any]],
        level4: bool,
    ) -> list[Column]:  # fmt: skip
        from app.core.errors import ValidationError as AppValidationError

        names, hidden = {f["name"] for f in fields}, level4_names(fields)
        keys = {c.key for c in cols}
        bad = sorted(k for k, v in mapping.items() if k not in keys or (v and v not in names))
        if bad:
            raise AppValidationError("unknown column or field", details={"fields": bad})
        targets = [v for v in mapping.values() if v]
        if len(targets) != len(set(targets)):
            raise AppValidationError("field mapped twice", details={"fields": sorted(targets)})
        for c in cols:
            if c.key not in mapping:
                if c.field in targets:  # the user moved this field to another column
                    c.field, c.confidence, c.origin = None, 0.0, "NONE"
                continue
            want = mapping[c.key]
            if want in hidden and not level4:  # never mapped for a caller without level 4
                c.field, c.confidence, c.origin = None, 0.0, "DROPPED_LEVEL4"
            elif want != c.field:
                c.field, c.confidence, c.origin = (
                    want,
                    (1.0 if want else 0.0),
                    ("USER" if want else "NONE"),
                )
        return cols

    # ------------------------------------------------------------- EP-DC-18
    async def preview(self, user: Any, batch_id: Any, *, sheets: list[Sheet] | None = None) -> Any:

        from app.modules.idp.schemas.capture import (
            ColumnMappingOut,
            ImportPreviewOut,
            ImportSummaryOut,
            SuggestedTypeOut,
        )

        batch, doc = await self.visible_batch(user, batch_id)
        meta = batch.column_mapping or {}
        if sheets is not None:  # first preview: freeze the sheet summary (no re-parse on GET)
            meta = {**meta, "sheets": [self._sheet_json(s) for s in sheets]}
            batch.column_mapping = meta
            await self.db.flush()
        sug = meta.get("suggested") or {}
        rows = await ImportRepository(self.db).rows(batch.id, limit=PREVIEW_ROWS)
        hidden, level4 = await self._hidden(batch), self._level4(user)
        return ImportPreviewOut(
            batch_id=batch.id, document_id=doc.id, sheets=meta.get("sheets", []),
            suggested_document_type=SuggestedTypeOut(**sug) if sug.get("code") else None,
            column_mapping={c["key"]: ColumnMappingOut(field=c["field"], confidence=c["confidence"])
                            for c in meta.get("columns", [])},
            preview_rows=[{"row_number": r.row_number,
                           "values": mask_values(r.values or {}, hidden, level4),
                           "errors": r.errors} for r in rows],
            summary=ImportSummaryOut(rows_total=batch.rows_total, rows_valid=batch.rows_valid,
                                     rows_invalid=batch.rows_invalid),
            version=batch.version,
        )  # fmt: skip

    @staticmethod
    def _sheet_json(s: Sheet) -> dict[str, Any]:
        hr = s.header_row()
        headers = s.headers(hr)
        return {"name": s.name, "row_count": len(s.data(hr)), "header_row": hr,
                "columns": [{"index": i, "header": h or None}
                            for i, h in enumerate(headers, start=1)]}  # fmt: skip

    @staticmethod
    def _level4(user: Any) -> bool:
        from app.core.field_policy import sees_level4

        return sees_level4(user)

    async def _hidden(self, batch: Any) -> set[str]:
        from app.modules.idp.services.capture_common import published_schema, type_code

        code = await type_code(self.db, batch.document_type_id)
        return level4_names((await published_schema(self.db, code)).fields) if code else set()

    async def visible_batch(self, user: Any, batch_id: Any) -> tuple[Any, Any]:
        """C5 batch + its document, both in the caller's idp scope — else `404`."""

        from app.core.errors import NotFoundError
        from app.modules.idp.repositories import SourceDocumentRepository
        from app.modules.idp.services.scope import capture_visible

        batch = await ImportRepository(self.db).excel_batch(batch_id)
        doc = None
        if batch is not None and batch.source_document_id is not None:
            doc = await SourceDocumentRepository(self.db).by_id(batch.source_document_id)
        if doc is None or not await capture_visible(self.db, user, doc):
            raise NotFoundError("import batch not found")
        return batch, doc

    async def _writable(self, user: Any, batch_id: Any, version: int) -> tuple[Any, Any]:
        """Submitter only; document still `VALIDATING`; optimistic lock on `batch.version`."""
        from app.core.errors import ConflictStateError, PermissionDeniedError

        batch, doc = await self.visible_batch(user, batch_id)
        if doc.submitted_by != user.user_id:
            raise PermissionDeniedError("only the submitter may change this import",
                                        details={"rule": "submitter_only"})  # fmt: skip
        if doc.status != "VALIDATING":
            raise ConflictStateError("import already submitted", details={"status": doc.status})
        if batch.version != version:
            raise ConflictStateError("import was modified", details={"version": batch.version})
        return batch, doc

    # ------------------------------------------------------------- EP-DC-19
    async def update_mapping(self, user: Any, batch_id: Any, body: Any) -> Any:
        from app.modules.idp.services.import_parse import parse
        from app.modules.idp.services.scope import ensure_doc_type_scope

        ensure_doc_type_scope(user, body.document_type)  # R-DEC-76
        batch, doc = await self._writable(user, batch_id, body.version)
        sheets = parse(self.store.open(doc.storage_key), doc.mime_type or "")
        await self._apply(user, batch, doc, sheets, body.document_type, body.sheet,
                          body.header_row, body.mapping)  # fmt: skip
        batch.version += 1
        await self.db.flush()
        await self._audit(doc.id, "idp.import_mapping_update", {
            "batch_id": str(batch.id), "document_type": body.document_type, "sheet": body.sheet,
            "header_row": body.header_row, "rows_invalid": batch.rows_invalid,
        })  # fmt: skip
        return await self.preview(user, batch.id)

    # ------------------------------------------------------------- EP-DC-20
    async def rows(self, user: Any, batch_id: Any, status: str, limit: int, offset: int,
                   order: str) -> tuple[list[Any], int]:  # fmt: skip

        from app.modules.idp.schemas.capture import ImportRowOut

        batch, _ = await self.visible_batch(user, batch_id)
        repo = ImportRepository(self.db)
        total = await repo.count_rows(batch.id, status)
        found = await repo.rows(batch.id, status=status, limit=limit, offset=offset,
                                desc=order != "asc")  # fmt: skip
        hidden, level4 = await self._hidden(batch), self._level4(user)
        items = [ImportRowOut(row_number=r.row_number,
                              values=mask_values(r.values or {}, hidden, level4),
                              errors=r.errors or []) for r in found]  # fmt: skip
        return items, int(total)

    # ------------------------------------------------------------- EP-DC-21
    async def error_file(self, user: Any, batch_id: Any) -> bytes:

        from app.core.errors import NotFoundError
        from app.modules.idp.services.import_parse import write_error_file

        batch, _ = await self.visible_batch(user, batch_id)
        bad = await ImportRepository(self.db).rows(batch.id, status="invalid")
        if not bad:
            raise NotFoundError("no error rows")
        cols = (batch.column_mapping or {}).get("columns", [])
        hidden, level4 = await self._hidden(batch), self._level4(user)
        keep = [c for c in cols if c["origin"] != "DROPPED_LEVEL4"
                and (level4 or c["field"] not in hidden)]  # fmt: skip
        rows = [[(r.raw or {}).get(c["key"]) for c in keep] + [_error_text(r.errors)]
                for r in bad]  # fmt: skip
        return write_error_file([c["header"] for c in keep], rows)

    # ------------------------------------------------------------- EP-DC-22
    async def submit(self, user: Any, batch_id: Any, version: int) -> Any:

        from app.core.errors import BusinessRuleError
        from app.modules.idp.schemas.capture import ImportSubmitOut
        from app.modules.idp.services.capture_common import (
            assign_initial_review,
            document_out,
            type_code,
        )

        batch, doc = await self._writable(user, batch_id, version)
        code = await type_code(self.db, batch.document_type_id)
        if code is None or batch.rows_valid == 0:
            raise BusinessRuleError("no valid rows to submit", details={"reason": "no_valid_rows"})
        valid = await ImportRepository(self.db).rows(batch.id, status="valid")
        await self._write_fields(batch, doc, code, list(valid))
        doc.status = "NEEDS_REVIEW"
        doc.routing_reason = "C5_REVIEW"  # R-DEC-62: C5 always reviewed in M1.5
        doc.row_count = len(valid)
        doc.classification_confidence = (batch.column_mapping or {}).get(
            "suggested", {}).get("confidence") or 1  # fmt: skip
        batch.status = "processing"
        batch.version += 1
        await self.db.flush()
        await assign_initial_review(self.db, doc)
        await self._audit(doc.id, "idp.import_submit", {
            "batch_id": str(batch.id), "rows_submitted": len(valid),
            "rows_excluded": batch.rows_invalid,
        })  # fmt: skip
        return ImportSubmitOut(document=document_out(doc, code), rows_submitted=len(valid),
                               rows_excluded=batch.rows_invalid)  # fmt: skip

    async def _write_fields(self, batch: Any, doc: Any, code: str, valid: list[Any]) -> None:
        """One `ExtractionJob` + `ExtractedField` per mapped cell of each valid row."""
        from sqlalchemy import select

        from app.modules.idp.models import DocumentPage, ExtractedField, ExtractionJob
        from app.modules.idp.services.capture_common import classification_of, published_schema
        from app.modules.idp.services.extractor import confidence_band

        pub = await published_schema(self.db, code)
        specs = {f["name"]: f for f in pub.fields}
        page_id = (await self.db.execute(select(DocumentPage.id).where(
            DocumentPage.source_document_id == doc.id,
            DocumentPage.sheet_name == batch.sheet_name,
        ))).scalar_one_or_none()  # fmt: skip
        cols = {c["field"]: c for c in (batch.column_mapping or {}).get("columns", [])
                if c["field"]}  # fmt: skip
        now = datetime.now(UTC)
        job = ExtractionJob(
            source_document_id=doc.id, extraction_schema_id=pub.schema.id, attempt_no=1,
            status="SUCCEEDED", document_confidence=1, routing_decision="REVIEW",
            routing_reasons=["C5_REVIEW"], xd_results={"validation_errors": []},
            started_at=now, finished_at=now,
        )  # fmt: skip
        self.db.add(job)
        await self.db.flush()
        for r in valid:
            for name, value in (r.values or {}).items():
                spec, col = specs.get(name), cols.get(name)
                if spec is None or col is None:
                    continue
                level = int(spec.get("sensitivity_level", 2))
                conf = float(col["confidence"])
                self.db.add(ExtractedField(
                    extraction_job_id=job.id, document_page_id=page_id, field_name=name,
                    row_index=r.row_number, value_type=spec.get("value_type", "text"),
                    value=value, raw_text=None if level >= 4 else str((r.raw or {}).get(
                        col["key"], value)),
                    confidence=conf, confidence_band=confidence_band(conf),
                    is_critical=is_critical(spec), sensitivity_level=level,
                    source_location={"kind": "cell", "sheet": batch.sheet_name,
                                     "row": r.row_number, "column": col["index"],
                                     "header": col["header"]},
                    validation=[], source="IMPORT", data_classification=classification_of(level),
                ))  # fmt: skip
        await self.db.flush()


def _error_text(errors: list[dict[str, Any]]) -> str:
    return "; ".join(f"{e.get('field') or '-'}: {e.get('rule_code')}" for e in errors or [])

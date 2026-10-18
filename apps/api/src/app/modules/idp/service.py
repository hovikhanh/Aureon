"""IDP business logic and file upload handling service (T-203).

Implements file validation, streaming SHA-256 calculation, deduplication, MinIO storage,
and audit logging per 04-IDP-FEATURE-SPEC.md and 10-API-SPECIFICATION.md.
"""

import csv
import hashlib
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.core.errors import ApiError, ErrorCode
from app.core.storage import get_storage_service
from app.db.enums import ActorType
from app.modules.audit.service import record_audit
from app.modules.auth.models import User
from app.modules.idp.enums import (
    AutonomyLevel,
    DocType,
    DocumentKind,
    DocumentStatus,
    FieldValueType,
    InputChannel,
    JobStatus,
    RoutingDecision,
    SensitivityLabel,
    SourceLocationKind,
)
from app.modules.idp.models import ExtractedField, ExtractionJob, SourceDocument
from app.modules.idp.schemas import (
    ColumnConfirmItem,
    ColumnMappingSuggestionItem,
    MappingSuggestion,
    RowErrorItem,
)

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB (04 §14 IDP-E01)
MAX_PDF_PAGES = 50  # 50 pages (04 §14 IDP-E01)
CHUNK_SIZE = 1024 * 1024  # 1 MB stream chunk

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".csv",
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
}

DOC_TYPE_PILLARS: dict[DocType, list[str]] = {
    DocType.FINANCIAL_REPORT: ["FIN"],
    DocType.INVOICE: ["FIN"],
    DocType.SALES_REPORT: ["CUS"],
    DocType.CONTRACT: ["CUS"],
    DocType.MEETING_MINUTES: ["OPS"],
    DocType.KPI_OKR: ["OPS"],
    DocType.EMPLOYEE_LIST: ["HR"],
    DocType.OTHER: ["FIN", "CUS", "OPS", "HR"],
}


def count_pdf_pages(data: bytes) -> int:
    """Count pages in a PDF byte buffer."""
    match = re.search(rb"/Type\s*/Pages.*?/Count\s+(\d+)", data, re.DOTALL)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    # Count occurrences of /Type /Page (not /Type /Pages)
    pages = len(re.findall(rb"/Type\s*/Page\b(?!s)", data))
    return max(1, pages)


async def process_upload_stream(
    upload_file: UploadFile,
) -> tuple[bytes, str, int, int]:
    """Read upload stream, validate size and format, and compute SHA-256 hash.

    Returns:
        (file_bytes, sha256_hex, size_bytes, page_count)
    """
    filename = upload_file.filename or "unknown"
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        allowed_list = sorted(ALLOWED_EXTENSIONS)
        raise ApiError(
            ErrorCode.UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file format '{ext}'. Allowed: {allowed_list}",
        )

    hasher = hashlib.sha256()
    chunks: list[bytes] = []
    total_bytes = 0

    while True:
        chunk = await upload_file.read(CHUNK_SIZE)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > MAX_FILE_SIZE_BYTES:
            raise ApiError(
                ErrorCode.FILE_TOO_LARGE,
                f"File size exceeds 20MB limit (read {total_bytes} bytes)",
            )
        hasher.update(chunk)
        chunks.append(chunk)

    file_bytes = b"".join(chunks)
    sha256_hex = hasher.hexdigest()

    page_count = 1
    if ext == ".pdf":
        page_count = count_pdf_pages(file_bytes)
        if page_count > MAX_PDF_PAGES:
            raise ApiError(
                ErrorCode.FILE_TOO_LARGE,
                f"PDF exceeds maximum of 50 pages (detected {page_count} pages)",
            )

    return file_bytes, sha256_hex, total_bytes, page_count


def handle_document_upload(
    db: Session,
    current_user: User,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    size_bytes: int,
    page_count: int,
    sha256_hex: str,
    channel: InputChannel,
    doc_type_hint: DocType | None = None,
    batch_id: UUID | None = None,
) -> tuple[SourceDocument, bool, UUID | None]:
    """Store file, check SHA-256 deduplication, create SourceDocument, and record audit.

    Returns:
        (document, is_duplicate, duplicate_of_id)
    """
    storage = get_storage_service()
    doc_id = uuid4()

    # Determine storage key: docs/{year}/{doc_id}/{filename}
    year = datetime.now(UTC).strftime("%Y")
    clean_filename = Path(filename).name.replace(" ", "_")
    storage_key = f"docs/{year}/{doc_id}/{clean_filename}"

    # Check duplicate SHA-256 (04 §8.2, FR-DC-06)
    stmt = select(SourceDocument).where(
        SourceDocument.sha256 == sha256_hex,
        SourceDocument.deleted_at.is_(None),
    )
    existing = db.execute(stmt).scalars().first()

    is_duplicate = existing is not None
    duplicate_of_id = existing.id if existing else None
    doc_status = DocumentStatus.DUPLICATE if is_duplicate else DocumentStatus.UPLOADED

    # Upload to MinIO
    content_type = mime_type or "application/octet-stream"
    storage.put_object(storage_key, file_bytes, content_type=content_type)

    pillars = DOC_TYPE_PILLARS.get(doc_type_hint, ["FIN"]) if doc_type_hint else ["FIN"]
    contains_salary = doc_type_hint == DocType.EMPLOYEE_LIST

    doc = SourceDocument(
        id=doc_id,
        batch_id=batch_id,
        channel=channel,
        kind=DocumentKind.FILE,
        original_filename=filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        page_count=page_count,
        storage_key=storage_key,
        sha256=sha256_hex,
        duplicate_of_id=duplicate_of_id,
        doc_type=doc_type_hint,
        pillars=pillars,
        status=doc_status,
        autonomy_level=AutonomyLevel.L2,
        contains_salary=contains_salary,
        contains_pii=False,
        uploaded_by_id=current_user.id,
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    db.flush()

    # Record audit log
    action = "document.upload_duplicate" if is_duplicate else "document.upload"
    record_audit(
        db=db,
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        actor_role_id=current_user.role_id,
        action=action,
        target_type="source_documents",
        target_id=doc.id,
        source_document_id=doc.id,
        after={
            "id": str(doc.id),
            "filename": filename,
            "sha256": sha256_hex,
            "status": doc_status.value,
            "duplicate_of_id": str(duplicate_of_id) if duplicate_of_id else None,
            "batch_id": str(batch_id) if batch_id else None,
        },
    )

    db.commit()
    db.refresh(doc)
    return doc, is_duplicate, duplicate_of_id


def validate_tax_code(tax_code: str) -> bool:
    """Validate Vietnamese tax code format: 10 or 13 digits (TC-IDP-004, 04 §13)."""
    clean = tax_code.strip()
    return bool(re.match(r"^\d{10}(-\d{3}|\d{3})?$", clean))


def infer_field_value_type(field_key: str, value: Any) -> FieldValueType:
    """Infer FieldValueType from field name and Python value type."""
    key = field_key.lower()
    if "tax_code" in key:
        return FieldValueType.TAX_CODE
    if "date" in key or key.endswith("_at"):
        return FieldValueType.DATE
    if any(m in key for m in ("amount", "subtotal", "vat", "cogs", "revenue", "profit", "salary")):
        return FieldValueType.MONEY
    if "rate" in key or "percent" in key:
        return FieldValueType.PERCENT
    if "period" in key:
        return FieldValueType.PERIOD
    if isinstance(value, int | float):
        return FieldValueType.NUMBER
    return FieldValueType.TEXT


def handle_manual_document_create(
    db: Session,
    current_user: User,
    doc_type: DocType,
    fields: dict[str, Any],
    batch_id: UUID | None = None,
) -> SourceDocument:
    """EP-21: Create manual document (C1 form), validate fields and create extracted fields."""
    # Validate Tax Code fields if present
    validation_errors: list[dict[str, str]] = []
    for k, v in fields.items():
        if ("tax_code" in k.lower() or k == "tax_code") and isinstance(v, str):
            if not validate_tax_code(v):
                validation_errors.append(
                    {
                        "field": k,
                        "message": f"Mã số thuế '{v}' không hợp lệ (phải có 10 hoặc 13 số)",
                    }
                )

    if validation_errors:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            "Validation failed on manual input fields",
            details={"fields": validation_errors},
        )

    doc_id = uuid4()
    pillars = DOC_TYPE_PILLARS.get(doc_type, ["FIN"])
    contains_salary = doc_type == DocType.EMPLOYEE_LIST

    doc = SourceDocument(
        id=doc_id,
        batch_id=batch_id,
        channel=InputChannel.C1,
        kind=DocumentKind.MANUAL,
        doc_type=doc_type,
        pillars=pillars,
        status=DocumentStatus.NEEDS_REVIEW,
        autonomy_level=AutonomyLevel.L1,
        contains_salary=contains_salary,
        manual_payload=fields,
        uploaded_by_id=current_user.id,
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    db.flush()

    job = ExtractionJob(
        source_document_id=doc.id,
        attempt_no=1,
        doc_type=doc_type,
        status=JobStatus.SUCCEEDED,
        routing_decision=RoutingDecision.REVIEW,
        routing_reason="C1 manual entry requires review verification",
        avg_confidence=1.0,
    )
    db.add(job)
    db.flush()

    # Create ExtractedField rows with confidence 1.0 and source_location.kind = manual
    for key, val in fields.items():
        vtype = infer_field_value_type(key, val)
        sensitivity = SensitivityLabel.SALARY if "salary" in key.lower() else SensitivityLabel.NONE
        extracted_f = ExtractedField(
            extraction_job_id=job.id,
            source_document_id=doc.id,
            field_key=key,
            value=val,
            raw_text=str(val),
            value_type=vtype,
            confidence=1.0,
            source_location={"kind": "manual"},
            source_kind=SourceLocationKind.MANUAL,
            sensitivity=sensitivity,
        )
        db.add(extracted_f)

    # Record audit log
    record_audit(
        db=db,
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        actor_role_id=current_user.role_id,
        action="document.manual_create",
        target_type="source_documents",
        target_id=doc.id,
        source_document_id=doc.id,
        after={
            "id": str(doc.id),
            "doc_type": doc_type.value,
            "channel": InputChannel.C1.value,
            "fields": fields,
        },
    )

    db.commit()
    db.refresh(doc)
    return doc


def handle_natural_language_create(
    db: Session,
    current_user: User,
    text: str,
    batch_id: UUID | None = None,
) -> SourceDocument:
    """EP-22: Parse natural language prompt, create TRANSCRIPT document at L2, never STP."""
    cfg = get_config()
    if cfg.ai_kill_switch:
        raise ApiError(
            ErrorCode.AI_DISABLED,
            "AI processing is currently disabled via kill switch (L0)",
        )

    doc_id = uuid4()
    doc = SourceDocument(
        id=doc_id,
        batch_id=batch_id,
        channel=InputChannel.C2,
        kind=DocumentKind.TRANSCRIPT,
        doc_type=DocType.INVOICE,  # Default or classified
        pillars=["FIN"],
        status=DocumentStatus.NEEDS_REVIEW,
        autonomy_level=AutonomyLevel.L2,  # AI-drafted, requires human confirmation (US-DC-003)
        manual_payload={"prompt_text": text},
        uploaded_by_id=current_user.id,
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    db.flush()

    job = ExtractionJob(
        source_document_id=doc.id,
        attempt_no=1,
        doc_type=DocType.INVOICE,
        status=JobStatus.SUCCEEDED,
        routing_decision=RoutingDecision.REVIEW,
        routing_reason="C2 transcript input is never STP (04 S6)",
        avg_confidence=0.85,
    )
    db.add(job)
    db.flush()

    # Draft extraction from prompt (TC-IDP-005: "Hóa đơn 0001234 ... 25 triệu ngày 05/10/2026")
    extracted_items: list[tuple[str, Any, FieldValueType]] = []

    # Extract invoice number
    inv_match = re.search(r"(?:hóa\s*đơn|hd)\s*([0-9a-zA-Z\-_]+)", text, re.IGNORECASE)
    if inv_match:
        extracted_items.append(("invoice_number", inv_match.group(1), FieldValueType.TEXT))

    # Extract amount (e.g., "25 triệu" -> 25,000,000)
    amount_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:triệu|tr|trieu)", text, re.IGNORECASE)
    if amount_match:
        val_str = amount_match.group(1).replace(",", ".")
        val_int = int(float(val_str) * 1_000_000)
        extracted_items.append(("total_amount", val_int, FieldValueType.MONEY))

    # Extract date (e.g., "05/10/2026")
    date_match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    if date_match:
        extracted_items.append(("issue_date", date_match.group(1), FieldValueType.DATE))

    # Fallback default field if none matched
    if not extracted_items:
        extracted_items.append(("raw_prompt", text, FieldValueType.TEXT))

    for k, val, vtype in extracted_items:
        field = ExtractedField(
            extraction_job_id=job.id,
            source_document_id=doc.id,
            field_key=k,
            value=val,
            raw_text=str(val),
            value_type=vtype,
            confidence=0.85,
            source_location={"kind": "transcript", "text": text},
            source_kind=SourceLocationKind.TRANSCRIPT,
            sensitivity=SensitivityLabel.NONE,
        )
        db.add(field)

    # Record audit log
    record_audit(
        db=db,
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        actor_role_id=current_user.role_id,
        action="document.nl_create",
        target_type="source_documents",
        target_id=doc.id,
        source_document_id=doc.id,
        after={
            "id": str(doc.id),
            "channel": InputChannel.C2.value,
            "prompt_text": text,
        },
    )

    db.commit()
    db.refresh(doc)
    return doc


HEADER_MAPPINGS: dict[str, tuple[str, float]] = {
    "stt": ("stt", 0.90),
    "số hđ": ("invoice_number", 0.98),
    "số hóa đơn": ("invoice_number", 0.98),
    "so hd": ("invoice_number", 0.95),
    "so hoa don": ("invoice_number", 0.95),
    "invoice_number": ("invoice_number", 0.99),
    "invoice_no": ("invoice_number", 0.99),
    "ngày": ("issue_date", 0.95),
    "ngay": ("issue_date", 0.95),
    "ngày hđ": ("issue_date", 0.98),
    "ngày xuất": ("issue_date", 0.98),
    "issue_date": ("issue_date", 0.99),
    "khách hàng": ("customer_name", 0.98),
    "tên khách hàng": ("customer_name", 0.98),
    "khach hang": ("customer_name", 0.95),
    "customer": ("customer_name", 0.99),
    "customer_name": ("customer_name", 0.99),
    "mst khách": ("customer_tax_code", 0.98),
    "mst": ("customer_tax_code", 0.95),
    "mã số thuế": ("customer_tax_code", 0.98),
    "tax_code": ("customer_tax_code", 0.99),
    "subtotal (vnd)": ("subtotal", 0.98),
    "subtotal": ("subtotal", 0.99),
    "tiền trước thuế": ("subtotal", 0.98),
    "thành tiền": ("subtotal", 0.95),
    "vat %": ("vat_rate", 0.98),
    "vat": ("vat_rate", 0.90),
    "thuế suất": ("vat_rate", 0.98),
    "vat_rate": ("vat_rate", 0.99),
    "đã thu (vnd)": ("paid_amount", 0.98),
    "đã thu": ("paid_amount", 0.98),
    "da thu": ("paid_amount", 0.95),
    "paid_amount": ("paid_amount", 0.99),
    "hạn tt": ("due_date", 0.98),
    "hạn thanh toán": ("due_date", 0.98),
    "han tt": ("due_date", 0.95),
    "due_date": ("due_date", 0.99),
    "trạng thái": ("status", 0.95),
    "trang thai": ("status", 0.90),
    "status": ("status", 0.99),
}


def index_to_col_letter(col_idx: int) -> str:
    """Convert 0-based column index to Excel column letter (0 -> A, 25 -> Z, 26 -> AA)."""
    result = ""
    col_idx += 1
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result = chr(65 + remainder) + result
    return result


def col_letter_to_index(col_letter: str) -> int:
    """Convert Excel column letter to 0-based column index (A -> 0, Z -> 25, AA -> 26)."""
    result = 0
    for char in col_letter.upper():
        if "A" <= char <= "Z":
            result = result * 26 + (ord(char) - ord("A") + 1)
    return result - 1


def parse_spreadsheet_rows(file_bytes: bytes, filename: str) -> tuple[str, list[list[str]]]:
    """Parse XLSX or CSV bytes into list of row values."""
    ext = Path(filename).suffix.lower()
    if ext == ".csv":
        text = ""
        for enc in ("utf-8-sig", "utf-8", "latin1"):
            try:
                text = file_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        reader = csv.reader(io.StringIO(text))
        rows = [row for row in reader if any(cell.strip() for cell in row)]
        return "Sheet1", rows

    if ext == ".xlsx":
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                shared_strings: list[str] = []
                if "xl/sharedStrings.xml" in zf.namelist():
                    tree = ET.fromstring(zf.read("xl/sharedStrings.xml"))  # noqa: S314 -- internal xlsx parsing without entity resolution (DEC-051)
                    for si in tree.findall(
                        ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"
                    ) or tree.findall(".//si"):
                        t_elems = si.findall(
                            ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
                        ) or si.findall(".//t")
                        shared_strings.append("".join(t.text or "" for t in t_elems))

                sheet_path = "xl/worksheets/sheet1.xml"
                if sheet_path not in zf.namelist():
                    for name in zf.namelist():
                        if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                            sheet_path = name
                            break

                tree = ET.fromstring(zf.read(sheet_path))  # noqa: S314 -- internal xlsx parsing without entity resolution (DEC-051)
                ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                rows_data: list[list[str]] = []
                for row_elem in tree.findall(f".//{ns}row") or tree.findall(".//row"):
                    row_cells: dict[int, str] = {}
                    max_col = -1
                    cells = row_elem.findall(f".//{ns}c") or row_elem.findall(".//c")
                    for c in cells:
                        ref = c.get("r", "")
                        match = re.match(r"([A-Za-z]+)(\d+)", ref)
                        col_idx = col_letter_to_index(match.group(1)) if match else len(row_cells)
                        max_col = max(max_col, col_idx)

                        t = c.get("t")
                        v_elem = c.find(f"{ns}v")
                        if v_elem is None:
                            v_elem = c.find("v")
                        val = ""
                        if v_elem is not None and v_elem.text:
                            if t == "s":
                                idx = int(v_elem.text)
                                val = shared_strings[idx] if idx < len(shared_strings) else ""
                            else:
                                val = v_elem.text
                        elif t == "inlineStr":
                            is_elem = c.find(f".//{ns}t")
                            if is_elem is None:
                                is_elem = c.find(".//t")
                            if is_elem is not None and is_elem.text:
                                val = is_elem.text
                        row_cells[col_idx] = val.strip()

                    if max_col >= 0:
                        row_list = [row_cells.get(i, "") for i in range(max_col + 1)]
                        if any(row_list):
                            rows_data.append(row_list)
                return "Sheet1", rows_data
        except Exception as exc:
            raise ApiError(
                ErrorCode.UNSUPPORTED_MEDIA_TYPE,
                f"Corrupted or invalid Excel file: {exc}",
            ) from exc

    raise ApiError(
        ErrorCode.UNSUPPORTED_MEDIA_TYPE,
        f"File format '{ext}' is not supported for import",
    )


def generate_mapping_suggestion(
    headers: list[str], sheet_name: str = "Sheet1"
) -> MappingSuggestion:
    """Generate AI / rule-based column mapping suggestions for import file headers."""
    items: list[ColumnMappingSuggestionItem] = []
    for idx, header in enumerate(headers):
        col_letter = index_to_col_letter(idx)
        clean_hdr = header.strip().lower()
        suggested_key, confidence = HEADER_MAPPINGS.get(clean_hdr, (None, 0.0))
        if not suggested_key:
            # Partial match check
            for pattern, (key, conf) in HEADER_MAPPINGS.items():
                if pattern in clean_hdr or clean_hdr in pattern:
                    suggested_key, confidence = key, conf * 0.95
                    break
        items.append(
            ColumnMappingSuggestionItem(
                column=col_letter,
                header=header.strip(),
                suggested_field_key=suggested_key,
                confidence=confidence,
            )
        )
    return MappingSuggestion(sheet_name=sheet_name, header_row=1, columns=items)


def handle_spreadsheet_upload(
    db: Session,
    current_user: User,
    file_bytes: bytes,
    filename: str,
    doc_type_hint: DocType | None = None,
    batch_id: UUID | None = None,
) -> tuple[SourceDocument, MappingSuggestion]:
    """EP-23: Upload XLSX/CSV file, validate line count <= 5000, generate mapping suggestion."""
    ext = Path(filename).suffix.lower()
    if ext not in (".xlsx", ".csv"):
        raise ApiError(
            ErrorCode.UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported spreadsheet format '{ext}'. Allowed: ['.xlsx', '.csv']",
        )

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ApiError(ErrorCode.FILE_TOO_LARGE, "File size exceeds 20MB limit")

    sheet_name, rows = parse_spreadsheet_rows(file_bytes, filename)
    if not rows:
        raise ApiError(ErrorCode.VALIDATION_ERROR, "Spreadsheet is empty or has no readable rows")

    headers = rows[0]
    data_rows = rows[1:]

    # Rule: <= 5,000 data rows (IDP-E11, 10 §4 EP-23)
    if len(data_rows) > 5000:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            f"Spreadsheet exceeds maximum of 5,000 rows (got {len(data_rows)} rows)",
            details={"actual_rows": len(data_rows), "max_rows": 5000},
        )

    mapping_suggestion = generate_mapping_suggestion(headers, sheet_name=sheet_name)

    doc_id = uuid4()
    storage_key = f"documents/{doc_id}/{filename}"
    storage = get_storage_service()
    content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if ext == ".xlsx"
        else "text/csv"
    )
    storage.put_object(storage_key, file_bytes, content_type=content_type)

    hasher = hashlib.sha256()
    hasher.update(file_bytes)
    sha256_hex = hasher.hexdigest()

    doc_type = doc_type_hint or DocType.INVOICE
    pillars = DOC_TYPE_PILLARS.get(doc_type, ["FIN"])

    doc = SourceDocument(
        id=doc_id,
        batch_id=batch_id,
        channel=InputChannel.C5,
        kind=DocumentKind.FILE,
        original_filename=filename,
        mime_type=content_type,
        size_bytes=len(file_bytes),
        page_count=1,
        storage_key=storage_key,
        sha256=sha256_hex,
        doc_type=doc_type,
        pillars=pillars,
        status=DocumentStatus.UPLOADED,
        autonomy_level=AutonomyLevel.L1,
        uploaded_by_id=current_user.id,
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    db.flush()

    # Record audit log
    record_audit(
        db=db,
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        actor_role_id=current_user.role_id,
        action="document.import_upload",
        target_type="source_documents",
        target_id=doc.id,
        source_document_id=doc.id,
        after={
            "id": str(doc.id),
            "filename": filename,
            "row_count": len(data_rows),
            "channel": InputChannel.C5.value,
        },
    )

    db.commit()
    db.refresh(doc)
    return doc, mapping_suggestion


def handle_import_mapping_confirm(
    db: Session,
    current_user: User,
    doc_id: UUID,
    doc_type: DocType,
    columns: list[ColumnConfirmItem],
) -> tuple[SourceDocument, list[RowErrorItem]]:
    """EP-36: Confirm column mapping and extract fields per row.

    Record row errors without blocking valid rows (IDP-E11).
    """
    doc = db.get(SourceDocument, doc_id)
    if not doc or doc.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, "Document not found")

    # Only uploader can confirm mapping (10 §4 EP-36, TC-IDP-007)
    if doc.uploaded_by_id != current_user.id:
        raise ApiError(
            ErrorCode.FORBIDDEN_SCOPE,
            "Only the user who uploaded the document can confirm column mapping",
        )

    if doc.status not in (DocumentStatus.UPLOADED, DocumentStatus.PREPROCESSING):
        raise ApiError(
            ErrorCode.CONFLICT_STATE,
            f"Cannot confirm mapping for document in status {doc.status.value}",
        )

    if not doc.storage_key:
        raise ApiError(ErrorCode.CONFLICT_STATE, "Document has no storage file to parse")

    storage = get_storage_service()
    file_bytes = storage.get_object(doc.storage_key)
    sheet_name, rows = parse_spreadsheet_rows(file_bytes, doc.original_filename or "data.xlsx")

    data_rows = rows[1:]  # Skip header row

    # Build mapping: col_index -> field_key
    col_mapping: dict[int, str] = {}
    for item in columns:
        col_idx = col_letter_to_index(item.column)
        col_mapping[col_idx] = item.field_key

    job = ExtractionJob(
        source_document_id=doc.id,
        attempt_no=1,
        doc_type=doc_type,
        status=JobStatus.SUCCEEDED,
        routing_decision=RoutingDecision.REVIEW,
        routing_reason="C5 bulk import requires review queue verification",
        avg_confidence=0.95,
    )
    db.add(job)
    db.flush()

    row_errors: list[RowErrorItem] = []

    # 1-based index: header is row 1, data starts at row 2
    for row_idx, row_data in enumerate(data_rows, start=2):
        # Check validation on row
        row_has_error = False
        row_fields: list[tuple[str, Any, str, int]] = []  # (field_key, value, raw_text, col_idx)

        for col_idx, field_key in col_mapping.items():
            raw_val = row_data[col_idx] if col_idx < len(row_data) else ""
            clean_val = raw_val.strip()

            # Format validation per field
            if "tax_code" in field_key.lower() and clean_val:
                if not validate_tax_code(clean_val):
                    row_errors.append(
                        RowErrorItem(
                            row_index=row_idx,
                            field_key=field_key,
                            code="INVALID_TAX_CODE",
                            message=f"Mã số thuế '{clean_val}' không đúng định dạng",
                        )
                    )
                    row_has_error = True

            # Convert numeric/date values if possible
            val: Any = clean_val
            if any(
                m in field_key.lower() for m in ("subtotal", "amount", "vat_amount", "paid_amount")
            ):
                try:
                    num_str = clean_val.replace(".", "").replace(",", "")
                    if num_str:
                        val = int(num_str)
                except ValueError:
                    pass

            row_fields.append((field_key, val, clean_val, col_idx))

        # IDP-E11: Row errors do not block valid rows or valid fields
        if not row_has_error:
            for field_key, val, raw_val, col_idx in row_fields:
                col_letter = index_to_col_letter(col_idx)
                vtype = infer_field_value_type(field_key, val)
                sensitivity = (
                    SensitivityLabel.SALARY
                    if "salary" in field_key.lower()
                    else SensitivityLabel.NONE
                )
                field = ExtractedField(
                    extraction_job_id=job.id,
                    source_document_id=doc.id,
                    field_key=field_key,
                    value=val,
                    raw_text=raw_val,
                    value_type=vtype,
                    confidence=0.95,
                    source_location={
                        "kind": "cell",
                        "sheet": sheet_name,
                        "row": row_idx,
                        "col": col_letter,
                    },
                    source_kind=SourceLocationKind.CELL,
                    record_group=str(row_idx),
                    sensitivity=sensitivity,
                )
                db.add(field)

    doc.status = DocumentStatus.NEEDS_REVIEW
    doc.doc_type = doc_type

    # Record audit log
    record_audit(
        db=db,
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        actor_role_id=current_user.role_id,
        action="document.import_mapping_confirm",
        target_type="source_documents",
        target_id=doc.id,
        source_document_id=doc.id,
        after={
            "id": str(doc.id),
            "doc_type": doc_type.value,
            "columns": [c.model_dump() for c in columns],
            "total_rows": len(data_rows),
            "error_rows": len(row_errors),
        },
    )

    db.commit()
    db.refresh(doc)
    return doc, row_errors

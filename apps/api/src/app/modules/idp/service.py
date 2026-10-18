"""IDP business logic and file upload handling service (T-203).

Implements file validation, streaming SHA-256 calculation, deduplication, MinIO storage,
and audit logging per 04-IDP-FEATURE-SPEC.md and 10-API-SPECIFICATION.md.
"""

import hashlib
import re
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


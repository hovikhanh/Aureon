"""IDP business logic and file upload handling service (T-203).

Implements file validation, streaming SHA-256 calculation, deduplication, MinIO storage,
and audit logging per 04-IDP-FEATURE-SPEC.md and 10-API-SPECIFICATION.md.
"""

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.storage import get_storage_service
from app.db.enums import ActorType
from app.modules.audit.service import record_audit
from app.modules.auth.models import User
from app.modules.idp.enums import (
    AutonomyLevel,
    DocType,
    DocumentKind,
    DocumentStatus,
    InputChannel,
)
from app.modules.idp.models import SourceDocument

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
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "error": {
                    "code": "UNSUPPORTED_MEDIA_TYPE",
                    "message": f"Unsupported file format '{ext}'. Allowed: {allowed_list}",
                }
            },
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
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "error": {
                        "code": "FILE_TOO_LARGE",
                        "message": f"File size exceeds 20MB limit (read {total_bytes} bytes)",
                    }
                },
            )
        hasher.update(chunk)
        chunks.append(chunk)

    file_bytes = b"".join(chunks)
    sha256_hex = hasher.hexdigest()

    page_count = 1
    if ext == ".pdf":
        page_count = count_pdf_pages(file_bytes)
        if page_count > MAX_PDF_PAGES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "error": {
                        "code": "FILE_TOO_LARGE",
                        "message": f"PDF exceeds maximum of 50 pages (detected {page_count} pages)",
                    }
                },
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

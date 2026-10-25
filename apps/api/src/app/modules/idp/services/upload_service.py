"""EP-20 upload (04 §3 step 0, FR-DC-07). Streams files to the object store, records
`ENT-SourceDocument` in `UPLOADED` + a per-attempt `ENT-ExtractionJob` (`QUEUED`), groups a
multi-file request under `ENT-ImportBatch`, and hands each document to the pipeline.

Limits (04 §15.1): ``IDP_MAX_FILES_PER_UPLOAD`` files, ``IDP_MAX_FILE_SIZE_MB`` per file.
SHA-256 dedupe marks a repeat as `DUPLICATE` linked to the original (still created — the user
may "process anyway"). The pipeline itself (scan → OCR → extract → validate) runs out of band.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.config import get_config
from app.core.deps import Principal
from app.core.errors import AppError
from app.core.storage import DEFAULT_BUCKET, ObjectStore, get_object_store
from app.modules.idp.models import ExtractionJob, ImportBatch, SourceDocument
from app.modules.idp.repositories import SourceDocumentRepository
from app.modules.idp.services.mime import resolve_mime
from app.modules.idp.services.schema_registry import default_schema_id

MAX_PREFIX = 4096  # bytes sniffed for magic-byte detection


@dataclass(frozen=True)
class UploadFile:
    filename: str | None
    content_type: str | None
    chunks: Iterator[bytes]


@dataclass
class UploadResult:
    document_ids: list[uuid.UUID]
    job_ids: list[uuid.UUID]
    batch_id: uuid.UUID | None
    duplicates: list[uuid.UUID]


@dataclass
class StoredFile:
    storage_key: str
    mime: str
    size: int
    sha256: str
    prefix: bytes = b""


def store_stream(store: ObjectStore, f: UploadFile, max_mb: int) -> StoredFile:
    """Stream `f` (1 MB chunks) into the object store: size cap → `413`, sha-256, MIME
    whitelist + magic bytes → `415` (04 §15.1). Never holds the whole file in RAM."""
    max_bytes = max_mb * 1024 * 1024
    sha = hashlib.sha256()
    size = 0
    prefix = b""

    def _counting() -> Iterator[bytes]:
        nonlocal size, prefix
        for chunk in f.chunks:
            size += len(chunk)
            if size > max_bytes:
                raise AppError(f"file exceeds {max_mb} MB", code="FILE_TOO_LARGE",
                               status_code=413, details={"max_mb": max_mb})  # fmt: skip
            if len(prefix) < MAX_PREFIX:
                prefix += chunk[: MAX_PREFIX - len(prefix)]
            sha.update(chunk)
            yield chunk

    storage_key = store.put_stream(_counting(), bucket=DEFAULT_BUCKET)
    mime = resolve_mime(f.filename, f.content_type, prefix)
    if mime is None:
        raise AppError(f"unsupported file type: {f.filename}", code="UNSUPPORTED_MEDIA_TYPE",
                       status_code=415, details={"filename": f.filename})  # fmt: skip
    return StoredFile(storage_key, mime, size, sha.hexdigest(), prefix)


class UploadService:
    def __init__(self, db: AsyncSession, store: ObjectStore | None = None) -> None:
        self.db = db
        self.store = store or get_object_store()
        self.cfg = get_config()

    async def upload(
        self,
        user: Principal,
        files: list[UploadFile],
        *,
        channel: str = "C3",
        document_type: str | None = None,
    ) -> UploadResult:
        if not files:
            raise AppError("no files in request", code="BAD_REQUEST", status_code=400)
        if len(files) > self.cfg.idp_max_files_per_upload:
            raise AppError(
                f"too many files (max {self.cfg.idp_max_files_per_upload})",
                code="FILE_TOO_LARGE",
                status_code=413,
                details={"max_files": self.cfg.idp_max_files_per_upload},
            )

        preselected = await self._preselected(document_type)
        batch: ImportBatch | None = None
        if len(files) > 1:
            batch = ImportBatch(
                kind="multi_upload",
                submitted_by=user.user_id,
                total_documents=len(files),
                status="processing",
            )
            self.db.add(batch)
            await self.db.flush()

        result = UploadResult([], [], batch.id if batch else None, [])
        for f in files:
            doc, job = await self._ingest_one(user, f, channel=channel, batch=batch)
            if preselected is not None:  # FR-DC-09: classify step skipped by the pipeline
                doc.type_preselected = True
                doc.document_type_id = preselected
            result.document_ids.append(doc.id)
            result.job_ids.append(job.id)
            if doc.status == "DUPLICATE" and doc.duplicate_of_id is not None:
                result.duplicates.append(doc.id)
        return result

    async def _ingest_one(
        self,
        user: Principal,
        f: UploadFile,
        *,
        channel: str,
        batch: ImportBatch | None,
    ) -> tuple[SourceDocument, ExtractionJob]:
        stored = store_stream(self.store, f, self.cfg.idp_max_file_size_mb)
        storage_key, mime, size = stored.storage_key, stored.mime, stored.size
        digest = stored.sha256
        original = await self._find_duplicate(digest)

        now = datetime.now(UTC)
        doc = SourceDocument(
            import_batch_id=batch.id if batch else None,
            channel=channel,
            kind="FILE",
            original_filename=f.filename,
            mime_type=mime,
            size_bytes=size,
            storage_key=storage_key,
            sha256=digest,
            duplicate_of_id=original.id if original else None,
            scan_status="PENDING",
            pillars=[],
            status="DUPLICATE" if original else "UPLOADED",
            status_reason="DUPLICATE_SHA256" if original else None,
            sensitivity_level=2,
            source="IDP",
            data_classification="INTERNAL",
            submitted_by=user.user_id,
            submitted_at=now,
            department_id=user.department_id,
        )
        self.db.add(doc)
        await self.db.flush()

        job = ExtractionJob(
            source_document_id=doc.id,
            extraction_schema_id=await default_schema_id(self.db),
            attempt_no=1,
            status="QUEUED",
            routing_reasons=[],
            xd_results={},
        )
        self.db.add(job)
        await self.db.flush()

        await record_audit(
            self.db,
            action="idp.upload",
            target_schema="idp",
            target_table="source_documents",
            target_id=doc.id,
            after={
                "filename": f.filename,
                "mime_type": mime,
                "size_bytes": size,
                "sha256": digest,
                "status": doc.status,
            },
        )
        return doc, job

    async def _preselected(self, code: str | None) -> uuid.UUID | None:
        """EP-DC-01 `document_type`: an active doc type code, else `422 VALIDATION_ERROR`."""
        if code is None:
            return None
        from sqlalchemy import select

        from app.core.errors import ValidationError as AppValidationError
        from app.modules.idp.models import DocumentType

        stmt = select(DocumentType.id).where(
            DocumentType.code == code, DocumentType.is_active.is_(True)
        )
        dt_id = (await self.db.execute(stmt)).scalar_one_or_none()
        if dt_id is None:
            raise AppValidationError("unknown or inactive document type",
                                     details={"fields": ["document_type"]})  # fmt: skip
        return dt_id

    async def _find_duplicate(self, digest: str) -> SourceDocument | None:
        return await SourceDocumentRepository(self.db).first_original_by_sha(digest)

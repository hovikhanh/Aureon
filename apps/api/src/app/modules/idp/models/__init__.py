"""Schema `idp` — 10 tables (05 §4.9, §11 pgvector). Column groups follow 05 §2.1.

- business: source_documents, extracted_fields
- config:   document_types, extraction_schemas, validation_rules (no `deleted_at`)
- log:      import_batches, document_pages, extraction_jobs, extraction_reviews,
            review_assignments

`pgvector` is not an installed dependency, so `Vector` below is a minimal `UserDefinedType`
rendering `vector(<dim>)`; the extension itself is created by the first platform migration.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from app.core.base_model import BusinessModel, ConfigModel, LogModel
from app.core.columns import fk, schema_args, sr, txt
from app.core.enums import AUTONOMY_LEVEL, CONFIDENCE_BAND, PILLAR, ROLE_CODE, pg_enum

S = "idp"
TS = DateTime(timezone=True)
ZERO_UUID = "'00000000-0000-0000-0000-000000000000'::uuid"
EMBEDDING_DIM = 1024  # 05 §11


class Vector(UserDefinedType[Any]):
    """Minimal pgvector column type (`vector(dim)`), used because `pgvector` is not installed."""

    cache_ok = True

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def get_col_spec(self, **kw: Any) -> str:
        return f"vector({self.dim})"


# ---------- enums owned by `idp` (05 §6) ----------
INPUT_CHANNEL = pg_enum(S, "input_channel", *(f"C{i}" for i in range(1, 11)))
DOCUMENT_KIND = pg_enum(S, "document_kind", "FILE", "MANUAL", "TRANSCRIPT")
DOCUMENT_STATUS = pg_enum(
    S, "document_status",
    "UPLOADED", "PREPROCESSING", "CLASSIFYING", "EXTRACTING", "VALIDATING", "NEEDS_REVIEW",
    "IN_REVIEW", "AUTO_APPROVED", "APPROVED", "COMMITTED", "REJECTED", "FAILED", "DUPLICATE",
    "ROLLED_BACK", "SPLIT", "SUPERSEDED",
)  # fmt: skip
SCAN_STATUS = pg_enum(S, "scan_status", "PENDING", "CLEAN", "INFECTED", "SKIPPED")
JOB_STATUS = pg_enum(S, "job_status", "QUEUED", "RUNNING", "SUCCEEDED", "FAILED")
ROUTING_DECISION = pg_enum(S, "routing_decision", "STP", "REVIEW")
FIELD_VALUE_TYPE = pg_enum(
    S, "field_value_type",
    "date", "money", "percent", "tax_code", "phone", "text", "person_name", "org_name", "enum",
    "period", "number", "checkbox", "signature_present", "stamp_present",
)  # fmt: skip
ASSIGNMENT_KIND = pg_enum(S, "assignment_kind", "ASSIGN", "REASSIGN", "ESCALATE")
REVIEW_DECISION = pg_enum(S, "review_decision", "APPROVED", "REJECTED", "ABANDONED")
SCHEMA_STATUS = pg_enum(S, "schema_status", "draft", "published", "retired")
RULE_KIND = pg_enum(S, "rule_kind", "field", "cross_field", "cross_document", "master_data")
RULE_SEVERITY = pg_enum(S, "rule_severity", "warn", "fail", "blocking")
BATCH_KIND = pg_enum(S, "batch_kind", "multi_upload", "excel_import", "onboarding")
BATCH_STATUS = pg_enum(S, "batch_status", "open", "processing", "completed", "partially_failed")

MODULE_ENUMS: tuple[ENUM, ...] = (
    INPUT_CHANNEL, DOCUMENT_KIND, DOCUMENT_STATUS, SCAN_STATUS, JOB_STATUS, ROUTING_DECISION,
    FIELD_VALUE_TYPE, ASSIGNMENT_KIND, REVIEW_DECISION, SCHEMA_STATUS, RULE_KIND, RULE_SEVERITY,
    BATCH_KIND, BATCH_STATUS,
)  # fmt: skip


def _hnsw(table: str) -> Index:
    """05 §11 — HNSW cosine index on `embedding`."""
    return Index(
        f"ix_{table}_embedding",
        "embedding",
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


# ---------- config ----------
class DocumentType(ConfigModel):
    """ENT-DocumentType — config, no `deleted_at` (deactivate via `is_active`).

    `current_schema_id` ↔ `extraction_schemas.document_type_id` is a FK cycle, so this side
    uses `use_alter=True` (constraint added after both tables exist).
    """

    __tablename__ = "document_types"
    __table_args__ = (
        CheckConstraint("sensitivity_level BETWEEN 1 AND 4", name="sensitivity_level_1_4"),
        {"schema": S},
    )

    code: Mapped[str] = txt(unique=True)
    name_vi: Mapped[str] = txt()
    name_en: Mapped[str] = txt()
    pillars: Mapped[list[str]] = mapped_column(ARRAY(PILLAR), nullable=False)
    current_schema_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{S}.extraction_schemas.id", ondelete="RESTRICT", use_alter=True),
        nullable=True,
        index=True,
    )
    sensitivity_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    retention_years: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class ExtractionSchema(ConfigModel):
    """ENT-ExtractionSchema — config. `schema_version` is the business version (immutable after
    publish, DEC-162); the inherited `version` is the C19 optimistic lock.
    """

    __tablename__ = "extraction_schemas"
    __table_args__ = (
        Index(
            "uq_extraction_schemas_document_type_id_schema_version",
            "document_type_id",
            "schema_version",
            unique=True,
        ),
        {"schema": S},
    )

    document_type_id: Mapped[uuid.UUID] = fk(f"{S}.document_types.id")
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    fields: Mapped[Any] = mapped_column(JSONB, nullable=False)
    thresholds: Mapped[Any] = mapped_column(JSONB, nullable=False)
    action_names: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    status: Mapped[str] = mapped_column(SCHEMA_STATUS, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class ValidationRule(ConfigModel):
    """ENT-ValidationRule — config; NULL schema = global XD rule."""

    __tablename__ = "validation_rules"
    __table_args__ = (
        Index(
            "uq_validation_rules_schema_code",
            text(f"COALESCE(extraction_schema_id, {ZERO_UUID})"),
            "code",
            unique=True,
        ),
        {"schema": S},
    )

    extraction_schema_id: Mapped[uuid.UUID | None] = fk(f"{S}.extraction_schemas.id", nullable=True)
    code: Mapped[str] = txt()
    kind: Mapped[str] = mapped_column(RULE_KIND, nullable=False)
    expression: Mapped[Any] = mapped_column(JSONB, nullable=False)
    severity: Mapped[str] = mapped_column(RULE_SEVERITY, nullable=False)
    tolerance: Mapped[Any] = mapped_column(Numeric(10, 6), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


# ---------- append-only / log ----------
class ImportBatch(LogModel):
    """ENT-ImportBatch — log group per 05 §2.1 (counters/status still updated by pipeline)."""

    __tablename__ = "import_batches"
    __table_args__ = schema_args(S)

    kind: Mapped[str] = mapped_column(BATCH_KIND, nullable=False)
    title: Mapped[str | None] = txt(nullable=True)
    submitted_by: Mapped[uuid.UUID] = sr(nullable=False)
    total_documents: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    completed_documents: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    failed_documents: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    column_mapping: Mapped[Any] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(BATCH_STATUS, nullable=False)
    quality_score: Mapped[Any] = mapped_column(Numeric(5, 2), nullable=True)


# ---------- business ----------
class SourceDocument(BusinessModel):
    """ENT-SourceDocument — business (C19). `sha256` indexed but not unique (DUPLICATE kept)."""

    __tablename__ = "source_documents"
    __table_args__ = (
        CheckConstraint("size_bytes <= 52428800", name="size_max_50mb"),
        CheckConstraint("page_count <= 300", name="page_count_max_300"),
        CheckConstraint("sensitivity_level BETWEEN 1 AND 4", name="sensitivity_level_1_4"),
        CheckConstraint("retry_count <= 3", name="retry_count_max_3"),
        Index("ix_source_documents_status_submitted_at", "status", "submitted_at"),
        Index("ix_source_documents_pillars", "pillars", postgresql_using="gin"),
        _hnsw("source_documents"),
        {"schema": S},
    )

    import_batch_id: Mapped[uuid.UUID | None] = fk(f"{S}.import_batches.id", nullable=True)
    parent_id: Mapped[uuid.UUID | None] = fk(f"{S}.source_documents.id", nullable=True)
    page_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    channel: Mapped[str] = mapped_column(INPUT_CHANNEL, nullable=False)
    kind: Mapped[str] = mapped_column(DOCUMENT_KIND, nullable=False)
    original_filename: Mapped[str | None] = txt(nullable=True)
    mime_type: Mapped[str | None] = txt(nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_key: Mapped[str | None] = txt(nullable=True)
    sha256: Mapped[str | None] = mapped_column(CHAR(64), nullable=True, index=True)
    duplicate_of_id: Mapped[uuid.UUID | None] = fk(f"{S}.source_documents.id", nullable=True)
    superseded_by_id: Mapped[uuid.UUID | None] = fk(f"{S}.source_documents.id", nullable=True)
    scan_status: Mapped[str] = mapped_column(
        SCAN_STATUS, nullable=False, server_default=text("'PENDING'")
    )
    manual_payload: Mapped[Any] = mapped_column(JSONB, nullable=True)
    document_type_id: Mapped[uuid.UUID | None] = fk(f"{S}.document_types.id", nullable=True)
    classification_confidence: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=True)
    type_preselected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    pillars: Mapped[list[str]] = mapped_column(ARRAY(PILLAR), nullable=False)
    department_id: Mapped[uuid.UUID | None] = sr()
    status: Mapped[str] = mapped_column(DOCUMENT_STATUS, nullable=False)
    status_reason: Mapped[str | None] = txt(nullable=True)
    routing_reason: Mapped[str | None] = txt(nullable=True)
    autonomy_level: Mapped[str | None] = mapped_column(AUTONOMY_LEVEL, nullable=True)
    sensitivity_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    suspicious_content: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    submitted_by: Mapped[uuid.UUID] = sr(nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    locked_by: Mapped[uuid.UUID | None] = sr()
    locked_until: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    committed_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    undo_deadline: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    retention_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    embedding: Mapped[Any] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)


# ---------- append-only / log ----------
class DocumentPage(LogModel):
    """ENT-DocumentPage — append-only; `embedding`/`embedding_model` added by 05 §11."""

    __tablename__ = "document_pages"
    __table_args__ = (
        Index(
            "uq_document_pages_source_document_id_page_number",
            "source_document_id",
            "page_number",
            unique=True,
        ),
        _hnsw("document_pages"),
        {"schema": S},
    )

    source_document_id: Mapped[uuid.UUID] = fk(f"{S}.source_documents.id")
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sheet_name: Mapped[str | None] = txt(nullable=True)
    text_layer_exists: Mapped[bool] = mapped_column(Boolean, nullable=False)
    text_layer_quality: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=True)
    ocr_used: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ocr_confidence: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=True)
    text_content: Mapped[str | None] = txt(nullable=True)
    image_storage_key: Mapped[str | None] = txt(nullable=True)
    width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[Any] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    embedding_model: Mapped[str | None] = txt(nullable=True)


class ExtractionJob(LogModel):
    """ENT-ExtractionJob — append-only (one row per attempt)."""

    __tablename__ = "extraction_jobs"
    __table_args__ = (
        Index(
            "uq_extraction_jobs_source_document_id_attempt_no",
            "source_document_id",
            "attempt_no",
            unique=True,
        ),
        {"schema": S},
    )

    source_document_id: Mapped[uuid.UUID] = fk(f"{S}.source_documents.id")
    extraction_schema_id: Mapped[uuid.UUID] = fk(f"{S}.extraction_schemas.id")
    attempt_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    celery_task_id: Mapped[str | None] = txt(nullable=True)
    status: Mapped[str] = mapped_column(JOB_STATUS, nullable=False)
    model_provider: Mapped[str | None] = txt(nullable=True)
    model_name: Mapped[str | None] = txt(nullable=True)
    document_confidence: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=True)
    routing_decision: Mapped[str | None] = mapped_column(ROUTING_DECISION, nullable=True)
    routing_reasons: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    xd_results: Mapped[Any] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    error_code: Mapped[str | None] = txt(nullable=True)


# ---------- business ----------
class ExtractedField(BusinessModel):
    """ENT-ExtractedField — business (C19). Level-4 `value` is stored as ciphertext.

    UQ `(extraction_job_id, field_name, row_index)` uses NULLS NOT DISTINCT so single
    (non-table) fields with `row_index IS NULL` are unique too.
    """

    __tablename__ = "extracted_fields"
    __table_args__ = (
        CheckConstraint("sensitivity_level BETWEEN 1 AND 4", name="sensitivity_level_1_4"),
        Index(
            "uq_extracted_fields_job_field_row",
            "extraction_job_id",
            "field_name",
            "row_index",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        {"schema": S},
    )

    extraction_job_id: Mapped[uuid.UUID] = fk(f"{S}.extraction_jobs.id")
    document_page_id: Mapped[uuid.UUID | None] = fk(f"{S}.document_pages.id", nullable=True)
    field_name: Mapped[str] = txt()
    row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_type: Mapped[str] = mapped_column(FIELD_VALUE_TYPE, nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    raw_text: Mapped[str | None] = txt(nullable=True)
    confidence: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=False)
    confidence_band: Mapped[str] = mapped_column(CONFIDENCE_BAND, nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    sensitivity_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    source_location: Mapped[Any] = mapped_column(JSONB, nullable=False)
    validation: Mapped[Any] = mapped_column(JSONB, nullable=False)
    master_match: Mapped[Any] = mapped_column(JSONB, nullable=True)
    corrected_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    corrected_by: Mapped[uuid.UUID | None] = sr()
    corrected_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    correction_reason: Mapped[str | None] = txt(nullable=True)


# ---------- append-only / log ----------
class ExtractionReview(LogModel):
    """ENT-ExtractionReview — append-only. "Bắt buộc khi REJECTED" is not marked CK in 05 and
    is ambiguous between code/note, so it is enforced in the service layer.
    """

    __tablename__ = "extraction_reviews"
    __table_args__ = schema_args(S)

    source_document_id: Mapped[uuid.UUID] = fk(f"{S}.source_documents.id")
    extraction_job_id: Mapped[uuid.UUID] = fk(f"{S}.extraction_jobs.id")
    reviewer_id: Mapped[uuid.UUID] = sr(nullable=False)
    reviewer_role: Mapped[str] = mapped_column(ROLE_CODE, nullable=False)
    decision: Mapped[str | None] = mapped_column(REVIEW_DECISION, nullable=True)
    reject_reason_code: Mapped[str | None] = txt(nullable=True)
    reject_note: Mapped[str | None] = txt(nullable=True)
    fields_total: Mapped[int] = mapped_column(Integer, nullable=False)
    fields_corrected: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    opened_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ReviewAssignment(LogModel):
    """ENT-ReviewAssignment — append-only history; one `is_current` row per document.

    "`reason` bắt buộc với REASSIGN" is not marked CK in 05 → enforced in the service layer.
    """

    __tablename__ = "review_assignments"
    __table_args__ = (
        Index(
            "uq_review_assignments_current",
            "source_document_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
        Index(
            "ix_review_assignments_source_document_id_is_current",
            "source_document_id",
            "is_current",
        ),
        Index(
            "ix_review_assignments_to_user_id_due_at",
            "to_user_id",
            "due_at",
            postgresql_where=text("is_current"),
        ),
        {"schema": S},
    )

    source_document_id: Mapped[uuid.UUID] = fk(f"{S}.source_documents.id")
    kind: Mapped[str] = mapped_column(ASSIGNMENT_KIND, nullable=False)
    from_user_id: Mapped[uuid.UUID | None] = sr()
    to_user_id: Mapped[uuid.UUID | None] = sr()
    to_role_code: Mapped[str | None] = mapped_column(ROLE_CODE, nullable=True)
    reason: Mapped[str | None] = txt(nullable=True)
    due_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

"""SQLAlchemy ORM models for IDP Core and Business Records.

Matches docs/2.PRODUCT/05-DATA-MODEL.md §4.3 through §4.8.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.idp.enums import (
    AutonomyLevel,
    DocType,
    DocumentKind,
    DocumentStatus,
    FieldValueType,
    InputChannel,
    JobStatus,
    RecordType,
    ReviewDecision,
    RoutingDecision,
    SensitivityLabel,
    SourceLocationKind,
)


class SourceDocument(Base):
    """ENT-SourceDocument: Raw or virtual document ingested into the system (05 §4.3)."""

    __tablename__ = "source_documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    batch_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    channel: Mapped[InputChannel] = mapped_column(
        SQLEnum(InputChannel, name="input_channel_enum", native_enum=False),
        nullable=False,
    )
    kind: Mapped[DocumentKind] = mapped_column(
        SQLEnum(DocumentKind, name="document_kind_enum", native_enum=False),
        nullable=False,
    )
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    duplicate_of_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_documents.id"), nullable=True, index=True
    )
    manual_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    doc_type: Mapped[DocType | None] = mapped_column(
        SQLEnum(DocType, name="doc_type_enum", native_enum=False),
        nullable=True,
    )
    pillars: Mapped[list[str]] = mapped_column(
        ARRAY(String(10)),
        nullable=False,
        default=list,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus, name="document_status_enum", native_enum=False),
        nullable=False,
        default=DocumentStatus.UPLOADED,
        index=True,
    )
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    autonomy_level: Mapped[AutonomyLevel | None] = mapped_column(
        SQLEnum(AutonomyLevel, name="autonomy_level_enum", native_enum=False),
        nullable=True,
    )
    contains_salary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_pii: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uploaded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    locked_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    undo_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    pages: Mapped[list["DocumentPage"]] = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan"
    )
    extraction_jobs: Mapped[list["ExtractionJob"]] = relationship(
        "ExtractionJob", back_populates="document", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["ExtractionReview"]] = relationship(
        "ExtractionReview", back_populates="document", cascade="all, delete-orphan"
    )
    business_records: Mapped[list["BusinessRecord"]] = relationship(
        "BusinessRecord", back_populates="source_document"
    )

    def mark_committed(self, committed_time: datetime | None = None) -> None:
        """Mark document committed and set undo_deadline to committed_at + 7 days (05 §4.3)."""
        now = committed_time or datetime.now(UTC)
        self.committed_at = now
        self.undo_deadline = now + timedelta(days=7)
        self.status = DocumentStatus.COMMITTED

    def update_contains_salary(self) -> None:
        """TC-DATA-005: Turn on contains_salary if doc_type is EMPLOYEE_LIST."""
        if self.doc_type == DocType.EMPLOYEE_LIST:
            self.contains_salary = True

    @property
    def parent_id(self) -> UUID | None:
        """Parent document UUID if this is a split child document (FR-DC-09)."""
        if self.manual_payload and "parent_id" in self.manual_payload:
            try:
                return UUID(str(self.manual_payload["parent_id"]))
            except (ValueError, TypeError):
                return None
        return None

    @property
    def page_range(self) -> tuple[int, int] | None:
        """Page range (from_page, to_page) if this is a split child document (FR-DC-09)."""
        if self.manual_payload and "page_range" in self.manual_payload:
            pr = self.manual_payload["page_range"]
            if isinstance(pr, (list, tuple)) and len(pr) >= 2:
                return (int(pr[0]), int(pr[1]))
        return None


class DocumentPage(Base):
    """ENT-DocumentPage: Individual page of a document, OCR, and rendered image (05 §4.4)."""

    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint("source_document_id", "page_number", name="uq_document_pages_page"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text_layer_exists: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    text_layer_quality: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    ocr_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped[SourceDocument] = relationship("SourceDocument", back_populates="pages")
    extracted_fields: Mapped[list["ExtractedField"]] = relationship(
        "ExtractedField", back_populates="page"
    )


class ExtractionJob(Base):
    """ENT-ExtractionJob: Asynchronous extraction processing execution (05 §4.5)."""

    __tablename__ = "extraction_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_no: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    doc_type: Mapped[DocType | None] = mapped_column(
        SQLEnum(DocType, name="doc_type_enum", native_enum=False),
        nullable=True,
    )
    classification_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")
    model_route: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, name="job_status_enum", native_enum=False),
        nullable=False,
        default=JobStatus.QUEUED,
    )
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    validation_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    cross_doc_results: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    routing_decision: Mapped[RoutingDecision | None] = mapped_column(
        SQLEnum(RoutingDecision, name="routing_decision_enum", native_enum=False),
        nullable=True,
    )
    routing_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    avg_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped[SourceDocument] = relationship(
        "SourceDocument", back_populates="extraction_jobs"
    )
    fields: Mapped[list["ExtractedField"]] = relationship(
        "ExtractedField", back_populates="job", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["ExtractionReview"]] = relationship(
        "ExtractionReview", back_populates="job"
    )


class ExtractedField(Base):
    """ENT-ExtractedField: Single field extracted by AI from a document (05 §4.6)."""

    __tablename__ = "extracted_fields"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_field_confidence_range"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    extraction_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("extraction_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_page_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("document_pages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    field_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    table_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    record_group: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[FieldValueType] = mapped_column(
        SQLEnum(FieldValueType, name="field_value_type_enum", native_enum=False),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    source_location: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_kind: Mapped[SourceLocationKind] = mapped_column(
        SQLEnum(SourceLocationKind, name="source_location_kind_enum", native_enum=False),
        nullable=False,
    )
    validation: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    sensitivity: Mapped[SensitivityLabel] = mapped_column(
        SQLEnum(SensitivityLabel, name="sensitivity_label_enum", native_enum=False),
        nullable=False,
        default=SensitivityLabel.NONE,
    )
    corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    corrected_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    corrected_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    _final_value: Mapped[Any] = mapped_column("final_value", JSONB, nullable=True)
    business_record_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True
    )
    committed_metric_value_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped[ExtractionJob] = relationship("ExtractionJob", back_populates="fields")
    page: Mapped[DocumentPage | None] = relationship(
        "DocumentPage", back_populates="extracted_fields"
    )
    business_record: Mapped["BusinessRecord | None"] = relationship(
        "BusinessRecord", back_populates="extracted_fields"
    )

    @hybrid_property
    def final_value(self) -> Any:
        """TC-DATA-008: final_value returns corrected_value if present, else original value."""
        if self._final_value is not None:
            return self._final_value
        return self.corrected_value if self.corrected_value is not None else self.value

    @final_value.setter  # type: ignore[no-redef]
    def final_value(self, val: Any) -> None:
        self._final_value = val


class ExtractionReview(Base):
    """ENT-ExtractionReview: Human review decisions and auditing (05 §4.7)."""

    __tablename__ = "extraction_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision != 'REJECTED' OR reject_reason_code IS NOT NULL",
            name="ck_review_reject_reason_required",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    extraction_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("extraction_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    reviewer_role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id"), nullable=False, index=True
    )
    decision: Mapped[ReviewDecision | None] = mapped_column(
        SQLEnum(ReviewDecision, name="review_decision_enum", native_enum=False),
        nullable=True,
    )
    reject_reason_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reject_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    fields_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fields_corrected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped[SourceDocument] = relationship("SourceDocument", back_populates="reviews")
    job: Mapped[ExtractionJob] = relationship("ExtractionJob", back_populates="reviews")

    def decide(self, decision: ReviewDecision, reject_reason_code: str | None = None) -> None:
        """Record decision and calculate duration_ms (TC-DATA-009)."""
        now = datetime.now(UTC)
        self.decision = decision
        self.decided_at = now
        if self.opened_at:
            delta = now - self.opened_at
            self.duration_ms = int(delta.total_seconds() * 1000)
        if decision == ReviewDecision.REJECTED:
            if not reject_reason_code:
                msg = "reject_reason_code is required when decision is REJECTED"
                raise ValueError(msg)
            self.reject_reason_code = reject_reason_code


class BusinessRecord(Base):
    """ENT-BusinessRecord: Unified business entity table (single-table inheritance, 05 §4.8)."""

    __tablename__ = "business_records"
    __table_args__ = (
        Index("ix_business_records_record_period", "record_type", "period_key"),
        Index("ix_business_records_issue_date", "record_type", "issue_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    record_type: Mapped[RecordType] = mapped_column(
        SQLEnum(RecordType, name="record_type_enum", native_enum=False),
        nullable=False,
        index=True,
    )
    pillar: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    series: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tax_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    customer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True
    )
    employee_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("business_records.id", ondelete="SET NULL"), nullable=True, index=True
    )
    period_key: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    done_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    signed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    subtotal: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    vat_rate: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    vat_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    paid_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Generated column: total_amount - COALESCE(paid_amount, 0)
    amount_due: Mapped[int | None] = mapped_column(
        BigInteger,
        Computed("total_amount - COALESCE(paid_amount, 0)", persisted=True),
        nullable=True,
    )

    probability: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    salary: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_critical: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    previous_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source_document: Mapped[SourceDocument | None] = relationship(
        "SourceDocument", back_populates="business_records"
    )
    extracted_fields: Mapped[list[ExtractedField]] = relationship(
        "ExtractedField", back_populates="business_record"
    )

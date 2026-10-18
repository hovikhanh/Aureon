"""Enumerations for Intelligent Document Processing (IDP) and Business Records.

Matches docs/2.PRODUCT/05-DATA-MODEL.md §6 and 04-IDP-FEATURE-SPEC.md §8.
"""

from enum import StrEnum


class InputChannel(StrEnum):
    """Input channels (C1–C5 per 04 §2)."""

    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"


class DocumentKind(StrEnum):
    """Document kind: real file vs virtual document (04 §2, 05 §4.3)."""

    FILE = "FILE"
    MANUAL = "MANUAL"
    TRANSCRIPT = "TRANSCRIPT"


class DocType(StrEnum):
    """7 document types + OTHER (04 §4)."""

    FINANCIAL_REPORT = "FINANCIAL_REPORT"
    INVOICE = "INVOICE"
    SALES_REPORT = "SALES_REPORT"
    CONTRACT = "CONTRACT"
    MEETING_MINUTES = "MEETING_MINUTES"
    EMPLOYEE_LIST = "EMPLOYEE_LIST"
    KPI_OKR = "KPI_OKR"
    OTHER = "OTHER"


class DocumentStatus(StrEnum):
    """14 document lifecycle states (04 §8.1, 05 §6)."""

    UPLOADED = "UPLOADED"
    PREPROCESSING = "PREPROCESSING"
    CLASSIFYING = "CLASSIFYING"
    EXTRACTING = "EXTRACTING"
    VALIDATING = "VALIDATING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    AUTO_APPROVED = "AUTO_APPROVED"
    APPROVED = "APPROVED"
    COMMITTED = "COMMITTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"
    ROLLED_BACK = "ROLLED_BACK"


class AutonomyLevel(StrEnum):
    """Autonomy levels L0–L3 (04 §9, 05 §6)."""

    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class JobStatus(StrEnum):
    """Status of an asynchronous extraction job (05 §4.5)."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class RoutingDecision(StrEnum):
    """Routing decision: Straight-Through Processing vs Human Review (FR-DC-15)."""

    STP = "STP"
    REVIEW = "REVIEW"


class FieldValueType(StrEnum):
    """Data types for extracted fields (04 §5.2)."""

    DATE = "date"
    MONEY = "money"
    PERCENT = "percent"
    TAX_CODE = "tax_code"
    TEXT = "text"
    PERSON_NAME = "person_name"
    ORG_NAME = "org_name"
    ENUM = "enum"
    PERIOD = "period"
    NUMBER = "number"
    TABLE = "table"


class SourceLocationKind(StrEnum):
    """Source location kinds for document traceability (04 §5.1)."""

    PDF_REGION = "pdf_region"
    IMAGE_REGION = "image_region"
    CELL = "cell"
    DOCX_PARAGRAPH = "docx_paragraph"
    TRANSCRIPT = "transcript"
    MANUAL = "manual"


class SensitivityLabel(StrEnum):
    """Sensitivity label for data masking and access control (02 §4.3)."""

    NONE = "NONE"
    PII = "PII"
    SALARY = "SALARY"


class ReviewDecision(StrEnum):
    """Review decisions made by human reviewers (04 §8.2, 05 §4.7)."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ABANDONED = "ABANDONED"


class RecordType(StrEnum):
    """Single-table inheritance record types for business_records (05 §4.8)."""

    INVOICE = "INVOICE"
    CONTRACT = "CONTRACT"
    CUSTOMER = "CUSTOMER"
    OPPORTUNITY = "OPPORTUNITY"
    SURVEY_RESPONSE = "SURVEY_RESPONSE"
    TASK = "TASK"
    DECISION = "DECISION"
    PROJECT = "PROJECT"
    EMPLOYEE = "EMPLOYEE"
    BUDGET_LINE = "BUDGET_LINE"
    FINANCIAL_LINE = "FINANCIAL_LINE"

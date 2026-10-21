"""PostgreSQL ENUM types shared across modules (05 §6, C12).

Types are declared with `create_type=False`: migrations create/drop them explicitly so a type
used by several tables is created exactly once. Module-owned enums live in the module's
models; only types that cross schema boundaries (platform.*, auth.role_code, ai.autonomy_level)
live here so `core/` never imports `modules/`.
"""

from sqlalchemy.dialects.postgresql import ENUM


def pg_enum(schema: str, name: str, *values: str) -> ENUM:
    return ENUM(*values, name=name, schema=schema, create_type=False)


# --- platform (shared) ---
PILLAR = pg_enum("platform", "pillar", "F", "O", "C", "U", "S")
ACTOR_TYPE = pg_enum("platform", "actor_type", "USER", "AI", "SYSTEM")
CONFIDENCE_BAND = pg_enum("platform", "confidence_band", "HIGH", "MEDIUM", "LOW")
PERIOD_TYPE = pg_enum("platform", "period_type", "MONTH", "QUARTER", "YEAR", "ROLLING_12M")
METRIC_UNIT = pg_enum(
    "platform", "metric_unit",
    "VND", "PERCENT", "DAYS", "MONTHS", "RATIO", "COUNT", "SCORE", "INDEX", "VND_PER_PERSON",
)  # fmt: skip
THRESHOLD_DIRECTION = pg_enum("platform", "threshold_direction", "LOWER_IS_BAD", "HIGHER_IS_BAD")
METRIC_VALUE_KIND = pg_enum("platform", "metric_value_kind", "ACTUAL", "TARGET", "FORECAST")
SCOPE_TYPE = pg_enum("platform", "scope_type", "company", "department", "product")
VALUE_ORIGIN = pg_enum("platform", "value_origin", "COMPUTED", "EXTRACTED", "MANUAL", "SEED")
THRESHOLD_STATUS = pg_enum("platform", "threshold_status", "GREEN", "YELLOW", "RED")
ALERT_SEVERITY = pg_enum("platform", "alert_severity", "WARNING", "CRITICAL")
ALERT_STATUS = pg_enum("platform", "alert_status", "OPEN", "ACKNOWLEDGED", "RESOLVED", "DISMISSED")
LINEAGE_KIND = pg_enum(
    "platform", "lineage_kind", "RECORD_FROM_FIELD", "METRIC_FROM_RECORD", "METRIC_FROM_FIELD"
)
NOTIFICATION_KIND = pg_enum(
    "platform", "notification_kind",
    "alert", "review_assigned", "review_escalated", "task_assigned", "approval_requested",
    "approval_decided", "report_ready", "ai_action", "document_ready", "reminder", "system",
)  # fmt: skip
RECORD_SOURCE = pg_enum(
    "platform", "record_source", "MANUAL", "IDP", "IMPORT", "AI", "EVENT", "SEED"
)
DATA_CLASSIFICATION = pg_enum(
    "platform", "data_classification", "PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"
)
APPROVAL_STATUS = pg_enum(
    "platform", "approval_status", "PENDING", "APPROVED", "REJECTED", "CANCELLED", "EXPIRED"
)
REPORT_KIND = pg_enum("platform", "report_kind", "WEEKLY", "MONTHLY")
REPORT_FORMAT = pg_enum("platform", "report_format", "PDF", "XLSX")
REPORT_STATUS = pg_enum("platform", "report_status", "QUEUED", "GENERATING", "READY", "FAILED")
OUTBOX_STATUS = pg_enum("platform", "outbox_status", "PENDING", "PUBLISHED", "FAILED")
PROCESSING_STATUS = pg_enum("platform", "processing_status", "DONE", "DLQ")

# --- cross-schema owned types ---
ROLE_CODE = pg_enum(
    "auth", "role_code",
    "CEO", "CFO", "VP_SALES", "HR_MANAGER", "REVIEWER", "CPO", "RISK_MANAGER", "MANAGER",
    "EMPLOYEE", "ADMIN",
)  # fmt: skip
AUTONOMY_LEVEL = pg_enum("ai", "autonomy_level", "L0", "L1", "L2", "L3")  # L4 out of scope

SHARED_ENUMS: tuple[ENUM, ...] = (
    PILLAR, ACTOR_TYPE, CONFIDENCE_BAND, PERIOD_TYPE, METRIC_UNIT, THRESHOLD_DIRECTION,
    METRIC_VALUE_KIND, SCOPE_TYPE, VALUE_ORIGIN, THRESHOLD_STATUS, ALERT_SEVERITY, ALERT_STATUS,
    LINEAGE_KIND, NOTIFICATION_KIND, RECORD_SOURCE, DATA_CLASSIFICATION, APPROVAL_STATUS,
    REPORT_KIND, REPORT_FORMAT, REPORT_STATUS, OUTBOX_STATUS, PROCESSING_STATUS,
    ROLE_CODE, AUTONOMY_LEVEL,
)  # fmt: skip

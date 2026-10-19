"""Enums for the Dashboard domain (metrics, metric values, alerts).

Matches docs/2.PRODUCT/05-DATA-MODEL.md §6 and docs/2.PRODUCT/03-DASHBOARD-SPEC.md.
"""

from __future__ import annotations

from enum import StrEnum


class MetricUnit(StrEnum):
    """Unit of a metric value (05 §6 `metric_unit`)."""

    VND = "VND"
    PERCENT = "PERCENT"
    DAYS = "DAYS"
    MONTHS = "MONTHS"
    RATIO = "RATIO"
    COUNT = "COUNT"
    SCORE = "SCORE"
    TASKS_PER_PERSON = "TASKS_PER_PERSON"
    VND_PER_PERSON = "VND_PER_PERSON"


class ThresholdDirection(StrEnum):
    """Which direction of the metric is bad (03 §2)."""

    LOWER_IS_BAD = "LOWER_IS_BAD"
    HIGHER_IS_BAD = "HIGHER_IS_BAD"


class ThresholdStatus(StrEnum):
    """Status color of a metric value at computation time (05 §4.10)."""

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class MetricValueKind(StrEnum):
    """ACTUAL vs TARGET metric value (05 §6 `metric_value_kind`)."""

    ACTUAL = "ACTUAL"
    TARGET = "TARGET"


class PeriodType(StrEnum):
    """Period granularity (05 §6 `period_type`)."""

    MONTH = "MONTH"
    QUARTER = "QUARTER"
    YEAR = "YEAR"
    ROLLING_12M = "ROLLING_12M"


class ValueOrigin(StrEnum):
    """How a metric value was produced (05 §4.10 `computation`)."""

    COMPUTED = "COMPUTED"
    EXTRACTED = "EXTRACTED"
    MANUAL = "MANUAL"
    SEED = "SEED"


class AlertSeverity(StrEnum):
    """Alert severity (05 §4.11)."""

    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(StrEnum):
    """Alert lifecycle status (03 §3.1, 05 §4.11)."""

    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"

"""Shared DTO bases + enums for `execution` (10 §4.4). Column names follow 05 §4.7."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TaskStatus = Literal["backlog", "todo", "in_progress", "blocked", "in_review", "done", "cancelled"]
TaskPriority = Literal["low", "medium", "high", "urgent"]
TaskSource = Literal["manual", "meeting", "ai", "document", "mitigation"]
DecisionStatus = Literal["open", "in_progress", "done", "cancelled"]
ProjectStatus = Literal["planned", "active", "on_hold", "done", "cancelled"]
InitiativeStatus = Literal["planned", "active", "at_risk", "done", "cancelled"]
MilestoneStatus = Literal["planned", "done", "missed"]
ObjectiveLevel = Literal["company", "department", "team", "individual"]
OkrStatus = Literal["draft", "active", "closed"]
OkrType = Literal["committed", "aspirational"]
Confidence = Literal["HIGH", "MEDIUM", "LOW"]
Pillar = Literal["F", "O", "C", "U", "S"]
KpiDirection = Literal["HIGHER_IS_BETTER", "LOWER_IS_BETTER", "WITHIN_RANGE", "BINARY"]
KpiValueType = Literal["ratio", "percentage", "numeric", "currency", "duration", "count"]
KpiDataSource = Literal["manual", "document", "automated", "ai_assisted"]
KpiPeriodType = Literal["MONTH", "QUARTER", "YEAR", "ROLLING_12M"]
KpiBand = Literal["CRITICAL", "BELOW", "NEAR", "MEETS", "EXCEEDS"]
StrategyStatus = Literal["draft", "active", "closed"]  # 05 §2.6 `execution.strategy_status`
GoalTargetType = Literal["key_result", "kpi"]  # check-in target (EP-PRF-05/06)
AtRiskReason = Literal["declining", "low_confidence", "behind_plan"]  # R-DEC-55

PERIOD = r"^\d{4}(-Q[1-4]|-(0[1-9]|1[0-2]))?$"


def measure(required: bool = False) -> Any:
    """numeric(20,6) (05 C10)."""
    if required:
        return Field(max_digits=20, decimal_places=6)
    return Field(default=None, max_digits=20, decimal_places=6)


def weight(default: Decimal | None = Decimal(100)) -> Any:
    return Field(default=default, ge=0, le=100, max_digits=7, decimal_places=4)


class Out(BaseModel):
    """Common response columns: C3/C4 + C19 (`source`, `data_classification`, `version`)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    source: str
    data_classification: str
    created_at: datetime
    updated_at: datetime


class LogOut(BaseModel):
    """Append-only rows (05 §2.1 group 3): no C19."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class Patch(BaseModel):
    """PATCH bodies: only sent fields are applied (`model_dump(exclude_unset=True)`)."""

    model_config = ConfigDict(extra="forbid")

    version: int | None = None

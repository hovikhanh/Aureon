"""Pydantic v2 schemas of `platform` (10 §4)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DeadLetterOut(BaseModel):
    """EP-56 row (10 §4.x): `{ event_id, event_type, consumer, attempts, last_error }`.

    `id` (= `processed_events.id`) is the `{id}` of `POST /platform/dead-letters/{id}/replay`:
    `event_id` alone is not unique across consumers. Proposed DEC to list it in 10.
    """

    id: uuid.UUID
    event_id: uuid.UUID
    event_type: str
    consumer: str
    attempts: int
    last_error: str | None


class ReplayOut(BaseModel):
    id: uuid.UUID  # replay job identifier (currently processed_events.id)
    event_id: uuid.UUID
    replay_status: str  # `queued` | `processing` | `done`
    queued_at: str  # ISO 8601 UTC


class ApprovalRequestOut(BaseModel):
    """EP-123/125 ApprovalRequestOut (10 §4.11)."""

    id: uuid.UUID
    rule_code: str | None = None
    target_kind: str
    target_table: str | None = None
    target_id: uuid.UUID | None = None
    ai_action_id: uuid.UUID | None = None
    amount: int | None = None
    currency: str = "VND"
    status: Literal["PENDING", "APPROVED", "REJECTED", "CANCELLED", "EXPIRED"]
    step: int
    requested_by: uuid.UUID
    due_at: datetime
    escalated_at: datetime | None = None


class DecideIn(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str | None = None


class ApprovalTimelineStep(BaseModel):
    step: int
    actor_ref: uuid.UUID | None
    decision: str
    reason: str | None = None
    at: datetime | None = None


class ApprovalDetailOut(ApprovalRequestOut):
    payload_diff: list[dict[str, object]] = Field(default_factory=list)
    timeline: list[ApprovalTimelineStep] = Field(default_factory=list)

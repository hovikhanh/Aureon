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
    """EP-WF-01..03 / EP-TASK-19 ApprovalRequestOut (10 §7.2.2, 05 §2.5)."""

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
    # TODO-T-622: `department_id` / stored `target_kind` (0015) and inbox fields filled by service.
    department_id: uuid.UUID | None = None
    title_key: str | None = None  # i18n key, no fixed sentence (CLAUDE.md §5.2)
    params: dict[str, object] = Field(default_factory=dict)
    requested_by_name: str | None = None
    overdue: bool = False
    created_at: datetime | None = None


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


class AuditLogOut(BaseModel):
    """EP-52 row (10 §4.x): append-only audit entry; `before`/`after` already masked."""

    id: uuid.UUID
    occurred_at: datetime
    actor_type: str
    actor_user_id: uuid.UUID | None
    actor_role: str | None
    action: str
    target_schema: str | None
    target_table: str | None
    target_id: uuid.UUID | None
    before: object | None = None
    after: object | None = None
    why: str | None = None


# ---------- M1.2 T-616 notifications (EP-NTF-01..05, 10 §7.2.1) ----------
NotificationKind = Literal[
    "alert", "review_assigned", "review_escalated", "task_assigned", "approval_requested",
    "approval_decided", "report_ready", "ai_action", "document_ready", "reminder", "system",
]  # fmt: skip


class NotificationOut(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    body: str
    link: str | None
    ref_schema: str | None
    ref_table: str | None
    ref_id: uuid.UUID | None
    read_at: datetime | None
    created_at: datetime


class ReadAllIn(BaseModel):
    up_to: datetime | None = None


class ReadAllOut(BaseModel):
    updated: int


class NotificationPreferenceOut(BaseModel):
    kind: str
    email_enabled: bool
    is_default: bool


class PreferenceItem(BaseModel):
    kind: NotificationKind
    email_enabled: bool


class PreferencesIn(BaseModel):
    items: list[PreferenceItem] = Field(min_length=1, max_length=20)

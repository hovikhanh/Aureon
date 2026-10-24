"""Pydantic v2 schemas of `platform` (10 §4)."""

import uuid
from datetime import datetime
from typing import Any, Literal

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
    # 0015: stored `target_kind` + `department_id` (MGR inbox scope, R-DEC-45).
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


# ---------- EP-ADM-13/14 onboarding (10 §7.2.5, 05 §2.8, R-DEC-75) ----------
OnboardingStatus = Literal["not_started", "in_progress", "completed"]
OnboardingStepName = Literal["company", "org_import", "review", "users", "goals_import", "finish"]
OnboardingStepStatus = Literal["pending", "in_progress", "done", "skipped"]
OnboardingAction = Literal["start", "complete_step", "skip_step", "reopen_step", "finish", "reset"]


class OnboardingStepOut(BaseModel):
    status: OnboardingStepStatus = "pending"
    updated_at: datetime | None = None
    refs: dict[str, Any] = Field(default_factory=dict)


class OnboardingProgressOut(BaseModel):
    """Derived from real data through public services (never trusted from the client)."""

    organization_ready: bool = False
    departments: int = 0
    employees: int = 0
    employees_without_user: int = 0
    users_by_role: dict[str, int] = Field(default_factory=dict)
    kpis: int = 0
    objectives: int = 0


class OnboardingStateOut(BaseModel):
    """`platform.system_settings` key `onboarding.state` + derived `progress`."""

    status: OnboardingStatus = "not_started"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    started_by: uuid.UUID | None = None
    steps: dict[OnboardingStepName, OnboardingStepOut] = Field(default_factory=dict)
    refs: dict[str, Any] = Field(default_factory=dict)
    version: int = 0  # `system_settings.version`; 0 = no row yet
    progress: OnboardingProgressOut = Field(default_factory=OnboardingProgressOut)


class OnboardingPatchIn(BaseModel):
    """EP-ADM-14 body. `version` is required for every action except `start` (service check)."""

    action: OnboardingAction
    step: OnboardingStepName | None = None
    refs: dict[str, Any] | None = None
    reason: str | None = Field(default=None, max_length=500)
    version: int | None = None

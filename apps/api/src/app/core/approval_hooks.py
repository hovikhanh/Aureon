"""Approval execution hooks — decouples `platform` approval from the modules it executes.

When an `ENT-ApprovalRequest` reaches its final `APPROVED` decision, the target object is executed
in the same transaction (04 §10.4). The target may live in another module (e.g. an `ENT-AIAction`
in `ai`), and `platform` must not import that module (DEC-125). Each owning module registers a
callback here at import time, keyed by the approval `target_kind`; the platform approval service
looks it up by key. `core` holds only the registry — it imports no module.

A hook receives `(db, approver, target_id, payload)` and performs the execution in `db`'s
transaction (`payload` = the request's stored payload, e.g. `task_reassign` → new assignee +
the task version seen at request time — R-DEC-45). Registered kinds: `ai_action`, `task_reassign`,
`hiring_plan`.

A **rejection** hook (R-DEC-173) receives `(db, approver, target_id, reason)` when the request is
rejected — for targets whose own state must follow the decision (a hiring plan → `rejected`).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

ApprovalHook = Callable[[Any, Any, uuid.UUID, dict[str, Any]], Awaitable[None]]

_HOOKS: dict[str, ApprovalHook] = {}


def register_approval_hook(target_kind: str, hook: ApprovalHook) -> None:
    _HOOKS[target_kind] = hook


def get_approval_hook(target_kind: str) -> ApprovalHook | None:
    return _HOOKS.get(target_kind)


RejectionHook = Callable[[Any, Any, uuid.UUID, str], Awaitable[None]]

_REJECT_HOOKS: dict[str, RejectionHook] = {}


def register_rejection_hook(target_kind: str, hook: RejectionHook) -> None:
    _REJECT_HOOKS[target_kind] = hook


def get_rejection_hook(target_kind: str) -> RejectionHook | None:
    return _REJECT_HOOKS.get(target_kind)

"""Approval execution hooks — decouples `platform` approval from the modules it executes.

When an `ENT-ApprovalRequest` reaches its final `APPROVED` decision, the target object is executed
in the same transaction (04 §10.4). The target may live in another module (e.g. an `ENT-AIAction`
in `ai`), and `platform` must not import that module (DEC-125). Each owning module registers a
callback here at import time, keyed by the approval `target_kind`; the platform approval service
looks it up by key. `core` holds only the registry — it imports no module.

A hook receives `(db, approver, target_id)` and performs the execution in `db`'s transaction.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

ApprovalHook = Callable[[Any, Any, uuid.UUID], Awaitable[None]]

_HOOKS: dict[str, ApprovalHook] = {}


def register_approval_hook(target_kind: str, hook: ApprovalHook) -> None:
    _HOOKS[target_kind] = hook


def get_approval_hook(target_kind: str) -> ApprovalHook | None:
    return _HOOKS.get(target_kind)

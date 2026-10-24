"""Onboarding progress registry (EP-ADM-13 `progress`, 10 §7.2.5, R-DEC-75).

`progress` is derived from real data in `hr` / `auth` / `execution`, but `platform` may not import
them (`hr`/`execution` → `platform` already exist, DEC-125 cycle). Each owning module registers a
source here at import time — same pattern as `core/org_scope` / `core/data_quality`. A source
returns counts and ids only (never names / emails). `core` imports no module.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

ProgressSource = Callable[[AsyncSession], Awaitable[dict[str, Any]]]

_SOURCES: dict[str, ProgressSource] = {}


def register_progress_source(owner: str, source: ProgressSource) -> None:
    """Install `owner`'s source (re-registration replaces it — idempotent on re-import)."""
    _SOURCES[owner] = source


async def collect_progress(db: AsyncSession) -> dict[str, Any]:
    """Merge every source; `employees_without_user` = live employees not linked to a user."""
    merged: dict[str, Any] = {}
    for owner in sorted(_SOURCES):
        merged |= await _SOURCES[owner](db)
    employee_ids: set[uuid.UUID] = merged.pop("employee_ids", set())
    linked: set[uuid.UUID] = merged.pop("user_employee_ids", set())
    merged["employees_without_user"] = len(employee_ids - linked)
    return merged


# --- org import commit state (05 §2.8: step `review` is `done` once the `org_import` commits) ---
# `idp` registers how to read "is the C5 import committed?" (same pattern as the sources above);
# `platform` derives `review` from it on read — no new event, consumer or field.
CommittedAt = Callable[[AsyncSession, uuid.UUID | None, uuid.UUID | None], Awaitable[str | None]]

_COMMITTED: list[CommittedAt] = []


def register_import_committed(fn: CommittedAt) -> None:
    """Install the `idp` reader (re-registration replaces it)."""
    _COMMITTED[:] = [fn]


async def import_committed_at(
    db: AsyncSession, batch_id: uuid.UUID | None, document_id: uuid.UUID | None
) -> str | None:
    """ISO `committed_at` of the import's source document when it is `COMMITTED`, else None."""
    if not _COMMITTED or (batch_id is None and document_id is None):
        return None
    return await _COMMITTED[0](db, batch_id, document_id)

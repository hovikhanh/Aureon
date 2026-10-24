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

"""Employee directory lookup — lets a module validate an employee id without importing `hr`.

`hr` already imports `execution` (EP-87 workload), so `execution → hr` would be a module cycle
(DEC-125, import-boundary test). `hr` registers its public `HrService.live_employee_ids` here at
import time; callers (e.g. EP-TASK-19 `to_assignee_id`, R-DEC-45) look it up. `core` holds only
the registry — it imports no module. No provider registered → fail closed (RuntimeError).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

EmployeeLookup = Callable[[Any, Sequence[uuid.UUID]], Awaitable[set[uuid.UUID]]]

# M2.3 R-DEC-103: fuzzy name → employee. `(employee_id|None, confidence 0-1, candidate_count)`.
NameMatch = tuple["uuid.UUID | None", float, int]
NameMatcher = Callable[[Any, str], Awaitable[NameMatch]]

_LOOKUP: list[EmployeeLookup] = []
_NAME_MATCHER: list[NameMatcher] = []


def register_employee_lookup(fn: EmployeeLookup) -> None:
    _LOOKUP[:] = [fn]


def register_employee_name_matcher(fn: NameMatcher) -> None:
    _NAME_MATCHER[:] = [fn]


async def live_employee_ids(db: Any, ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Subset of `ids` that are live (not deleted, not terminated) employees."""
    if not _LOOKUP:
        raise RuntimeError("no employee directory registered (hr module not loaded)")
    return await _LOOKUP[0](db, ids)


async def match_employee_by_name(db: Any, name: str) -> NameMatch:
    """Fuzzy match a raw name to a live employee (R-DEC-103). `(id|None, confidence, count)`."""
    if not _NAME_MATCHER:
        raise RuntimeError("no employee name matcher registered (hr module not loaded)")
    return await _NAME_MATCHER[0](db, name)

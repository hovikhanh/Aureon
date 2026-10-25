"""Department subtree registry (R-DEC-57, T-632) — goal scope "khối" / "team".

`execution` needs "department + sub-departments" but may not import `hr` (`hr → execution`
already exists, DEC-125). `hr` registers its public `StructureService.subtree_ids` here at import
time (`app.modules.hr` package init) — same pattern as `core/data_quality.register_dq`.
Without a provider (a process that never imported `hr`) the subtree is just the roots.
"""

import uuid
from collections.abc import Awaitable, Callable, Iterable

from sqlalchemy.ext.asyncio import AsyncSession

SubtreeProvider = Callable[[AsyncSession, Iterable[uuid.UUID]], Awaitable[set[uuid.UUID]]]

_PROVIDER: list[SubtreeProvider] = []


def register_subtree_provider(provider: SubtreeProvider) -> None:
    """Install the provider (re-registration replaces it — idempotent on re-import)."""
    _PROVIDER[:] = [provider]


async def department_subtree(db: AsyncSession, roots: Iterable[uuid.UUID]) -> set[uuid.UUID]:
    """`roots` + every live descendant department (in the current tenant)."""
    ids = set(roots)
    if not ids or not _PROVIDER:
        return ids
    return ids | await _PROVIDER[0](db, ids)

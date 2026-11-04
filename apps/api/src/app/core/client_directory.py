"""Client lookup registry (R-DEC-172) — finance links an OUT invoice to its sales client by MST.

`finance` may not import `sales` (`sales → finance` already exists for revenue by client), so
`sales` registers its public `client_ref_by_tax_code` here at import time (`app.modules.sales`
package init) — the `core/org_scope` pattern. Only `(id, name)` crosses the boundary, never the
client record. Without a provider (a process that never imported `sales`) nothing resolves.
"""

import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

ClientLookup = Callable[[AsyncSession, str], Awaitable[tuple[uuid.UUID, str] | None]]

_LOOKUP: list[ClientLookup] = []


def register_client_lookup(lookup: ClientLookup) -> None:
    """Install the lookup (re-registration replaces it — idempotent on re-import)."""
    _LOOKUP[:] = [lookup]


async def client_by_tax_code(db: AsyncSession, tax_code: str) -> tuple[uuid.UUID, str] | None:
    """`(client_id, name)` of the live client holding this tax code, or `None`."""
    if not tax_code.strip() or not _LOOKUP:
        return None
    return await _LOOKUP[0](db, tax_code.strip())

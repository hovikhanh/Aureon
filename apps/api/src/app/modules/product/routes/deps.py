"""Shared router + dependencies for the product routes (EP-90..95).

Route files (`catalog.py`, `planning.py`, `metrics.py`) register on this one `router`;
`router.py` imports them so `main.py` keeps a single `product_router`.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_db, require_permission, require_pillar_permission
from app.core.routing import EnvelopeRouter

router = EnvelopeRouter(tags=["product"])

Db = Annotated[AsyncSession, Depends(get_db)]
# Record reads cô lập khối U ở service (require_reader); writes cô lập khối U ở dependency.
Reader = Annotated[Principal, Depends(require_permission("product:read"))]
Writer = Annotated[Principal, Depends(require_pillar_permission("product:write"))]
Querier = Annotated[Principal, Depends(require_permission("product:query"))]
DASHBOARD_CACHE = {"Cache-Control": "private, max-age=60", "Vary": "Authorization"}

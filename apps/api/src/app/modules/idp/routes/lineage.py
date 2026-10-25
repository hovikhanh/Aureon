"""`/lineage/*` — EP-DC-26 record lineage to source document page/row (FR-DATA-04, R-DEC-64).

`entity` ∈ whitelist (`hr.employees`, `execution.tasks`, …); scope is checked on both the target
record and the source document — fail → `{restricted: true, reason}`.
"""

import uuid
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_db, require_permission
from app.core.routing import EnvelopeRouter
from app.modules.idp.schemas.capture import LineageOut
from app.modules.idp.services.lineage import read_lineage

router = EnvelopeRouter(prefix="/lineage", tags=["data-capture"])

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_permission("idp:read"))]


@router.get("/{entity}/{record_id}", response_model=LineageOut, summary="EP-DC-26 Record lineage")
async def get_lineage(entity: str, record_id: uuid.UUID, user: Reader, db: Db) -> Any:
    return await read_lineage(db, user, entity, record_id)

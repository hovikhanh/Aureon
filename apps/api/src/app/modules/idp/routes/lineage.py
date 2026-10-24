"""`/lineage/*` — EP-DC-26 record lineage to source document page/row (FR-DATA-04, R-DEC-64).

`entity` ∈ whitelist (`hr.employees`, `execution.tasks`, …); scope is checked on both the target
record and the source document — fail → `{restricted: true, reason}`. Behaviour lands in T-637.
"""

import uuid
from typing import Annotated, Any

from fastapi import Depends

from app.core.deps import Principal, require_permission
from app.core.routing import EnvelopeRouter
from app.core.stub import not_implemented
from app.modules.idp.schemas.capture import LineageOut

router = EnvelopeRouter(prefix="/lineage", tags=["data-capture"])

Reader = Annotated[Principal, Depends(require_permission("idp:read"))]


@router.get("/{entity}/{record_id}", response_model=LineageOut, summary="EP-DC-26 Record lineage")
async def get_lineage(entity: str, record_id: uuid.UUID, user: Reader) -> Any:
    not_implemented("EP-DC-26", "T-637")

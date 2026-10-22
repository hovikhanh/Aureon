"""HTTP routes for `platform` (10 §4): EP-56 dead letters (list + replay).

The brief named `POST /admin/dlq/{id}/retry`; 10 EP-56 (contract source) is
`GET /platform/dead-letters` + `POST /platform/dead-letters/{id}/replay`, `platform:admin`.
"""

import uuid
from typing import Annotated

from fastapi import Depends, Query, status

from app.core.approval_hooks import get_approval_hook
from app.core.deps import DbSession, Principal, require_permission
from app.core.envelope import Page
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.platform.models import ApprovalRequest
from app.modules.platform.schemas import (
    ApprovalRequestOut,
    DeadLetterOut,
    DecideIn,
    ReplayOut,
)
from app.modules.platform.services.approval_service import ApprovalService
from app.modules.platform.services.platform_service import PlatformService

router = EnvelopeRouter(prefix="/platform", tags=["platform"])

PlatformAdmin = Annotated[Principal, Depends(require_permission("platform", "admin"))]
PlatformApprover = Annotated[Principal, Depends(require_permission("platform", "approve"))]
DeadLetterPage = Annotated[PageParams, Depends(page_params())]


def get_platform_service(db: DbSession) -> PlatformService:
    return PlatformService(db)


Service = Annotated[PlatformService, Depends(get_platform_service)]


@router.get("/dead-letters", response_model=list[DeadLetterOut], summary="EP-56 Dead letters")
async def list_dead_letters(
    _: PlatformAdmin,
    svc: Service,
    page: DeadLetterPage,
    consumer: Annotated[str | None, Query()] = None,
    event_type: Annotated[str | None, Query()] = None,
) -> Page[DeadLetterOut]:
    return await svc.list_dead_letters(
        limit=page.limit, offset=page.offset, consumer=consumer, event_type=event_type
    )


@router.post(
    "/dead-letters/{id}/replay",
    response_model=ReplayOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="EP-56 Replay dead letter",
)
async def replay_dead_letter(id: uuid.UUID, _: PlatformAdmin, svc: Service) -> ReplayOut:
    return await svc.replay_dead_letter(id)


@router.post(
    "/approvals/{id}/decide", response_model=ApprovalRequestOut, summary="EP-125 Decide approval"
)
async def decide_approval(
    id: uuid.UUID, body: DecideIn, approver: PlatformApprover, db: DbSession, idem: Idem
) -> ApprovalRequestOut:
    """Decide one step. On the final APPROVE, execute the linked target in the same transaction.

    The target executor is resolved from `core.approval_hooks` (the owning module registers it at
    import time) so `platform` never imports it (DEC-125, no module cycle) — the AI action runs in
    this transaction (04 §10.4).
    """

    async def _on_approved(req: ApprovalRequest) -> None:
        if req.ai_action_id is None:
            return
        hook = get_approval_hook("ai_action")
        if hook is not None:
            await hook(db, approver, req.ai_action_id)

    out = await ApprovalService(db).decide(
        approver, id, decision=body.decision, reason=body.reason, on_approved=_on_approved
    )
    await db.commit()
    return out

"""`/workflow/*` — D04 Approval cơ bản (10 §7.2.2 EP-WF-01..03, R-DEC-40/45).

EP-WF-03 moved from `/platform/approvals/{id}/decide` (EP-125) with v2.1 behaviour, no alias.
EP-WF-01/02 are contract stubs (`501`) until T-622. Only `platform:approve` on every route.
"""

import uuid
from typing import Annotated, Any, Literal

from fastapi import Depends, Query

from app.core.approval_hooks import get_approval_hook
from app.core.deps import DbSession, Principal, require_permission
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.core.stub import not_implemented
from app.modules.platform.models import ApprovalRequest
from app.modules.platform.schemas import ApprovalDetailOut, ApprovalRequestOut, DecideIn
from app.modules.platform.services.approval_service import ApprovalService

router = EnvelopeRouter(prefix="/workflow", tags=["workflow"])

Approver = Annotated[Principal, Depends(require_permission("platform", "approve"))]
ApprovalStatus = Literal["PENDING", "APPROVED", "REJECTED", "CANCELLED", "EXPIRED"]


@router.get(
    "/approval-requests", response_model=list[ApprovalRequestOut],
    summary="EP-WF-01 Approval inbox",
)  # fmt: skip
async def list_approval_requests(
    _: Approver,
    page: Annotated[PageParams, Depends(page_params("due_at", "created_at"))],
    assigned_to: Annotated[Literal["me"], Query()] = "me",
    status: ApprovalStatus | None = None,
    rule_code: str | None = None,
    target_kind: str | None = None,
) -> Any:
    not_implemented("EP-WF-01", "T-622")


@router.get(
    "/approval-requests/{id}", response_model=ApprovalDetailOut,
    summary="EP-WF-02 Approval request detail",
)  # fmt: skip
async def get_approval_request(id: uuid.UUID, _: Approver) -> Any:
    not_implemented("EP-WF-02", "T-622")


@router.post(
    "/approval-requests/{id}/decide", response_model=ApprovalRequestOut,
    summary="EP-WF-03 Decide approval",
)  # fmt: skip
async def decide_approval(
    id: uuid.UUID, body: DecideIn, approver: Approver, db: DbSession, idem: Idem
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

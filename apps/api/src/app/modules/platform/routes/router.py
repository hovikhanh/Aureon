"""HTTP routes for `platform` (10 §4): EP-52 audit log, EP-56 dead letters (list + replay).

Approval decide moved to `/workflow/*` (`routes/workflow.py`, EP-WF-03 — R-DEC-40).

The brief named `POST /admin/dlq/{id}/retry`; 10 EP-56 (contract source) is
`GET /platform/dead-letters` + `POST /platform/dead-letters/{id}/replay`, `platform:admin`.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import Depends, Query, status

from app.core.deps import DbSession, Principal, require_permission
from app.core.envelope import Page
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.platform.routes.notifications import router as notifications_router
from app.modules.platform.routes.workflow import router as workflow_router
from app.modules.platform.schemas import (
    AuditLogOut,
    DeadLetterOut,
    ReplayOut,
)
from app.modules.platform.services.audit_query import AuditQueryService
from app.modules.platform.services.platform_service import PlatformService

router = EnvelopeRouter(prefix="/platform", tags=["platform"])

PlatformReader = Annotated[Principal, Depends(require_permission("platform", "read"))]
PlatformAdmin = Annotated[Principal, Depends(require_permission("platform", "admin"))]
DeadLetterPage = Annotated[PageParams, Depends(page_params())]


def get_platform_service(db: DbSession) -> PlatformService:
    return PlatformService(db)


Service = Annotated[PlatformService, Depends(get_platform_service)]


@router.get("/audit-logs", response_model=list[AuditLogOut], summary="EP-52 Audit log")
async def list_audit_logs(
    _: PlatformReader,
    db: DbSession,
    page: DeadLetterPage,
    action: Annotated[str | None, Query()] = None,
    target_type: Annotated[str | None, Query()] = None,
    target_id: Annotated[uuid.UUID | None, Query()] = None,
    actor_user_id: Annotated[uuid.UUID | None, Query()] = None,
    actor_type: Annotated[Literal["USER", "AI", "SYSTEM"] | None, Query()] = None,
    occurred_from: Annotated[datetime | None, Query(alias="from")] = None,
    occurred_to: Annotated[datetime | None, Query(alias="to")] = None,
) -> Page[AuditLogOut]:
    """EP-ADM-12: + `from`/`to` (ISO 8601 UTC on `occurred_at`) and `actor_type` (M1.2)."""
    return await AuditQueryService(db).list(
        actor_type=actor_type,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=page.limit,
        offset=page.offset,
        action=action,
        target_type=target_type,
        target_id=target_id,
        actor_user_id=actor_user_id,
    )


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


# M1.2 T-616: EP-NTF-01..05 `/notifications` (token only, R-DEC-31) in the same module router.
module_router = EnvelopeRouter(tags=["platform"])
module_router.include_router(router)
module_router.include_router(notifications_router)
# M1.3 T-619C: `/workflow/*` (EP-WF-01..03, R-DEC-40) — replaces `/platform/approvals/*`.
module_router.include_router(workflow_router)

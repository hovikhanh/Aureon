"""EP-INT-01..04 Integration Hub — calendar OAuth (10 §7.2.8, R-DEC-118/119).

Prefix `/integrations` (10 §7.1, D06 · platform). Per-user delegated OAuth: `user_id` is always
the caller (R-DEC-17). Permission `execution:write` (connect/callback/disconnect) and
`execution:read` (providers) — `integration` is not a valid permission domain (§5.3), and
platform:* would exclude EMP/MGR/DIR. Tokens are never returned (R-DEC-117).
"""

from typing import Annotated, Any

from fastapi import Depends, Query, Response
from fastapi.responses import RedirectResponse

from app.core.config import get_config
from app.core.deps import DbSession, Principal, require_permission
from app.core.idempotency import Idem
from app.core.routing import EnvelopeRouter
from app.modules.platform.schemas.integrations import (
    CalendarProviderName,
    ConnectOut,
    ProviderStatusOut,
)
from app.modules.platform.services.integration_service import IntegrationService

router = EnvelopeRouter(prefix="/integrations", tags=["integrations"])

Reader = Annotated[Principal, Depends(require_permission("execution", "read"))]
Writer = Annotated[Principal, Depends(require_permission("execution", "write"))]


@router.get("/providers", response_model=list[ProviderStatusOut], summary="EP-INT-01")
async def list_providers(db: DbSession, user: Reader) -> Any:
    return await IntegrationService(db).providers(user.user_id)


@router.post("/{provider}/connect", response_model=ConnectOut, summary="EP-INT-02")
async def connect(provider: CalendarProviderName, db: DbSession, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay({"provider": provider})) is not None:
        return ConnectOut.model_validate(hit)
    url = await IntegrationService(db).connect(user.user_id, provider)
    await db.commit()
    out = ConnectOut(authorize_url=url)
    await idem.remember(out)
    return out


@router.get("/{provider}/callback", summary="EP-INT-03")
async def callback(
    provider: CalendarProviderName,
    db: DbSession,
    user: Writer,
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
) -> RedirectResponse:
    await IntegrationService(db).callback(user.user_id, provider, code=code, state=state)
    await db.commit()
    base = get_config().web_base_url.rstrip("/")
    return RedirectResponse(url=f"{base}/settings/integrations?connected={provider}")


@router.delete("/{provider}/disconnect", status_code=204, response_class=Response)
async def disconnect(provider: CalendarProviderName, db: DbSession, user: Writer) -> Response:
    await IntegrationService(db).disconnect(user.user_id, provider)
    await db.commit()
    return Response(status_code=204)

"""EP-ADM-13/14 `/platform/onboarding` — UC-07 wizard progress (10 §7.2.5, R-DEC-75).

State lives in `platform.system_settings` key `onboarding.state` (no new table); `progress` is
derived from real data (`core/onboarding` sources of hr/auth/execution). State machine:
`services/onboarding_service.py` (T-648).
"""

from typing import Annotated, Any

from fastapi import Depends

from app.core.deps import DbSession, Principal, require_permission
from app.core.routing import EnvelopeRouter
from app.modules.platform.schemas import OnboardingPatchIn, OnboardingStateOut
from app.modules.platform.services.onboarding_service import OnboardingService

router = EnvelopeRouter(prefix="/platform", tags=["platform-onboarding"])

Reader = Annotated[Principal, Depends(require_permission("platform", "read"))]
Admin = Annotated[Principal, Depends(require_permission("platform", "admin"))]


@router.get("/onboarding", response_model=OnboardingStateOut, summary="EP-ADM-13 Onboarding state")
async def get_onboarding(user: Reader, db: DbSession) -> Any:
    return await OnboardingService(db).get()


@router.patch(
    "/onboarding", response_model=OnboardingStateOut, summary="EP-ADM-14 Onboarding action"
)
async def patch_onboarding(body: OnboardingPatchIn, admin: Admin, db: DbSession) -> Any:
    return await OnboardingService(db).apply(admin, body)

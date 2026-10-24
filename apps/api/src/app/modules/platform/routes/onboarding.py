"""EP-ADM-13/14 `/platform/onboarding` — UC-07 wizard progress (10 §7.2.5, R-DEC-75).

State lives in `platform.system_settings` key `onboarding.state` (no new table); `progress` is
derived from real data through public services. Behaviour lands in T-648 (`501` until then).
"""

from typing import Annotated, Any

from fastapi import Depends

from app.core.deps import Principal, require_permission
from app.core.routing import EnvelopeRouter
from app.core.stub import not_implemented
from app.modules.platform.schemas import OnboardingPatchIn, OnboardingStateOut

router = EnvelopeRouter(prefix="/platform", tags=["platform-onboarding"])

Reader = Annotated[Principal, Depends(require_permission("platform", "read"))]
Admin = Annotated[Principal, Depends(require_permission("platform", "admin"))]


@router.get("/onboarding", response_model=OnboardingStateOut, summary="EP-ADM-13 Onboarding state")
async def get_onboarding(user: Reader) -> Any:
    not_implemented("EP-ADM-13", "T-648")


@router.patch(
    "/onboarding", response_model=OnboardingStateOut, summary="EP-ADM-14 Onboarding action"
)
async def patch_onboarding(body: OnboardingPatchIn, admin: Admin) -> Any:
    not_implemented("EP-ADM-14", "T-648")

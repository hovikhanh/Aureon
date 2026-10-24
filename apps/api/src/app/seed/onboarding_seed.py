"""Seed `platform.system_settings` `onboarding.state = completed` for ABC (T-649, R-DEC-79).

ABC is the already-onboarded demo company: every wizard step `done` with fixed timestamps on
the demo timeline (before `DEMO_REFERENCE_DATE`), `refs` = the seeded organization id only
(codes/ids, no PII — 05 §2.8). Idempotent: an existing row (an admin / E2E `reset`) is left
untouched; `demo_reset.sh` truncates `platform` first, so a reset restores `completed`.
No `platform.onboarding_completed` event — seed is not a wizard run.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.platform.services.onboarding_service import KEY, STEPS
from app.modules.platform.services.settings_service import SystemSettingService
from app.seed.hr_seed import ORG_ID
from app.seed.ids import seed_uuid

STARTED_AT, COMPLETED_AT = "2026-09-01T01:30:00Z", "2026-09-01T07:45:00Z"


def completed_state(started_by: str) -> dict[str, object]:
    step = {"status": "done", "updated_at": COMPLETED_AT, "refs": {}}
    steps = {s: dict(step) for s in STEPS}
    steps["company"] = {**step, "refs": {"organization_id": str(ORG_ID)}}
    return {"status": "completed", "started_at": STARTED_AT, "completed_at": COMPLETED_AT,
            "started_by": started_by, "steps": steps,
            "refs": {"organization_id": str(ORG_ID)}}  # fmt: skip


async def seed_onboarding(session: AsyncSession, admin_id: uuid.UUID | None) -> str:
    settings = SystemSettingService(session)
    if await settings.get(KEY) is not None:
        return "unchanged"
    by = admin_id or seed_uuid("user", "admin@abc.demo")
    await settings.set(KEY, completed_state(str(by)), reason="seed: ABC đã onboarding",
                       updated_by=by)  # fmt: skip
    return "created"

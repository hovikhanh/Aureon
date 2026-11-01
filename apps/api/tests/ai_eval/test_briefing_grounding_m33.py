"""M3.3 ai-eval BRF-* (T-824, R-DEC-131/132) — CEO Daily Briefing is grounded and idempotent.

The briefing is a snapshot of `ReportingService.executive()`, so every tile carries a
`metric_code` that resolves to the metric store (FR-AIQ-01 — no fabricated numbers). These tests
run against the seeded dev DB inside the rolled-back `db_session`:

- BRF-01: `today()` persists exactly one row per (recipient, day) and is idempotent on re-call.
- BRF-02: every number in the snapshot is grounded — each dashboard tile has a `metric_code`
  and the stale list is a subset of those codes.
- BRF-03: `mark_opened` records the first open (G1 tracking) and stays idempotent.
- BRF-04: a non-executive principal (EMP) is refused the briefing (403 — PermissionDenied).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.core.deps import Principal
from app.core.errors import PermissionDeniedError
from app.modules.ai.models import Briefing
from app.modules.ai.services.briefing_service import BriefingService
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

pytestmark = pytest.mark.integration


def _principal(role: str) -> Principal:
    return Principal(
        user_id=uuid.uuid4(), role=role,
        permissions=frozenset(ROLE_PERMISSIONS[role]), email=f"{role.lower()}@abc.test",
    )  # fmt: skip


async def _count(db, recipient_id: uuid.UUID) -> int:
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(Briefing)
                .where(Briefing.recipient_id == recipient_id)
            )
        ).scalar_one()
    )


async def test_brf01_today_persists_and_is_idempotent(db_session) -> None:
    ceo = _principal("CEO")
    svc = BriefingService(db_session)
    first = await svc.today(ceo)
    await db_session.flush()
    again = await svc.today(ceo)
    assert again.id == first.id  # same (recipient, day) row — idempotent
    assert await _count(db_session, ceo.user_id) == 1


async def test_brf02_every_number_is_grounded(db_session) -> None:
    ceo = _principal("CEO")
    out = await BriefingService(db_session).today(ceo)
    tiles = out.dashboard.get("tiles", [])
    # every tile that shows a number must name the metric it came from (FR-AIQ-01)
    codes = {t["metric_code"] for t in tiles}
    for t in tiles:
        if t.get("value") is not None:
            assert t["metric_code"], "a numeric tile must carry its metric_code"
    assert set(out.stale_metric_codes) <= codes  # stale list ⊆ shown metrics


async def test_brf03_mark_opened_tracks_g1(db_session) -> None:
    ceo = _principal("CEO")
    svc = BriefingService(db_session)
    created = await svc.today(ceo)
    await db_session.flush()
    opened = await svc.mark_opened(ceo, created.id)
    assert opened.status == "opened"
    assert opened.opened_at is not None
    first_open = opened.opened_at
    again = await svc.mark_opened(ceo, created.id)  # idempotent — keeps the first open time
    assert again.opened_at == first_open


async def test_brf04_employee_is_refused(db_session) -> None:
    emp = _principal("EMP")
    with pytest.raises(PermissionDeniedError):
        await BriefingService(db_session).today(emp)

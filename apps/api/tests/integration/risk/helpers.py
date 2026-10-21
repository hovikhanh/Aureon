"""Shared builders for the risk integration tests (T-211..T-215)."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_LOGS
from app.core.events.envelope import OUTBOX
from tests.conftest import ApiClient

OWNER = str(uuid.uuid4())


def risk_body(**kw: Any) -> dict[str, Any]:
    return {
        "title": f"Risk {uuid.uuid4().hex[:8]}", "category": "financial", "likelihood": 3,
        "impact": 4, "owner_id": OWNER, **kw,
    }  # fmt: skip


async def make_risk(
    api: ApiClient, role: str = "RISK_MANAGER", department_id: Any = None, **kw: Any
) -> dict[str, Any]:
    r = await api.call(
        "POST", "/risk/risks", role, json=risk_body(**kw), department_id=department_id
    )
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


async def set_status(
    api: ApiClient, risk_id: str, to: str, role: str = "RISK_MANAGER", **kw: Any
) -> Any:
    return await api.call(
        "POST", f"/risk/risks/{risk_id}/status", role, json={"to_status": to, **kw}
    )


async def audit_actions(db: AsyncSession, target_id: str) -> list[str]:
    rows = await db.execute(
        select(AUDIT_LOGS.c.action).where(AUDIT_LOGS.c.target_id == uuid.UUID(target_id))
    )
    return sorted(r[0] for r in rows)


async def outbox_for(db: AsyncSession, aggregate_id: str) -> list[tuple[str, dict[str, Any]]]:
    rows = await db.execute(
        select(OUTBOX.c.event_type, OUTBOX.c.payload)
        .where(OUTBOX.c.aggregate_id == uuid.UUID(aggregate_id))
        .order_by(OUTBOX.c.occurred_at)
    )
    return [(r[0], r[1]) for r in rows]


def types(events: list[tuple[str, dict[str, Any]]]) -> list[str]:
    return [e[0] for e in events]

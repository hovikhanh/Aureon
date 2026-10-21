"""Shared builders for the sales integration tests (T-111..T-113)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_LOGS
from app.core.events.envelope import OUTBOX
from tests.conftest import ApiClient

FUTURE = (datetime.now(UTC).date() + timedelta(days=30)).isoformat()


def uniq(prefix: str = "Cty") -> str:
    return f"{prefix} {uuid.uuid4().hex}"


async def make_client(api: ApiClient, role: str = "VP_SALES", **kw: Any) -> dict[str, Any]:
    r = await api.call("POST", "/sales/clients", role, json={"name": uniq(), **kw})
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


def deal_body(client_id: str, **kw: Any) -> dict[str, Any]:
    return {
        "name": uniq("Deal"), "client_id": client_id, "deal_value": 800_000_000,
        "probability_pct": 20, "expected_close_date": FUTURE, "owner_id": str(uuid.uuid4()),
        **kw,
    }  # fmt: skip


async def make_deal(
    api: ApiClient, client_id: str, role: str = "VP_SALES", department_id: Any = None, **kw: Any
) -> dict[str, Any]:
    r = await api.call(
        "POST", "/sales/deals", role, json=deal_body(client_id, **kw), department_id=department_id
    )
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


async def stage(api: ApiClient, deal_id: str, to: str, role: str = "VP_SALES", **kw: Any) -> Any:
    return await api.call(
        "POST", f"/sales/deals/{deal_id}/stage", role, json={"to_stage": to, **kw}
    )


async def audit_actions(db: AsyncSession, target_id: str) -> list[str]:
    rows = await db.execute(
        select(AUDIT_LOGS.c.action).where(AUDIT_LOGS.c.target_id == uuid.UUID(target_id))
    )
    return sorted(r[0] for r in rows)


async def outbox_for(db: AsyncSession, aggregate_id: str) -> list[tuple[str, dict[str, Any]]]:
    rows = await db.execute(
        select(OUTBOX.c.event_type, OUTBOX.c.payload).where(
            OUTBOX.c.aggregate_id == uuid.UUID(aggregate_id)
        )
    )
    return [(r[0], r[1]) for r in rows]

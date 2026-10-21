"""Shared builders for the product integration tests (T-201, T-202)."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_LOGS
from app.core.events.envelope import OUTBOX
from tests.conftest import ApiClient


def code() -> str:
    return f"T-{uuid.uuid4().hex[:12]}"


async def make_product(api: ApiClient, role: str = "CPO", **kw: Any) -> dict[str, Any]:
    body = {"code": code(), "name": "Sản phẩm thử", "owner_id": str(uuid.uuid4()), **kw}
    r = await api.call("POST", "/product/products", role, json=body)
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


async def make(api: ApiClient, path: str, body: dict[str, Any]) -> dict[str, Any]:
    r = await api.call("POST", f"/product/{path}", "CPO", json=body)
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


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

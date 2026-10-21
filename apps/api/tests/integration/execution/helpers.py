"""Shared builders for the execution integration tests (T-131..T-133)."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_LOGS
from app.core.events.envelope import OUTBOX
from app.core.security import sign_access_token
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from tests.conftest import ApiClient


def uniq(prefix: str = "X") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def headers(role: str, user_id: Any, department_id: Any = None) -> dict[str, str]:
    """Token for a fixed user id (owner / assignee scope `◑o`)."""
    token, _ = sign_access_token(
        user_id=user_id, email=f"{role.lower()}@abc.test", role=role, role_id=role,
        permissions=list(ROLE_PERMISSIONS[role]), department_id=department_id,
    )  # fmt: skip
    return {"Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid.uuid4())}


async def as_user(
    api: ApiClient, method: str, url: str, role: str, user_id: Any, *,
    department_id: Any = None, json: Any = None, params: Any = None,
) -> Any:  # fmt: skip
    return await api.http.request(
        method, f"/api/v1{url}", json=json, params=params,
        headers=headers(role, user_id, department_id),
    )  # fmt: skip


async def make(api: ApiClient, url: str, body: dict[str, Any], role: str = "CEO") -> dict[str, Any]:
    r = await api.call("POST", url, role, json=body)
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


async def make_task(api: ApiClient, **kw: Any) -> dict[str, Any]:
    return await make(api, "/execution/tasks", {"title": uniq("Task"), **kw})


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


async def patch(api: ApiClient, url: str, version: int, role: str = "CEO", **body: Any) -> Any:
    return await api.call("PATCH", url, role, json={**body, "version": version})

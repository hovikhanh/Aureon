"""EP-52 `GET /platform/audit-logs` (T-516 ADMIN flow, TC-UI-018 backend part)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import Actor
from app.modules.platform.repositories import AuditRepository
from tests.conftest import ApiClient


async def test_admin_lists_masked_audit_logs(api: ApiClient, db_session: AsyncSession) -> None:
    target = uuid.uuid4()
    await AuditRepository(db_session).create(
        action="hr.employee_update",
        target_schema="hr",
        target_table="employees",
        target_id=target,
        before={"salary": 1}, after={"salary": 2, "title": "Lead"},
        actor=Actor(type="USER", user_id=uuid.uuid4(), role="HR_MANAGER"),
    )  # fmt: skip
    res = await api.call("GET", "/platform/audit-logs", "ADMIN", params={"target_id": str(target)})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["meta"]["pagination"]["total"] == 1
    row = body["data"][0]
    assert row["action"] == "hr.employee_update"
    assert row["target_table"] == "employees"
    assert row["after"]["salary"] != 2  # level-4 masked
    assert row["after"]["title"] == "Lead"

    page = await api.call("GET", "/platform/audit-logs", "ADMIN", params={"limit": 5})
    assert page.status_code == 200
    assert len(page.json()["data"]) <= 5


async def test_audit_logs_forbidden_without_platform_read(api: ApiClient) -> None:
    res = await api.call("GET", "/platform/audit-logs", "REVIEWER")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN_ROLE"

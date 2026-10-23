"""T-616 — EP-NTF-01..05 inbox + preferences (TC-M12-13, TC-M12-14, TC-M12-16)."""

import uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import tenant_scope
from app.modules.platform.models import Notification
from app.modules.platform.services.notification_service import NotificationService
from tests.conftest import ApiClient
from tests.integration.hr.helpers import audit_rows
from tests.integration.test_tenant_isolation import TENANT_B

pytestmark = pytest.mark.integration
BASE = "/api/v1/notifications"


async def notify(db: AsyncSession, user: uuid.UUID, kind: str = "system", **kw: Any) -> uuid.UUID:
    nid = await NotificationService(db).create(
        recipient_id=user, kind=kind, title="Tiêu đề", body="Nội dung", **kw
    )
    await db.commit()
    return nid


class Me:
    def __init__(self, api: ApiClient, role: str = "EMPLOYEE", tenant: Any = None) -> None:
        self.api, self.id, self.role, self.tenant = api, uuid.uuid4(), role, tenant

    async def __call__(self, method: str, path: str = "", json: Any = None, **params: Any) -> Any:
        h = self.api.headers(self.role, user_id=self.id, idem=method == "POST",
                             tenant_id=self.tenant)  # fmt: skip
        return await self.api.http.request(method, BASE + path, headers=h, json=json,
                                           params=params or None)  # fmt: skip


async def test_inbox_only_mine(api: ApiClient, db_session: AsyncSession) -> None:
    me, other = Me(api), Me(api)
    a = await notify(db_session, me.id, "alert")
    await notify(db_session, me.id, "task_assigned")
    theirs = await notify(db_session, other.id)
    r = await me("GET")
    assert r.status_code == 200, r.text
    j = r.json()
    assert len(j["data"]) == 2 and j["meta"]["unread_count"] == 2
    assert {n["id"] for n in j["data"]} <= {str(a), *(n["id"] for n in j["data"])}
    assert str(theirs) not in {n["id"] for n in j["data"]}
    assert [n["kind"] for n in (await me("GET", kind="alert")).json()["data"]] == ["alert"]
    # read: someone else's → 404; own → idempotent (keeps first read_at)
    assert (await me("POST", f"/{theirs}/read")).status_code == 404
    first = (await me("POST", f"/{a}/read")).json()["data"]["read_at"]
    again = (await me("POST", f"/{a}/read")).json()["data"]["read_at"]
    assert first and first == again
    unread = (await me("GET", unread_only="true")).json()
    assert len(unread["data"]) == 1 and unread["meta"]["unread_count"] == 1
    r = await me("POST", "/read-all", json={})
    assert r.json()["data"] == {"updated": 1}
    assert (await me("GET")).json()["meta"]["unread_count"] == 0
    other_left = (await other("GET")).json()["meta"]["unread_count"]
    assert other_left == 1  # read-all touched only the caller


async def test_every_role_has_an_inbox(api: ApiClient) -> None:
    for role in ("REVIEWER", "ADMIN", "CEO", "MANAGER"):
        assert (await Me(api, role)("GET")).status_code == 200, role
    assert (await api.http.get(BASE)).status_code == 401


async def test_preferences_default_and_upsert(api: ApiClient, db_session: AsyncSession) -> None:
    me = Me(api)
    prefs = {p["kind"]: p for p in (await me("GET", "/preferences")).json()["data"]}
    assert len(prefs) == 11 and all(p["is_default"] for p in prefs.values())
    assert prefs["task_assigned"]["email_enabled"] and not prefs["alert"]["email_enabled"]
    items = [{"kind": "alert", "email_enabled": True},
             {"kind": "task_assigned", "email_enabled": False}]  # fmt: skip
    r = await me("PATCH", "/preferences", json={"items": items})
    assert r.status_code == 200, r.text
    got = {p["kind"]: p for p in r.json()["data"]}
    assert got["alert"] == {"kind": "alert", "email_enabled": True, "is_default": False}
    assert got["task_assigned"]["email_enabled"] is False
    r = await me(
        "PATCH", "/preferences", json={"items": [{"kind": "alert", "email_enabled": False}]}
    )
    assert {p["kind"]: p for p in r.json()["data"]}["alert"]["email_enabled"] is False
    bad = await me("PATCH", "/preferences", json={"items": [{"kind": "x", "email_enabled": True}]})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "VALIDATION_ERROR"
    acts = [a for a, *_ in await audit_rows(db_session, str(me.id))]
    assert acts.count("platform.notification_preference_update") == 2
    # email_status follows the preference at creation time (TC-M12-14)
    await me("PATCH", "/preferences", json={"items": [{"kind": "alert", "email_enabled": True}]})
    on = await notify(db_session, me.id, "alert")
    off = await notify(db_session, me.id, "task_assigned")
    default_on = await notify(db_session, me.id, "review_assigned")
    rows = (await db_session.execute(select(Notification.id, Notification.email_status).where(
        Notification.id.in_([on, off, default_on])))).all()  # fmt: skip
    assert dict(rows) == {on: "PENDING", off: "NOT_REQUIRED", default_on: "PENDING"}


async def test_tenant_isolation(api: ApiClient, db_session: AsyncSession) -> None:
    me = Me(api)
    nid = await notify(db_session, me.id)
    await me("PATCH", "/preferences", json={"items": [{"kind": "alert", "email_enabled": True}]})
    as_b = Me(api, tenant=TENANT_B)
    as_b.id = me.id  # same user id, other tenant
    assert (await as_b("GET")).json()["data"] == []
    assert (await as_b("POST", f"/{nid}/read")).status_code == 404
    prefs = {p["kind"]: p for p in (await as_b("GET", "/preferences")).json()["data"]}
    assert prefs["alert"]["is_default"] is True
    with tenant_scope(TENANT_B):
        bid = await notify(db_session, me.id)
    assert bid not in {uuid.UUID(n["id"]) for n in (await me("GET")).json()["data"]}

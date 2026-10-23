"""T-614 — ADM user/role administration + audit-log filters (EP-ADM-05..12, 10 §7.2.1).

TC-M12-06 (audit + `auth.user_access_changed`), TC-M12-08 CRUD, TC-M12-09 deactivate /
reactivate with refresh-token revocation, TC-M12-10 roles + audit-log filters, TC-M12-11 RBAC.
"""

import uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from tests.conftest import ApiClient
from tests.integration.hr.helpers import audit_rows, events

pytestmark = pytest.mark.integration
PASSWORD = "Mat-khau-dai-12345"


def data(r: Any, status: int = 200) -> Any:
    assert r.status_code == status, r.text
    return r.json()["data"]


def code(r: Any) -> str:
    return str(r.json()["error"]["code"])


def body(**kw: Any) -> dict[str, Any]:
    return {"email": f"u{uuid.uuid4().hex[:8]}@abc.test", "full_name": "Người dùng thử",
            "role_code": "EMP", "initial_password": PASSWORD, **kw}  # fmt: skip


async def login(api: ApiClient, email: str, password: str = PASSWORD) -> Any:
    return await api.http.post("/api/v1/auth/login", json={"email": email, "password": password})


async def test_create_list_get(api: ApiClient, db_session: AsyncSession) -> None:
    b = body(role_code="DIR", scope_pillars=["O"])
    u = data(await api.call("POST", "/platform/users", "ADMIN", json=b), 201)
    assert u["role_code"] == "DIR" and u["scope_pillars"] == ["O"] and u["version"] == 1
    assert "password_hash" not in u and "initial_password" not in u
    row = (await db_session.execute(select(User).where(User.id == uuid.UUID(u["id"])))).scalar_one()
    assert row.password_hash.startswith("$argon2id$")
    audits = await audit_rows(db_session, u["id"])
    assert [a for a, *_ in audits] == ["auth.user_create"]
    assert "password_hash" not in str(audits) and PASSWORD not in str(audits)
    evts = await events(db_session, u["id"], "auth.user_access_changed")
    assert [p for _, p in evts] == [{"user_id": u["id"], "change": "created", "role_code": "DIR"}]
    dup = await api.call("POST", "/platform/users", "ADMIN", json=body(email=b["email"]))
    assert dup.status_code == 409 and code(dup) == "DUPLICATE_RESOURCE"
    listed = data(await api.call("GET", "/platform/users", "ADMIN",
                                 params={"q": b["email"], "role_code": "DIR"}))  # fmt: skip
    assert [x["id"] for x in listed] == [u["id"]]
    assert data(await api.call("GET", f"/platform/users/{u['id']}", "CEO"))["email"] == b["email"]
    assert (await login(api, b["email"])).status_code == 200


async def test_create_rules(api: ApiClient) -> None:
    r = await api.call("POST", "/platform/users", "ADMIN", json=body(scope_pillars=["F"]))
    assert r.status_code == 422 and r.json()["error"]["details"]["reason"] == "pillars_need_dir"
    r = await api.call("POST", "/platform/users", "ADMIN", json=body(role_code="AI"))
    assert r.status_code == 422
    r = await api.call("POST", "/platform/users", "ADMIN", json=body(role_code="CEO"))
    assert r.status_code == 403 and code(r) == "FORBIDDEN_SCOPE"
    by_ceo = await api.call("POST", "/platform/users", "CEO", json=body(role_code="CEO"))
    assert by_ceo.status_code == 201
    short = await api.call("POST", "/platform/users", "ADMIN", json=body(initial_password="x"))
    assert short.status_code == 422


async def test_role_change_revokes_refresh(api: ApiClient, db_session: AsyncSession) -> None:
    b = body(role_code="MGR")
    u = data(await api.call("POST", "/platform/users", "ADMIN", json=b), 201)
    tok = data(await login(api, b["email"]))["refresh_token"]
    url = f"/platform/users/{u['id']}"
    renamed = data(
        await api.call("PATCH", url, "ADMIN", json={"full_name": "Tên mới", "version": 1})
    )
    assert renamed["version"] == 2
    assert len(await events(db_session, u["id"], "auth.user_access_changed")) == 1
    stale = await api.call("PATCH", url, "ADMIN", json={"role_code": "EMP", "version": 1})
    assert stale.status_code == 409
    p = data(await api.call("PATCH", url, "ADMIN", json={"role_code": "EMP", "version": 2}))
    assert p["role_code"] == "EMP"
    r = await api.http.post("/api/v1/auth/refresh", json={"refresh_token": tok})
    assert r.status_code == 401 and code(r) == "REFRESH_TOKEN_INVALID"
    evts = await events(db_session, u["id"], "auth.user_access_changed")
    changes = [pl["change"] for _, pl in evts]
    assert changes == ["created", "role_changed"]
    up = await api.call("PATCH", url, "ADMIN", json={"role_code": "CEO", "version": 3})
    assert up.status_code == 403 and code(up) == "FORBIDDEN_SCOPE"


async def test_self_change_forbidden(api: ApiClient) -> None:
    b = body(role_code="ADM")
    me = data(await api.call("POST", "/platform/users", "CEO", json=b), 201)
    h = api.headers("ADMIN", user_id=uuid.UUID(me["id"]), idem=True)
    r = await api.http.patch(f"/api/v1/platform/users/{me['id']}", headers=h,
                             json={"role_code": "EMP", "version": 1})  # fmt: skip
    assert r.status_code == 422 and r.json()["error"]["details"]["reason"] == "self_change"
    r = await api.http.post(f"/api/v1/platform/users/{me['id']}/deactivate", headers=h,
                            json={"reason": "thử"})  # fmt: skip
    assert r.status_code == 422


async def test_deactivate_reactivate(api: ApiClient, db_session: AsyncSession) -> None:
    b = body()
    u = data(await api.call("POST", "/platform/users", "ADMIN", json=b), 201)
    tok = data(await login(api, b["email"]))["refresh_token"]
    url = f"/platform/users/{u['id']}"
    off = data(await api.call("POST", f"{url}/deactivate", "ADMIN", json={"reason": "Nghỉ việc"}))
    assert off["is_active"] is False
    again = data(await api.call("POST", f"{url}/deactivate", "ADMIN", json={"reason": "x"}))
    assert again["version"] == off["version"]  # idempotent
    r = await api.http.post("/api/v1/auth/refresh", json={"refresh_token": tok})
    assert r.status_code == 401 and code(r) == "REFRESH_TOKEN_INVALID"
    r = await login(api, b["email"])
    assert r.status_code == 401 and code(r) == "INVALID_CREDENTIALS"
    on = data(await api.call("POST", f"{url}/reactivate", "ADMIN", json={"reason": "Quay lại"}))
    assert on["is_active"] is True and on["locked_until"] is None
    assert (await login(api, b["email"])).status_code == 200
    acts = sorted(
        a for a, *_ in await audit_rows(db_session, u["id"]) if a.startswith("auth.user_")
    )
    assert acts == ["auth.user_create", "auth.user_deactivate", "auth.user_reactivate"]


async def test_roles_and_rbac(api: ApiClient) -> None:
    roles = data(await api.call("GET", "/platform/roles", "ADMIN"))
    by_code = {r["code"]: r for r in roles}
    assert set(by_code) == set(ROLE_PERMISSIONS)
    for c, perms in ROLE_PERMISSIONS.items():
        assert by_code[c]["permissions"] == sorted(perms), c
    assert "hr:admin" in by_code["ADM"]["permissions"]
    for role in ("MANAGER", "EMPLOYEE", "REVIEWER", "HR_MANAGER"):
        r = await api.call("POST", "/platform/users", role, json=body())
        assert r.status_code == 403 and code(r) == "FORBIDDEN_ROLE", role
        assert (await api.call("GET", "/platform/users", role)).status_code == 403, role


async def test_audit_log_filters(api: ApiClient) -> None:
    u = data(await api.call("POST", "/platform/users", "ADMIN", json=body()), 201)
    rows = data(await api.call("GET", "/platform/audit-logs", "ADMIN", params={
        "target_id": u["id"], "actor_type": "USER", "from": "2020-01-01T00:00:00Z"}))  # fmt: skip
    assert [r["action"] for r in rows] == ["auth.user_create"]
    none = data(await api.call("GET", "/platform/audit-logs", "ADMIN",
                               params={"target_id": u["id"], "actor_type": "AI"}))  # fmt: skip
    assert none == []
    q = {"target_id": u["id"], "to": "2020-01-01T00:00:00Z"}
    old = data(await api.call("GET", "/platform/audit-logs", "ADMIN", params=q))
    assert old == []
    q = {"from": "2026-02-01T00:00:00Z", "to": "2026-01-01T00:00:00Z"}
    bad = await api.call("GET", "/platform/audit-logs", "ADMIN", params=q)
    assert bad.status_code == 400

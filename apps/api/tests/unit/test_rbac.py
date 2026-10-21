"""TC-AUTH-* (unit) — `require_permission` / `require_role` + 02 §5.3 matrix (default deny)."""

import uuid
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.deps import Principal, require_permission, require_role
from app.core.handlers import install_error_handlers
from app.core.permissions import ACTIONS, DOMAINS, VALID_PERMISSIONS, permission_name
from app.core.security import sign_access_token
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS, ROLE_REFS

ROLES = tuple(ROLE_PERMISSIONS)


def _token(role: str, perms: tuple[str, ...] | None = None) -> str:
    token, _ = sign_access_token(
        user_id=uuid.uuid4(),
        email=f"{role.lower()}@abc.vn",
        role=role,
        role_id=str(uuid.uuid4()),
        permissions=ROLE_PERMISSIONS[role] if perms is None else perms,
        department_id=None,
    )
    return token


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    for perm in sorted(VALID_PERMISSIONS):
        domain, action = perm.split(":")

        guard = require_permission(domain, action)

        async def handler(p: Annotated[Principal, Depends(guard)]) -> dict[str, str]:
            return {"role": p.role}

        app.add_api_route(f"/p/{perm}", handler, methods=["GET"])

    ceo_cfo = require_role("CEO", "CFO")

    @app.get("/ceo-or-cfo")
    async def ceo_or_cfo(p: Annotated[Principal, Depends(ceo_cfo)]) -> dict[str, str]:
        return {"role": p.role}

    return app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(_app())


def test_matrix_shape() -> None:
    assert len(ROLES) == 10
    assert list(ROLE_REFS.values()) == [f"ROLE-{i:02d}" for i in range(1, 11)]
    for role, perms in ROLE_PERMISSIONS.items():
        assert set(perms) <= VALID_PERMISSIONS, role
        assert len(set(perms)) == len(perms), role


def test_matrix_spot_checks() -> None:
    """Anchors from 02 §5.3 / CLAUDE.md §1.4."""
    p = {r: set(v) for r, v in ROLE_PERMISSIONS.items()}
    assert "hr:approve" in p["CFO"]
    assert "risk:approve" in p["CEO"]
    assert "ai:admin" in p["ADMIN"]
    assert "finance:read" not in p["ADMIN"]  # ADMIN does not read business records
    assert "idp:approve" in p["REVIEWER"]
    assert "platform:admin" not in p["EMPLOYEE"]
    assert all("platform:approve" not in p[r] for r in ("EMPLOYEE", "ADMIN", "REVIEWER"))


def test_permission_name_validation() -> None:
    assert permission_name("finance", "read") == "finance:read"
    assert permission_name("finance:read") == "finance:read"
    with pytest.raises(ValueError):
        permission_name("finance", "approve")  # not in 02 §5.2
    with pytest.raises(ValueError):
        require_permission("payroll:read")
    assert set(DOMAINS) == {v.split(":")[0] for v in VALID_PERMISSIONS}
    assert {v.split(":")[1] for v in VALID_PERMISSIONS} <= set(ACTIONS)


@pytest.mark.parametrize("role", ROLES)
def test_every_role_every_permission(client: TestClient, role: str) -> None:
    """10 roles × 33 permissions: allowed iff the matrix grants it, else 403 FORBIDDEN_ROLE."""
    headers = {"Authorization": f"Bearer {_token(role)}"}
    granted = set(ROLE_PERMISSIONS[role])
    for perm in sorted(VALID_PERMISSIONS):
        r = client.get(f"/p/{perm}", headers=headers)
        if perm in granted:
            assert r.status_code == 200, (role, perm)
            assert r.json() == {"role": role}
        else:
            assert r.status_code == 403, (role, perm)
            assert r.json()["error"]["code"] == "FORBIDDEN_ROLE"
            assert r.json()["error"]["details"] == {"required": perm}


def test_missing_and_bad_token(client: TestClient) -> None:
    r = client.get("/p/finance:read")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"
    r = client.get("/p/finance:read", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401
    r = client.get("/p/finance:read", headers={"Authorization": "Basic abc"})
    assert r.status_code == 401


def test_require_role(client: TestClient) -> None:
    assert (
        client.get("/ceo-or-cfo", headers={"Authorization": f"Bearer {_token('CFO')}"}).status_code
        == 200
    )
    r = client.get("/ceo-or-cfo", headers={"Authorization": f"Bearer {_token('EMPLOYEE')}"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_permissions_come_from_token_not_role_name(client: TestClient) -> None:
    """A CEO token minted with no permissions is denied — the role name grants nothing."""
    r = client.get("/p/finance:read", headers={"Authorization": f"Bearer {_token('CEO', ())}"})
    assert r.status_code == 403

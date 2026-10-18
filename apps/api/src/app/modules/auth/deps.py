"""Authentication & Role dependencies — 10 §1.4, 02 §3 (T-104).

Provides:
- ``require_role(*allowed_roles)``: FastAPI dependency enforcing JWT Bearer token authentication
  and role-based authorization. Attaches ``__aureon_roles__`` marker for OpenAPI contract checks.
- ``compute_permissions(role_code)``: Computes the capability object per 02 §3 & 10 EP-03.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session, joinedload

from app.core.config import ConfigService, get_config
from app.core.errors import ApiError, ErrorCode
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.auth.token import TokenError, decode_access_token

ROLE_MARKER = "__aureon_roles__"

# Capability dictionary mapping per role code (02 §3 matrix & 10 EP-03)
ROLE_PERMISSIONS: dict[str, dict[str, Any]] = {
    "ROLE-01": {
        "alerts.ack_pillars": ["FIN", "CUS", "OPS", "HR"],
        "review.pillars": [],
        "onboarding": True,
        "audit.read": True,
        "salary.view": False,
        "dashboard.view_pillars": ["FIN", "CUS", "OPS", "HR"],
        "dashboard.view_agg_pillars": [],
    },
    "ROLE-02": {
        "alerts.ack_pillars": ["FIN"],
        "review.pillars": ["FIN"],
        "onboarding": False,
        "audit.read": False,
        "salary.view": False,
        "dashboard.view_pillars": ["FIN", "OPS"],
        "dashboard.view_agg_pillars": ["CUS", "HR"],
    },
    "ROLE-03": {
        "alerts.ack_pillars": ["CUS"],
        "review.pillars": [],
        "onboarding": False,
        "audit.read": False,
        "salary.view": False,
        "dashboard.view_pillars": ["CUS", "FIN"],
        "dashboard.view_agg_pillars": ["OPS"],
    },
    "ROLE-04": {
        "alerts.ack_pillars": ["HR"],
        "review.pillars": ["HR"],
        "onboarding": False,
        "audit.read": False,
        "salary.view": True,
        "dashboard.view_pillars": ["HR", "OPS"],
        "dashboard.view_agg_pillars": ["FIN"],
    },
    "ROLE-05": {
        "alerts.ack_pillars": [],
        "review.pillars": ["FIN", "CUS", "OPS", "HR"],
        "onboarding": True,
        "audit.read": False,
        "salary.view": True,
        "dashboard.view_pillars": [],
        "dashboard.view_agg_pillars": [],
    },
}


def compute_permissions(role_code: str) -> dict[str, Any]:
    """Return permissions capabilities object matching 02 §3 and 10 EP-03."""
    return ROLE_PERMISSIONS.get(
        role_code,
        {
            "alerts.ack_pillars": [],
            "review.pillars": [],
            "onboarding": False,
            "audit.read": False,
            "salary.view": False,
            "dashboard.view_pillars": [],
            "dashboard.view_agg_pillars": [],
        },
    )


def require_role(*allowed_roles: str) -> Callable[..., User]:
    """Factory creating a FastAPI dependency that verifies JWT and enforces allowed roles.

    The callable carries ``__aureon_roles__ = frozenset(allowed_roles)`` for contract tests.
    """
    role_set = frozenset(allowed_roles)

    def dependency(
        request: Request,
        db: Annotated[Session, Depends(get_db)],
        config: Annotated[ConfigService, Depends(get_config)],
    ) -> User:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ApiError(ErrorCode.UNAUTHENTICATED, "Missing or invalid authorization header")

        token = auth_header[len("Bearer ") :].strip()
        if not token:
            raise ApiError(ErrorCode.UNAUTHENTICATED, "Missing bearer token")

        try:
            claims = decode_access_token(token, config)
        except TokenError as exc:
            raise ApiError(ErrorCode.UNAUTHENTICATED, f"Token validation failed: {exc}") from exc

        # Role authorization strictly from verified JWT claim (TC-AUTH-009)
        if claims.role not in role_set:
            raise ApiError(
                ErrorCode.FORBIDDEN_ROLE,
                f"Role {claims.role} is not permitted to access this resource",
            )

        user = (
            db.query(User)
            .options(joinedload(User.role))
            .filter(User.id == claims.sub, User.deleted_at.is_(None))
            .first()
        )
        if user is None:
            raise ApiError(ErrorCode.UNAUTHENTICATED, "User not found or deleted")

        return user

    setattr(dependency, ROLE_MARKER, role_set)
    dependency.__name__ = f"require_role_{'_'.join(sorted(role_set))}"
    dependency.__qualname__ = dependency.__name__
    return dependency

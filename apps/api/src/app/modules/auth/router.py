"""EP-02 POST /api/v1/auth/login — public (DEC-080), rate-limited, audited. T-103.

Public endpoint: no ``require_role`` (the client has no JWT yet, 07 §8.1.2) — the contract suite
(T-009) asserts EP-02 carries no ``__aureon_roles__`` marker. Order of operations per 10 EP-02:

1. rate limit per (email, client IP) → 429 ``RATE_LIMITED`` with ``Retry-After`` when over;
2. authenticate + audit ``auth.login`` (success and failure) inside one transaction;
3. commit, then return the ``{data: LoginData}`` envelope.
"""

from __future__ import annotations

import ipaddress
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import ConfigService, get_config
from app.core.errors import ApiError, ErrorCode
from app.db.session import get_db
from app.modules.auth.deps import compute_permissions, require_role
from app.modules.auth.models import User
from app.modules.auth.rate_limit import LoginRateLimiter, default_login_rate_limiter
from app.modules.auth.schemas import (
    DemoUsersEnvelope,
    LoginEnvelope,
    LoginRequest,
    MeData,
    MeEnvelope,
    SwitchRoleEnvelope,
    SwitchRoleRequest,
    UserOut,
)
from app.modules.auth.service import list_demo_users, login, switch_role

router = APIRouter(prefix="/auth", tags=["auth"])


def get_login_rate_limiter(
    config: Annotated[ConfigService, Depends(get_config)],
) -> LoginRateLimiter:
    """Dependency so a test can override it with a tiny limit without weakening the real default."""
    return default_login_rate_limiter(config)


def _client_host(request: Request) -> str:
    """Host used only for the rate-limit key; any non-empty string is fine."""
    return request.client.host if request.client is not None else "unknown"


def _audit_ip(host: str) -> str | None:
    """Only a valid IP reaches the INET ``audit_logs.ip_address`` column; else ``None``."""
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return None
    return host


@router.post(
    "/login",
    response_model=LoginEnvelope,
    responses={
        401: {"description": "INVALID_CREDENTIALS"},
        422: {"description": "VALIDATION_ERROR"},
        429: {"description": "RATE_LIMITED"},
    },
)
def login_endpoint(
    request: Request,
    body: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    config: Annotated[ConfigService, Depends(get_config)],
    rate_limiter: Annotated[LoginRateLimiter, Depends(get_login_rate_limiter)],
) -> LoginEnvelope:
    host = _client_host(request)
    outcome = rate_limiter.hit(body.email, host)
    if not outcome.allowed:
        # 10 §1.3 RATE_LIMITED (429); Retry-After lets the client back off (standard header).
        raise ApiError(
            ErrorCode.RATE_LIMITED,
            headers={"Retry-After": str(outcome.retry_after)},
        )

    try:
        data = login(
            db,
            email=body.email,
            password=body.password,
            config=config,
            ip_address=_audit_ip(host),
        )
    except ApiError:
        # The failure audit row was added to this session; persist it before surfacing the 401
        # (10 EP-02: audit BOTH success and failure). The audit is the only write on this path.
        db.commit()
        raise
    # Success: audit + last_login_at share one committed transaction (05 §4.12, §1.7).
    db.commit()
    return LoginEnvelope(data=data)


@router.get(
    "/me",
    response_model=MeEnvelope,
    responses={
        401: {"description": "UNAUTHENTICATED"},
    },
)
def me_endpoint(
    user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")),
    ],
    config: Annotated[ConfigService, Depends(get_config)],
) -> MeEnvelope:
    """EP-03 GET /api/v1/auth/me — Return current user info and capabilities (10 EP-03)."""
    perms = compute_permissions(user.role.code)
    return MeEnvelope(
        data=MeData(
            user=UserOut.model_validate(user),
            permissions=perms,
            demo_mode=config.demo_mode,
        )
    )


def verify_demo_mode(config: Annotated[ConfigService, Depends(get_config)]) -> None:
    """Ensure DEMO_MODE=true; 404 NOT_FOUND otherwise (07 §8.1.1, 10 EP-04, EP-05)."""
    if not config.demo_mode:
        raise ApiError(ErrorCode.NOT_FOUND, "Demo mode is disabled")


@router.post(
    "/switch-role",
    response_model=SwitchRoleEnvelope,
    responses={
        401: {"description": "UNAUTHENTICATED"},
        404: {"description": "NOT_FOUND"},
        422: {"description": "VALIDATION_ERROR"},
    },
)
def switch_role_endpoint(
    request: Request,
    body: SwitchRoleRequest,
    user: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    config: Annotated[ConfigService, Depends(get_config)],
    _: Annotated[None, Depends(verify_demo_mode)],
) -> SwitchRoleEnvelope:
    """EP-04 POST /api/v1/auth/switch-role — Switch active demo role (10 EP-04)."""
    host = _client_host(request)
    data = switch_role(
        db,
        current_user=user,
        target_role_code=body.target_role_code,
        config=config,
        ip_address=_audit_ip(host),
    )
    db.commit()
    return SwitchRoleEnvelope(data=data)


@router.get(
    "/demo-users",
    response_model=DemoUsersEnvelope,
    responses={
        401: {"description": "UNAUTHENTICATED"},
        404: {"description": "NOT_FOUND"},
    },
)
def demo_users_endpoint(
    _: Annotated[
        User,
        Depends(require_role("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")),
    ],
    db: Annotated[Session, Depends(get_db)],
    __: Annotated[None, Depends(verify_demo_mode)],
) -> DemoUsersEnvelope:
    """EP-05 GET /api/v1/auth/demo-users — List 5 demo accounts (10 EP-05)."""
    items = list_demo_users(db)
    return DemoUsersEnvelope(data=items)

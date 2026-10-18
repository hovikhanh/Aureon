"""JWT mint/verify for EP-02 login — HS256 (DEC-073; 10 §1.4). T-103, reused by T-104/T-105.

A single place that owns the JWT contract:

- ``create_access_token(user, config)`` mints an HS256 token with the required claims
  ``sub, role, iat, exp, iss, aud`` (10 §1.4).
- ``decode_access_token(token, config)`` verifies signature, ``exp``, ``iss`` and ``aud`` and
  returns the parsed :class:`AccessTokenClaims`. T-104's ``get_current_user`` reuses it; a bad
  token raises :class:`TokenError` which the caller maps to ``UNAUTHENTICATED``.

The signing key comes only from ``ConfigService.jwt_secret`` (never hard-coded; CLAUDE.md).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import jwt
from pydantic import BaseModel

from app.core.config import ConfigService

if TYPE_CHECKING:
    from app.modules.auth.models import User

ALGORITHM = "HS256"


class TokenError(Exception):
    """Raised when a JWT is missing, malformed, expired or fails signature/iss/aud checks."""


class AccessTokenClaims(BaseModel):
    """The verified claim set of an access token (10 §1.4)."""

    sub: uuid.UUID
    role: str
    iat: datetime
    exp: datetime
    iss: str
    aud: str


def create_access_token(
    user: User,
    config: ConfigService,
    *,
    now: datetime | None = None,
) -> tuple[str, datetime]:
    """Mint an HS256 access token for ``user``; return ``(token, expires_at)`` (10 §1.4, EP-02).

    ``now`` is injectable so tests can pin ``iat``/``exp`` without touching the real clock.
    """
    issued_at = (now or datetime.now(UTC)).replace(microsecond=0)
    expires_at = issued_at + timedelta(seconds=config.jwt_expires_in)
    payload = {
        "sub": str(user.id),
        "role": user.role.code,
        "iat": issued_at,
        "exp": expires_at,
        "iss": config.jwt_issuer,
        "aud": config.jwt_audience,
    }
    token = jwt.encode(
        payload,
        config.jwt_secret.get_secret_value(),
        algorithm=ALGORITHM,
    )
    return token, expires_at


def decode_access_token(token: str, config: ConfigService) -> AccessTokenClaims:
    """Verify signature, ``exp``, ``iss`` and ``aud`` and return the claims (reused by T-104).

    Raises :class:`TokenError` on any failure; the caller maps it to ``UNAUTHENTICATED``
    (10 §1.4 Verify) and never leaks the underlying PyJWT message.
    """
    try:
        raw = jwt.decode(
            token,
            config.jwt_secret.get_secret_value(),
            algorithms=[ALGORITHM],
            issuer=config.jwt_issuer,
            audience=config.jwt_audience,
            options={"require": ["sub", "role", "iat", "exp", "iss", "aud"]},
        )
    except jwt.InvalidTokenError as exc:  # parent of expired/signature/iss/aud errors
        raise TokenError(str(exc)) from exc
    try:
        return AccessTokenClaims.model_validate(raw)
    except ValueError as exc:
        raise TokenError("token claims failed validation") from exc

"""Unit tests for the JWT helper — HS256 claims + verify (10 §1.4, DEC-073). T-103.

No DB/Redis: these drive ``create_access_token`` / ``decode_access_token`` directly so the claim
contract (sub/role/iat/exp/iss/aud, signature, exp, iss, aud) is covered without integration.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import SecretStr

from app.core.config import ConfigService
from app.modules.auth.token import (
    ALGORITHM,
    AccessTokenClaims,
    TokenError,
    create_access_token,
    decode_access_token,
)


class _Role:
    def __init__(self, code: str) -> None:
        self.code = code


class _User:
    def __init__(self, role_code: str) -> None:
        self.id = uuid.uuid4()
        self.role = _Role(role_code)


def _config(**over: object) -> ConfigService:
    base: dict[str, object] = {
        "jwt_secret": SecretStr("s" * 48),
        "jwt_issuer": "aureon-demo",
        "jwt_audience": "aureon-api",
        "jwt_expires_in": 3600,
    }
    base.update(over)
    return ConfigService(**base)  # type: ignore[arg-type]


def test_create_access_token_has_required_claims() -> None:
    cfg = _config()
    user = _User("ROLE-01")
    token, expires_at = create_access_token(user, cfg)  # type: ignore[arg-type]

    claims: AccessTokenClaims = decode_access_token(token, cfg)
    assert claims.sub == user.id
    assert claims.role == "ROLE-01"
    assert claims.iss == "aureon-demo"
    assert claims.aud == "aureon-api"
    assert claims.exp > claims.iat
    assert claims.exp == expires_at
    # Header advertises HS256.
    assert jwt.get_unverified_header(token)["alg"] == ALGORITHM


def test_decode_rejects_wrong_secret() -> None:
    user = _User("ROLE-02")
    token, _ = create_access_token(user, _config())  # type: ignore[arg-type]
    with pytest.raises(TokenError):
        decode_access_token(token, _config(jwt_secret=SecretStr("different-secret-value-xxxxxxxx")))


def test_decode_rejects_wrong_audience_and_issuer() -> None:
    user = _User("ROLE-03")
    token, _ = create_access_token(user, _config())  # type: ignore[arg-type]
    with pytest.raises(TokenError):
        decode_access_token(token, _config(jwt_audience="other-api"))
    with pytest.raises(TokenError):
        decode_access_token(token, _config(jwt_issuer="other-issuer"))


def test_decode_rejects_expired_token() -> None:
    cfg = _config()
    user = _User("ROLE-04")
    past = datetime.now(UTC) - timedelta(hours=2)
    token, _ = create_access_token(user, cfg, now=past)  # type: ignore[arg-type]
    with pytest.raises(TokenError):
        decode_access_token(token, cfg)


def test_decode_rejects_garbage() -> None:
    with pytest.raises(TokenError):
        decode_access_token("not-a-jwt", _config())

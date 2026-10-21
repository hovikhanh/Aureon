"""JWT RS256 (DEC-129) + argon2id password hashing (DEC-141) + opaque refresh tokens.

Keys: PEM from `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` env (raw PEM or base64 PEM) if set, else the
files at `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH` (`./secrets`, gitignored). Only the
`auth` module calls `sign_access_token`; every module verifies with the public key.
"""

import base64
import binascii
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from pydantic import SecretStr

from app.core.config import ConfigService, get_config
from app.core.errors import UnauthenticatedError

ALGORITHM = "RS256"
REFRESH_TOKEN_BYTES = 48

_hasher = PasswordHasher()


# --- keys ---------------------------------------------------------------------------------


def _decode_pem(raw: str) -> bytes:
    text = raw.strip()
    if text.startswith("-----BEGIN"):
        return text.replace("\\n", "\n").encode()
    try:
        decoded = base64.b64decode(text, validate=True)
    except binascii.Error as exc:
        raise ValueError("JWT key env is neither PEM nor base64 PEM") from exc
    if not decoded.lstrip().startswith(b"-----BEGIN"):
        raise ValueError("JWT key env base64 does not decode to PEM")
    return decoded


def _load_key(env_value: SecretStr | None, path: Path, label: str) -> bytes:
    if env_value is not None and env_value.get_secret_value().strip():
        return _decode_pem(env_value.get_secret_value())
    if not path.is_file():
        raise RuntimeError(
            f"JWT {label} key missing: set JWT_{label.upper()}_KEY or create {path} "
            "(scripts/generate_keys.sh)"
        )
    return path.read_bytes()


@dataclass(frozen=True)
class KeyPair:
    private_pem: bytes | None
    public_pem: bytes
    kid: str


def load_keys(cfg: ConfigService, *, need_private: bool) -> KeyPair:
    public = _load_key(cfg.jwt_public_key, cfg.jwt_public_key_path, "public")
    private = (
        _load_key(cfg.jwt_private_key, cfg.jwt_private_key_path, "private")
        if need_private
        else None
    )
    return KeyPair(private_pem=private, public_pem=public, kid=cfg.jwt_key_id)


@lru_cache
def _signing_keys() -> KeyPair:
    return load_keys(get_config(), need_private=True)


@lru_cache
def _verify_keys() -> KeyPair:
    return load_keys(get_config(), need_private=False)


def reset_key_cache() -> None:
    """Tests / key rotation: drop cached keys so the next call reloads them."""
    _signing_keys.cache_clear()
    _verify_keys.cache_clear()


# --- access token -------------------------------------------------------------------------


@dataclass(frozen=True)
class AccessClaims:
    """Claims of 10 §2.1: sub, email, role, role_id, permissions[], department_id, jti…"""

    sub: uuid.UUID
    email: str
    role: str
    role_id: str
    permissions: tuple[str, ...]
    department_id: uuid.UUID | None
    jti: str
    iat: datetime
    exp: datetime


def sign_access_token(
    *,
    user_id: uuid.UUID,
    email: str,
    role: str,
    role_id: str,
    permissions: tuple[str, ...] | list[str],
    department_id: uuid.UUID | None,
    now: datetime | None = None,
    ttl_seconds: int | None = None,
) -> tuple[str, int]:
    """Return `(token, expires_in_seconds)`."""
    cfg = get_config()
    keys = _signing_keys()
    issued = now or datetime.now(UTC)
    ttl = ttl_seconds if ttl_seconds is not None else cfg.jwt_access_ttl_seconds
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "role_id": role_id,
        "permissions": sorted(permissions),
        "department_id": str(department_id) if department_id else None,
        "iat": int(issued.timestamp()),
        "exp": int((issued + timedelta(seconds=ttl)).timestamp()),
        "iss": cfg.jwt_issuer,
        "aud": cfg.jwt_audience,
        "jti": str(uuid.uuid4()),
    }
    if keys.private_pem is None:  # pragma: no cover — load_keys(need_private=True) guarantees it
        raise RuntimeError("JWT private key not loaded")
    token = jwt.encode(payload, keys.private_pem, algorithm=ALGORITHM, headers={"kid": keys.kid})
    return token, ttl


def verify_access_token(token: str) -> AccessClaims:
    """Verify signature (RS256 only — no `none`/HS*), exp, iss, aud. Raise 401 otherwise."""
    cfg = get_config()
    try:
        data = jwt.decode(
            token,
            _verify_keys().public_pem,
            algorithms=[ALGORITHM],
            audience=cfg.jwt_audience,
            issuer=cfg.jwt_issuer,
            leeway=cfg.jwt_leeway_seconds,
            options={"require": ["sub", "exp", "iat", "jti", "iss", "aud"]},
        )
        dept = data.get("department_id")
        return AccessClaims(
            sub=uuid.UUID(data["sub"]),
            email=str(data["email"]),
            role=str(data["role"]),
            role_id=str(data["role_id"]),
            permissions=tuple(data.get("permissions") or ()),
            department_id=uuid.UUID(dept) if dept else None,
            jti=str(data["jti"]),
            iat=datetime.fromtimestamp(int(data["iat"]), UTC),
            exp=datetime.fromtimestamp(int(data["exp"]), UTC),
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthenticatedError("token expired") from exc
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError) as exc:
        raise UnauthenticatedError("invalid token") from exc


# --- refresh token (opaque, stored as sha256) ---------------------------------------------


def new_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(token: str) -> str:
    """64-hex sha256 → `auth.refresh_tokens.token_hash char(64)`."""
    return hashlib.sha256(token.encode()).hexdigest()


# --- passwords (argon2id) -----------------------------------------------------------------


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# Constant-time dummy so unknown emails cost the same as a wrong password (no user enumeration).
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def burn_password_check(password: str) -> None:
    verify_password(_DUMMY_HASH, password)

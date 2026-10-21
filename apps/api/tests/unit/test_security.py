"""TC-AUTH-* (unit) — RS256 sign/verify, key loading, password hashing (DEC-129, DEC-141)."""

import base64
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core import security
from app.core.config import get_config
from app.core.errors import UnauthenticatedError
from tests.conftest import TEST_PRIVATE_PEM, TEST_PUBLIC_PEM

UID = uuid.uuid4()
DEPT = uuid.uuid4()


def _sign(**kw: object) -> str:
    args: dict[str, object] = {
        "user_id": UID,
        "email": "ceo@abc.vn",
        "role": "CEO",
        "role_id": str(uuid.uuid4()),
        "permissions": ["finance:read", "dashboard:read"],
        "department_id": DEPT,
    }
    args.update(kw)
    token, _ = security.sign_access_token(**args)  # type: ignore[arg-type]
    return token


def test_roundtrip_claims() -> None:
    token = _sign()
    header = jwt.get_unverified_header(token)
    assert header["alg"] == "RS256"
    assert header["kid"] == get_config().jwt_key_id
    claims = security.verify_access_token(token)
    assert claims.sub == UID
    assert claims.role == "CEO"
    assert claims.permissions == ("dashboard:read", "finance:read")
    assert claims.department_id == DEPT
    uuid.UUID(claims.jti)


def test_default_ttl_is_15_minutes() -> None:
    _, ttl = security.sign_access_token(
        user_id=UID, email="a@b.vn", role="CEO", role_id="r", permissions=[], department_id=None
    )
    assert ttl == 900


def test_expired_token_rejected() -> None:
    token = _sign(now=datetime.now(UTC) - timedelta(hours=2), ttl_seconds=60)
    with pytest.raises(UnauthenticatedError, match="expired"):
        security.verify_access_token(token)


def test_tampered_payload_rejected() -> None:
    head, payload, sig = _sign().split(".")
    data = jwt.utils.base64url_decode(payload)
    forged = jwt.utils.base64url_encode(data.replace(b'"CEO"', b'"ADMIN"')).decode()
    with pytest.raises(UnauthenticatedError):
        security.verify_access_token(f"{head}.{forged}.{sig}")


def test_hs256_and_none_rejected() -> None:
    claims = {"sub": str(UID), "exp": 9999999999, "iat": 1, "jti": "x", "iss": "aureon"}
    hs = jwt.encode({**claims, "aud": "aureon-api"}, "x" * 32, algorithm="HS256")
    none = jwt.encode({**claims, "aud": "aureon-api"}, None, algorithm="none")
    for token in (hs, none):
        with pytest.raises(UnauthenticatedError):
            security.verify_access_token(token)


def test_wrong_audience_rejected() -> None:
    token = jwt.encode(
        {"sub": str(UID), "exp": 9999999999, "iat": 1, "jti": "x", "iss": "aureon", "aud": "x"},
        TEST_PRIVATE_PEM,
        algorithm="RS256",
    )
    with pytest.raises(UnauthenticatedError):
        security.verify_access_token(token)


def test_garbage_rejected() -> None:
    with pytest.raises(UnauthenticatedError):
        security.verify_access_token("not.a.jwt")


def test_key_from_base64_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_PUBLIC_KEY", base64.b64encode(TEST_PUBLIC_PEM.encode()).decode())
    monkeypatch.setenv("JWT_PRIVATE_KEY", base64.b64encode(TEST_PRIVATE_PEM.encode()).decode())
    get_config.cache_clear()
    security.reset_key_cache()
    assert security.verify_access_token(_sign()).sub == UID


def test_key_with_escaped_newlines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_PUBLIC_KEY", TEST_PUBLIC_PEM.replace("\n", "\\n"))
    get_config.cache_clear()
    security.reset_key_cache()
    assert security.verify_access_token(_sign()).sub == UID


def test_invalid_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_PUBLIC_KEY", "@@not-base64@@")
    get_config.cache_clear()
    security.reset_key_cache()
    with pytest.raises(ValueError, match="neither PEM"):
        security.load_keys(get_config(), need_private=False)
    monkeypatch.setenv("JWT_PUBLIC_KEY", base64.b64encode(b"hello").decode())
    get_config.cache_clear()
    with pytest.raises(ValueError, match="does not decode"):
        security.load_keys(get_config(), need_private=False)


def test_key_file_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    from pathlib import Path

    d = Path(str(tmp_path))
    (d / "pub.pem").write_text(TEST_PUBLIC_PEM)
    monkeypatch.setenv("JWT_PUBLIC_KEY", "")
    monkeypatch.setenv("JWT_PRIVATE_KEY", "")
    monkeypatch.setenv("JWT_PUBLIC_KEY_PATH", str(d / "pub.pem"))
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", str(d / "missing.pem"))
    get_config.cache_clear()
    keys = security.load_keys(get_config(), need_private=False)
    assert keys.public_pem.startswith(b"-----BEGIN PUBLIC KEY")
    with pytest.raises(RuntimeError, match="private key missing"):
        security.load_keys(get_config(), need_private=True)


def test_password_hash_argon2id() -> None:
    h = security.hash_password("S3cret!pass")
    assert h.startswith("$argon2id$")
    assert security.verify_password(h, "S3cret!pass")
    assert not security.verify_password(h, "wrong")
    assert not security.verify_password("not-a-hash", "x")
    security.burn_password_check("anything")


def test_refresh_token_hash() -> None:
    raw = security.new_refresh_token()
    assert len(raw) >= 60
    assert len(security.hash_refresh_token(raw)) == 64
    assert security.hash_refresh_token(raw) == security.hash_refresh_token(raw)
    assert security.new_refresh_token() != raw


def test_iat_clock_skew_within_leeway_accepted() -> None:
    """Regression (flaky 401 in T-008 gate): whole-second `iat` vs float `now` in PyJWT
    raised ImmatureSignatureError ~1/600 calls. `JWT_LEEWAY_SECONDS` (30) absorbs it."""
    token = _sign(now=datetime.now(UTC) + timedelta(seconds=5))
    assert security.verify_access_token(token).role == "CEO"


def test_iat_beyond_leeway_rejected() -> None:
    token = _sign(now=datetime.now(UTC) + timedelta(minutes=10))
    with pytest.raises(UnauthenticatedError, match="invalid"):
        security.verify_access_token(token)


def test_exp_beyond_leeway_rejected() -> None:
    # Expired 10 min ago (≫ 30 s leeway) — a 1 s margin was flaky under host clock steps (WSL).
    token = _sign(now=datetime.now(UTC) - timedelta(seconds=60 + 600), ttl_seconds=60)
    with pytest.raises(UnauthenticatedError, match="expired"):
        security.verify_access_token(token)

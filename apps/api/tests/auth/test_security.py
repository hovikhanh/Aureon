"""argon2id password hashing (DEC-116; T-101) — unit coverage of app.core.security."""

from __future__ import annotations

import pytest

from app.core.security import hash_password, password_needs_rehash, verify_password


def test_hash_and_verify_roundtrip() -> None:
    hashed = hash_password("s3cret-demo-pw")
    assert hashed.startswith("$argon2id$")
    assert verify_password("s3cret-demo-pw", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_hash_rejects_empty_password() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        hash_password("")


def test_verify_returns_false_on_malformed_hash() -> None:
    assert verify_password("anything", "not-a-valid-hash") is False


def test_needs_rehash_false_for_current_params() -> None:
    assert password_needs_rehash(hash_password("another-demo-pw")) is False

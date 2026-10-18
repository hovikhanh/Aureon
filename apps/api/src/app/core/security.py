"""Password hashing — argon2id via argon2-cffi (DEC-116; 05 §4.1 `users.password_hash`).

Used by the seed (T-101) and EP-02 login (T-103). Plain passwords are never logged or stored.
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# argon2-cffi defaults: Type.ID (argon2id) with RFC 9106 low-memory parameters.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return an encoded argon2id hash (``$argon2id$...``)."""
    if not password:
        raise ValueError("password must not be empty")
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time check; ``False`` on mismatch or malformed hash (never raises)."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """``True`` when the hash was produced with outdated parameters."""
    return _hasher.check_needs_rehash(password_hash)

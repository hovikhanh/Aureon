"""pgcrypto column encryption for level-4 PII (NĐ 13/2023, 05 OQ-08, T-234, DEC-207).

Columns are `bytea` holding `pgp_sym_encrypt(<text>, key)`. Encryption/decryption happen in
SQL via `bind_expression` / `column_expression`, so services, repositories and aggregates
(`SUM(base_salary)`) stay unchanged: they read plaintext, the table and `pg_dump` hold
ciphertext. The key is a bound parameter (never literal SQL, never logged); it comes from
`DB_ENCRYPTION_KEY` (alias `PII_ENCRYPTION_KEY`, 05 OQ-08).
"""

from typing import Any

from sqlalchemy import BigInteger, LargeBinary, Text, bindparam, cast, func
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.types import TypeDecorator

from app.core.config import get_config


def encryption_key() -> str:
    key = get_config().db_encryption_key
    if key is None:
        raise RuntimeError("DB_ENCRYPTION_KEY is not configured (32-byte hex, see .env.example)")
    return key.get_secret_value()


def _key() -> Any:
    return bindparam(None, callable_=encryption_key, type_=Text, unique=True)


def decrypted_bigint(col: Any) -> ColumnElement[int]:
    """Plaintext expression for aggregates (`SUM`) — `column_expression` only applies to the
    top-level SELECT list."""
    return cast(func.pgp_sym_decrypt(col, _key(), type_=Text), BigInteger)


class EncryptedText(TypeDecorator[str]):
    """`bytea` column (DDL in migration 0008); bound/read as text around pgcrypto calls."""

    impl = Text
    cache_ok = True

    def bind_expression(self, bindvalue: Any) -> ColumnElement[Any]:
        return func.pgp_sym_encrypt(cast(bindvalue, Text), _key(), type_=LargeBinary)

    def column_expression(self, col: Any) -> ColumnElement[Any]:
        return func.pgp_sym_decrypt(col, _key(), type_=Text)

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        return None if value is None else str(value)

    def process_result_value(self, value: Any, dialect: Any) -> str | None:
        return None if value is None else str(value)


class EncryptedBigInt(TypeDecorator[int]):
    """`bytea` column; Python side `int` (money, smallest unit)."""

    impl = Text
    cache_ok = True

    def bind_expression(self, bindvalue: Any) -> ColumnElement[Any]:
        return func.pgp_sym_encrypt(cast(bindvalue, Text), _key(), type_=LargeBinary)

    def column_expression(self, col: Any) -> ColumnElement[Any]:
        return decrypted_bigint(col)

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        return None if value is None else str(int(value))

    def process_result_value(self, value: Any, dialect: Any) -> int | None:
        return None if value is None else int(value)

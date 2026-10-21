"""Column helpers so table specs read like 05 §4 (type, null, constraint)."""

import uuid
from typing import Any

from sqlalchemy import CHAR, BigInteger, ForeignKey, Numeric, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def schema_args(schema: str) -> Any:
    """`__table_args__` for a table with no extra constraints (fresh dict per table)."""
    return {"schema": schema}


def fk(target: str, *, nullable: bool = False) -> Any:
    """Same-schema FK, ON DELETE RESTRICT, indexed (05 §1 C6)."""
    return mapped_column(
        UUID(as_uuid=True), ForeignKey(target, ondelete="RESTRICT"), nullable=nullable, index=True
    )


def sr(*, nullable: bool = True, index: bool = True) -> Any:
    """Soft reference across schemas — uuid + index, **no** FK constraint (05 §1 C7)."""
    return mapped_column(UUID(as_uuid=True), nullable=nullable, index=index)


def money(*, nullable: bool = False) -> Any:
    """C8 — bigint smallest unit."""
    return mapped_column(BigInteger, nullable=nullable)


def currency() -> Mapped[str]:
    """C8 — currency char(3) default VND."""
    return mapped_column(CHAR(3), nullable=False, server_default=text("'VND'"))


def pct(*, nullable: bool = True) -> Any:
    """C9 — percentage points numeric(7,4)."""
    return mapped_column(Numeric(7, 4), nullable=nullable)


def measure(*, nullable: bool = True) -> Any:
    """C10 — numeric(20,6)."""
    return mapped_column(Numeric(20, 6), nullable=nullable)


def txt(*, nullable: bool = False, unique: bool = False) -> Any:
    return mapped_column(Text, nullable=nullable, unique=unique)


__all__ = ["currency", "fk", "measure", "money", "pct", "schema_args", "sr", "txt", "uuid"]

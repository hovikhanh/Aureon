"""TC-DATA-002 — common columns + FK indexes on SQLAlchemy metadata (T-004; 05 §1 C3–C6)."""

import uuid

from sqlalchemy import ForeignKey, MetaData, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.base import (
    NAMING_CONVENTION,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

from .metadata_checker import check_metadata


def test_real_metadata_satisfies_conventions() -> None:
    # Gains coverage automatically as T-101/T-102/T-201/T-301 register entity models.
    assert check_metadata(Base.metadata) == []


def test_checker_accepts_compliant_models() -> None:
    # Fresh Base on its own MetaData so throwaway models never pollute ``Base.metadata``.
    class LocalBase(DeclarativeBase):
        metadata = MetaData(naming_convention=NAMING_CONVENTION)

    class Parent(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, LocalBase):
        __tablename__ = "parents"
        name: Mapped[str] = mapped_column(String(50))

    class Child(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, LocalBase):
        __tablename__ = "children"
        parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parents.id"), index=True)

    class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, LocalBase):
        # Append-only: no deleted_at (05 §1 C5 exemption).
        __tablename__ = "audit_logs"

    assert check_metadata(LocalBase.metadata) == []
    # FK index follows the 05 §1 C6 name `ix_<table>_<column>`.
    assert {ix.name for ix in LocalBase.metadata.tables["children"].indexes} == {
        "ix_children_parent_id"
    }
    assert set(LocalBase.metadata.tables) == {"parents", "children", "audit_logs"}
    assert "parents" not in Base.metadata.tables


def test_checker_catches_missing_fk_index() -> None:
    # Fresh Base on its own MetaData so throwaway models never pollute ``Base.metadata``.
    class LocalBase(DeclarativeBase):
        metadata = MetaData(naming_convention=NAMING_CONVENTION)

    class Parent(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, LocalBase):
        __tablename__ = "parents"

    class Orphan(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, LocalBase):
        __tablename__ = "orphans"
        parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parents.id"))

    assert check_metadata(LocalBase.metadata) == [
        "orphans.parent_id: foreign key column has no index"
    ]


def test_checker_catches_missing_common_columns() -> None:
    # Fresh Base on its own MetaData so throwaway models never pollute ``Base.metadata``.
    class LocalBase(DeclarativeBase):
        metadata = MetaData(naming_convention=NAMING_CONVENTION)

    class Bare(LocalBase):
        __tablename__ = "bares"
        id: Mapped[int] = mapped_column(primary_key=True)

    problems = check_metadata(LocalBase.metadata)
    assert "bares.id: must be uuid" in problems
    assert "bares: missing column 'created_at'" in problems
    assert "bares: missing column 'updated_at'" in problems
    assert "bares: missing column 'deleted_at'" in problems


def test_mixin_column_definitions() -> None:
    # Fresh Base on its own MetaData so throwaway models never pollute ``Base.metadata``.
    class LocalBase(DeclarativeBase):
        metadata = MetaData(naming_convention=NAMING_CONVENTION)

    class Thing(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, LocalBase):
        __tablename__ = "things"

    assert Thing.__tablename__ == "things"
    table = LocalBase.metadata.tables["things"]
    assert table.c.id.default is not None and table.c.id.server_default is not None
    assert table.c.created_at.server_default is not None
    assert table.c.updated_at.onupdate is not None
    assert table.c.deleted_at.nullable is True
    assert table.primary_key.name == "pk_things"
    assert table.c.id.default.is_callable

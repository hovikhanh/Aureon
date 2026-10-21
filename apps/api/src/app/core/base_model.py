"""Declarative base + standard columns (05 §1 C3, C4, C5, C17, C19).

Compose per table according to 05 §2.1:
- business entity:   Base + Id + Timestamp + SoftDelete + Actor + CommonFieldsMixin
- config / catalog:  Base + IdMixin + TimestampMixin + VersionMixin + ClassificationMixin
- append-only / log: Base + IdMixin + TimestampMixin
`BusinessModel` is the convenience abstract base for the first group.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, MetaData, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic names → stable autogenerate/downgrade; `ix_<table>_<column>` per 05 §1 C6.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class NameEnum(enum.StrEnum):
    """StrEnum whose `auto()` value is the member NAME (SCREAMING, as stored in PG)."""

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> str:
        return name


class DataClassification(NameEnum):
    """4 BRD levels (DEC-149) — decides which AI provider may see the row (07 §6.5)."""

    PUBLIC = enum.auto()
    INTERNAL = enum.auto()
    CONFIDENTIAL = enum.auto()
    SECRET = enum.auto()


class RecordSource(NameEnum):
    """Channel that created the row (05 §1 C19)."""

    MANUAL = enum.auto()
    IDP = enum.auto()
    IMPORT = enum.auto()
    AI = enum.auto()
    EVENT = enum.auto()
    SEED = enum.auto()


# Shared PG enums live in schema `platform` (05 §1 C12). Migrations create them explicitly.
data_classification_enum = SAEnum(
    DataClassification,
    name="data_classification",
    schema="platform",
    values_callable=lambda e: [m.value for m in e],
    create_type=False,
)
record_source_enum = SAEnum(
    RecordSource,
    name="record_source",
    schema="platform",
    values_callable=lambda e: [m.value for m in e],
    create_type=False,
)


class Base(DeclarativeBase):
    """Root base; `Base.metadata` is Alembic's `target_metadata`."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class IdMixin:
    """C3 — uuid PK; Python uuid4 so id is known pre-flush, DB default as backstop."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    """C4 — UTC timestamps from the DB clock."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    """C5 — NULL = live row."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ActorMixin:
    """C17 — soft refs to auth.users (no FK, C7); NULL when SYSTEM."""

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class VersionMixin:
    """C19 `version` — optimistic locking; bumped on every UPDATE."""

    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class ClassificationMixin:
    """C19 `data_classification`."""

    data_classification: Mapped[DataClassification] = mapped_column(
        data_classification_enum,
        nullable=False,
        server_default=DataClassification.INTERNAL.value,
    )


class SourceMixin:
    """C19 `source` (DEC-154: domain-specific source columns use other names)."""

    source: Mapped[RecordSource] = mapped_column(record_source_enum, nullable=False)


class CommonFieldsMixin(SourceMixin, ClassificationMixin, VersionMixin):
    """All three C19 columns."""


class BusinessModel(Base, IdMixin, TimestampMixin, SoftDeleteMixin, ActorMixin, CommonFieldsMixin):
    """Abstract base for business entities (05 §2.1 group 1)."""

    __abstract__ = True

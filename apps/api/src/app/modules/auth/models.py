"""ENT-Role (`roles`) and ENT-User (`users`) — 05 §4.1, §4.2 (T-101).

Seed-only reference data (02 §3.6): 5 fixed roles ROLE-01..05, 5 demo users (08 §2).
`password_hash` is never part of a response model (10 §1.8 DS6) — see ``schemas.UserOut``.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import Pillar, RoleKey


def _enum_values(enum_cls: type[Pillar] | type[RoleKey]) -> list[str]:
    return [member.value for member in enum_cls]


# PostgreSQL ENUM types (05 §6). `create_type=False`: the migrations own CREATE/DROP TYPE.
PILLAR_ENUM = ENUM(Pillar, name="pillar", values_callable=_enum_values, create_type=False)
ROLE_KEY_ENUM = ENUM(RoleKey, name="role_key", values_callable=_enum_values, create_type=False)


class Role(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """ENT-Role — 05 §4.2. Scope columns are reference data for backend filters (M2)."""

    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    key: Mapped[RoleKey] = mapped_column(ROLE_KEY_ENUM, nullable=False, unique=True)
    name_i18n_key: Mapped[str] = mapped_column(Text, nullable=False)
    pillar_scope: Mapped[list[Pillar]] = mapped_column(ARRAY(PILLAR_ENUM), nullable=False)
    pillar_agg_scope: Mapped[list[Pillar]] = mapped_column(ARRAY(PILLAR_ENUM), nullable=False)
    review_pillars: Mapped[list[Pillar]] = mapped_column(ARRAY(PILLAR_ENUM), nullable=False)
    can_view_salary: Mapped[bool] = mapped_column(Boolean, nullable=False)
    home_route: Mapped[str] = mapped_column(Text, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """ENT-User — 05 §4.1. One demo user = one fixed role (M6)."""

    __tablename__ = "users"
    __table_args__ = (
        # 05 §4.1: UQ `email` partial `WHERE deleted_at IS NULL`.
        Index(
            "uq_users_email",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # 05 §4.1: email is stored lowercase.
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    email: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    salutation: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    is_demo_account: Mapped[bool] = mapped_column(Boolean, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    role: Mapped[Role] = relationship(back_populates="users", lazy="joined")

    @validates("email")
    def _normalize_email(self, _key: str, value: str) -> str:
        return value.strip().lower()

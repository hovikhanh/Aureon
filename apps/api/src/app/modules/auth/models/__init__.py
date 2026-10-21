"""Schema `auth` — 3 tables (05 §4.1). Column groups follow 05 §2.1."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    CHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ConfigModel, LogModel, SoftDeleteMixin
from app.core.columns import fk, schema_args, sr, txt
from app.core.enums import DATA_CLASSIFICATION, PILLAR, ROLE_CODE

S = "auth"
TS = DateTime(timezone=True)


class Role(ConfigModel):
    """ENT-Role — seeded 10 rows; permissions are a text[] (no Permission entity, DEC-150)."""

    __tablename__ = "roles"
    __table_args__ = schema_args(S)

    code: Mapped[str] = mapped_column(ROLE_CODE, nullable=False, unique=True)
    role_ref: Mapped[str] = txt(unique=True)
    name_vi: Mapped[str] = txt()
    name_en: Mapped[str] = txt()
    permissions: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    scope_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    pillars: Mapped[list[str]] = mapped_column(ARRAY(PILLAR), nullable=False)


class User(ConfigModel, SoftDeleteMixin):
    """ENT-User — identity group: version + data_classification (CONFIDENTIAL), no `source`."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("locale IN ('vi', 'en')", name="locale_vi_en"),
        {"schema": S},
    )

    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    password_hash: Mapped[str] = txt()
    full_name: Mapped[str] = txt()
    role_id: Mapped[uuid.UUID] = fk(f"{S}.roles.id")
    department_id: Mapped[uuid.UUID | None] = sr()
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, unique=True, index=True
    )
    locale: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'vi'"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_service_account: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    last_login_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    failed_login_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    locked_until: Mapped[datetime | None] = mapped_column(TS, nullable=True)

    # 05 §2.1: identity rows are level 3 by default.
    data_classification: Mapped[str] = mapped_column(
        DATA_CLASSIFICATION, nullable=False, server_default="CONFIDENTIAL"
    )


class RefreshToken(LogModel):
    """ENT-RefreshToken — append-only; revoke via `revoked_at`, never deleted."""

    __tablename__ = "refresh_tokens"
    __table_args__ = schema_args(S)

    user_id: Mapped[uuid.UUID] = fk(f"{S}.users.id")
    token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    user_agent: Mapped[str | None] = txt(nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)

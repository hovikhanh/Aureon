"""Pydantic DTOs for `auth` (10 §4.1). `password_hash` never appears in any response."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Pragmatic RFC 5322 subset (10 §1.1); `email-validator` is not an approved dependency.
EMAIL_PATTERN = r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$"


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=256)


class RefreshIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=16, max_length=512)


class UserOut(BaseModel):
    """10 §4.1 UserOut."""

    id: uuid.UUID
    email: str
    full_name: str
    role_code: str
    role_id: uuid.UUID
    permissions: list[str]
    department_id: uuid.UUID | None
    locale: str
    is_active: bool
    last_login_at: datetime | None


class TokenOut(BaseModel):
    """EP-02 / EP-06 response `data`."""

    access_token: str
    token_type: Literal["Bearer"] = Field(default="Bearer")
    expires_in: int
    refresh_token: str
    user: UserOut


# ---------- M1.2 T-614 admin (EP-ADM-05..11, 10 §7.2.1) ----------
RoleCode = Literal["CEO", "DIR", "MGR", "EMP", "REV", "ADM", "AI"]
PillarCode = Literal["F", "O", "C", "U", "S"]
Locale = Literal["vi", "en"]


class UserAdminOut(BaseModel):
    """EP-ADM-05 `UserAdminOut` — never `password_hash`."""

    id: uuid.UUID
    email: str
    full_name: str
    role_id: uuid.UUID
    role_code: str
    scope_pillars: list[str]
    department_id: uuid.UUID | None
    employee_id: uuid.UUID | None
    locale: str
    is_active: bool
    is_service_account: bool
    last_login_at: datetime | None
    locked_until: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254, pattern=EMAIL_PATTERN)
    full_name: str = Field(min_length=1, max_length=200)
    role_code: RoleCode
    scope_pillars: list[PillarCode] = Field(default_factory=list)
    department_id: uuid.UUID | None = None
    employee_id: uuid.UUID | None = None
    locale: Locale = "vi"
    initial_password: str = Field(min_length=12, max_length=256, repr=False)


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    role_code: RoleCode | None = None
    scope_pillars: list[PillarCode] | None = None
    department_id: uuid.UUID | None = None
    employee_id: uuid.UUID | None = None
    locale: Locale | None = None
    version: int | None = None


class ReasonIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)


class RoleOut(BaseModel):
    id: uuid.UUID
    code: str
    role_ref: str
    name_vi: str
    name_en: str
    permissions: list[str]
    scope_rules: dict[str, object]
    pillars: list[str]

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

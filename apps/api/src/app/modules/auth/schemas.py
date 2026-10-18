"""UserOut / RoleOut response models — 10 EP-02 (reused by EP-03..05). T-101, for T-104.

`password_hash` is deliberately absent (10 §1.8 DS6; CLAUDE.md FastAPI gotcha).
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.envelope import Envelope
from app.db.enums import Pillar, RoleKey


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    key: RoleKey
    name_i18n_key: str
    pillar_scope: list[Pillar]
    pillar_agg_scope: list[Pillar]
    review_pillars: list[Pillar]
    can_view_salary: bool
    home_route: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    salutation: Literal["anh", "chị"] | None
    role: RoleOut
    is_demo_account: bool


class LoginRequest(BaseModel):
    """EP-02 request body — 10 EP-02 request table. `password` is never logged or echoed."""

    # `str` (not pydantic EmailStr): email-validator is not a dependency (no new deps, CLAUDE.md).
    # A malformed/unknown email is not 422 here — it yields the same 401 INVALID_CREDENTIALS as a
    # wrong password (no user enumeration, 10 EP-02). `email` is stored lowercase (05 §4.1).
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginData(BaseModel):
    """EP-02 `data` payload — 10 EP-02 Response 200 (`access_token`, `token_type`, `expires_at`)."""

    access_token: str
    # S105 false positive: "Bearer" is the OAuth token *scheme* name (10 EP-02), not a secret.
    token_type: Literal["Bearer"] = "Bearer"  # noqa: S105
    expires_at: datetime
    user: UserOut


# Declared response_model for EP-02 (CLAUDE.md § API; contract check_response_envelopes).
LoginEnvelope = Envelope[LoginData]

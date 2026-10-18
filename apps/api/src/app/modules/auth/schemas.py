"""UserOut / RoleOut response models — 10 EP-02 (reused by EP-03..05). T-101, for T-104.

`password_hash` is deliberately absent (10 §1.8 DS6; CLAUDE.md FastAPI gotcha).
"""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

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

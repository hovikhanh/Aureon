"""Static seed reference data: 5 roles (02 §3, 05 §4.2) + 5 demo users (08 §2). T-101.

The scope columns are backend-filter reference data (05 §4.2, M2); the full permission
matrix stays a code constant (02 §3). Passwords are NOT here — they are read at seed time
from ``ConfigService.demo_*_password`` and hashed with argon2id (DEC-116). No secrets in code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.db.enums import Pillar, RoleKey


@dataclass(frozen=True)
class RoleSeed:
    """One row of ``roles`` (05 §4.2)."""

    code: str
    key: RoleKey
    name_i18n_key: str
    pillar_scope: list[Pillar]
    pillar_agg_scope: list[Pillar]
    review_pillars: list[Pillar]
    can_view_salary: bool
    home_route: str


@dataclass(frozen=True)
class UserSeed:
    """One row of ``users`` (08 §2).

    ``account_key`` is the non-sensitive token that identifies the demo account's password env
    var: the seed reads ``ConfigService.demo_<account_key>_password`` (e.g. ``ceo`` →
    ``DEMO_CEO_PASSWORD``). The password value itself is never stored here (08 §2).
    """

    external_id: str
    email: str
    full_name: str
    salutation: str | None
    role_code: str
    account_key: str
    is_demo_account: bool = field(default=True)


# 05 §4.2 scope columns, sourced from 02 §4.2 / §3.4 and 06 §2.3 routes:
# - pillar_scope: pillars at `view` level.
# - pillar_agg_scope: pillars at `view-agg` level.
# - review_pillars: pillars the role may approve/commit/undo (02 §3.4).
# - can_view_salary: true only for HR Manager (05 §4.2); Reviewer handles salary per review
#   context (§10), so the column stays false.
# - home_route: 06 §2.3 (ROLE-01..04 → /dashboard, ROLE-05 → /inbox = IDP queue).
ROLES: tuple[RoleSeed, ...] = (
    RoleSeed(
        code="ROLE-01",
        key=RoleKey.CEO,
        name_i18n_key="shell.roles.CEO",
        pillar_scope=[Pillar.FIN, Pillar.CUS, Pillar.OPS, Pillar.HR],
        pillar_agg_scope=[],
        review_pillars=[],
        can_view_salary=False,
        home_route="/dashboard",
    ),
    RoleSeed(
        code="ROLE-02",
        key=RoleKey.CFO,
        name_i18n_key="shell.roles.CFO",
        pillar_scope=[Pillar.FIN, Pillar.OPS],
        pillar_agg_scope=[Pillar.CUS, Pillar.HR],
        review_pillars=[Pillar.FIN],
        can_view_salary=False,
        home_route="/dashboard",
    ),
    RoleSeed(
        code="ROLE-03",
        key=RoleKey.SALES_DIRECTOR,
        # CUS + revenue metrics of FIN (02 §4.2): scope is CUS and FIN at view level.
        name_i18n_key="shell.roles.SALES_DIRECTOR",
        pillar_scope=[Pillar.CUS, Pillar.FIN],
        pillar_agg_scope=[Pillar.OPS],
        review_pillars=[],
        can_view_salary=False,
        home_route="/dashboard",
    ),
    RoleSeed(
        code="ROLE-04",
        key=RoleKey.HR_MANAGER,
        name_i18n_key="shell.roles.HR_MANAGER",
        pillar_scope=[Pillar.HR, Pillar.OPS],
        pillar_agg_scope=[Pillar.FIN],
        review_pillars=[Pillar.HR],
        can_view_salary=True,
        home_route="/dashboard",
    ),
    RoleSeed(
        code="ROLE-05",
        key=RoleKey.REVIEWER,
        # Reviewer has no dashboard pillars (02 §3.7, §4.2): only the IDP review queue.
        name_i18n_key="shell.roles.REVIEWER",
        pillar_scope=[],
        pillar_agg_scope=[],
        review_pillars=[Pillar.FIN, Pillar.CUS, Pillar.OPS, Pillar.HR],
        can_view_salary=False,
        home_route="/inbox",
    ),
)

# 08 §2 — 5 demo accounts. salutation per P04 (08 §2 "Ông/Bà/Cô/Anh"): anh=male, chị=female.
USERS: tuple[UserSeed, ...] = (
    UserSeed(
        external_id="acc-ceo",
        email="ceo@abc.demo",
        full_name="Nguyễn Văn An",
        salutation="anh",
        role_code="ROLE-01",
        account_key="ceo",
    ),
    UserSeed(
        external_id="acc-cfo",
        email="cfo@abc.demo",
        full_name="Trần Thị Minh",
        salutation="chị",
        role_code="ROLE-02",
        account_key="cfo",
    ),
    UserSeed(
        external_id="acc-sales",
        email="sales@abc.demo",
        full_name="Lê Hoàng Giang",
        salutation="anh",
        role_code="ROLE-03",
        account_key="sales",
    ),
    UserSeed(
        external_id="acc-hr",
        email="hr@abc.demo",
        full_name="Phạm Thị Hạnh",
        salutation="chị",
        role_code="ROLE-04",
        account_key="hr",
    ),
    UserSeed(
        external_id="acc-reviewer",
        email="reviewer@abc.demo",
        full_name="Vũ Đức Thắng",
        salutation="anh",
        role_code="ROLE-05",
        account_key="reviewer",
    ),
)

"""HR data scoping + level-4 visibility (02 §6.2–6.3) — one source of truth for REST, dashboard
and (later) AI tools.

- CEO, HR_MANAGER: whole company, level-4 visible.
- MANAGER: own department (`d`); level-4 masked.
- EMPLOYEE: own profile only (`o`), matched by the JWT e-mail (DEC-196); level-4 masked.
- REVIEWER: `hr:read ◑r` = only records of an assigned review — assignments arrive with IDP
  (T-4xx), so until then every employee / hiring-plan read is `403 FORBIDDEN_SCOPE` (DEC-196).
- Everyone else reaching an `hr:query` endpoint (CFO, RISK_MANAGER, CEO): company aggregates.
"""

import uuid

from app.core.deps import Principal
from app.core.errors import ScopeDeniedError

LEVEL4_ROLES = frozenset({"CEO", "HR_MANAGER"})
# Aggregate payroll fund (not individual salary): CEO, HR_MANAGER, CFO (02 §6.2, 05 §4.4).
PAYROLL_AGGREGATE_ROLES = frozenset({"CEO", "HR_MANAGER", "CFO"})
DEPARTMENT_ROLES = frozenset({"MANAGER"})
SELF_ROLES = frozenset({"EMPLOYEE"})
NO_RECORD_ROLES = frozenset({"REVIEWER"})


def sees_level4(user: Principal) -> bool:
    return user.role in LEVEL4_ROLES


def sees_payroll(user: Principal) -> bool:
    return user.role in PAYROLL_AGGREGATE_ROLES


def deny(what: str, **details: object) -> ScopeDeniedError:
    return ScopeDeniedError(
        f"{what} outside your scope", details={k: str(v) for k, v in details.items()}
    )


def department_scope(user: Principal, requested: uuid.UUID | None) -> uuid.UUID | None:
    """Effective `department_id` filter for a list; MANAGER is pinned to their department."""
    if user.role in NO_RECORD_ROLES:
        raise deny("hr records", role=user.role)
    if user.role in DEPARTMENT_ROLES:
        if user.department_id is None or (
            requested is not None and requested != user.department_id
        ):
            raise deny("department", department_id=requested)
        return user.department_id
    return requested


def check_department(user: Principal, department_id: uuid.UUID | None) -> None:
    """Single record check (MANAGER: own department only)."""
    if user.role in NO_RECORD_ROLES:
        raise deny("hr records", role=user.role)
    if user.role in DEPARTMENT_ROLES and department_id != user.department_id:
        raise deny("department", department_id=department_id)

"""Risk data scope (02 §5.3, §6.2; DEC-219) — one source of truth for REST, dashboard, AI tools.

- CEO, CFO, RISK_MANAGER: whole register (`risk:read ●`).
- VP_SALES / HR_MANAGER / CPO (`◑l` linked to their domain): a risk is visible when its
  `linked_entities` holds a key of their domain or its category is their domain category.
- MANAGER (`◑d`): risks of their own department; writes pinned to it.
- REVIEWER (`◑r`): review assignments arrive with IDP (T-4xx) → every read is
  `403 FORBIDDEN_SCOPE` until then (same approach as DEC-196).
"""

import uuid
from typing import Any

from sqlalchemy import ColumnElement, Text, or_
from sqlalchemy.dialects.postgresql import array

from app.core.deps import Principal
from app.core.errors import ScopeDeniedError
from app.modules.risk.models import Risk

FULL_READERS = frozenset({"CEO", "CFO", "RISK_MANAGER"})
DEPARTMENT_ROLES = frozenset({"MANAGER"})
NO_RECORD_ROLES = frozenset({"REVIEWER"})
# role → (linked_entities keys, categories) of "their" domain (02 §6.2 table).
LINKED: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "VP_SALES": (("deal_id", "client_id", "contract_id"), ("customer",)),
    "HR_MANAGER": (("hiring_plan_id", "employee_id", "department_id"), ("people",)),
    "CPO": (("product_id", "feature_id", "roadmap_item_id"), ("product",)),
}


def deny(what: str, **details: object) -> ScopeDeniedError:
    return ScopeDeniedError(
        f"{what} outside your scope", details={k: str(v) for k, v in details.items()}
    )


def read_filter(user: Principal) -> list[ColumnElement[bool]]:
    """SQL predicates restricting a risk list to the caller's scope."""
    if user.role in FULL_READERS:
        return []
    if user.role in DEPARTMENT_ROLES:
        if user.department_id is None:
            raise deny("risk register", role=user.role)
        return [Risk.department_id == user.department_id]
    if user.role in LINKED:
        keys, cats = LINKED[user.role]
        return [or_(Risk.linked_entities.has_any(array(keys, type_=Text)), Risk.category.in_(cats))]
    raise deny("risk register", role=user.role)


def can_read(user: Principal, risk: Risk) -> bool:
    if user.role in FULL_READERS:
        return True
    if user.role in DEPARTMENT_ROLES:
        return user.department_id is not None and risk.department_id == user.department_id
    if user.role in LINKED:
        keys, cats = LINKED[user.role]
        links: dict[str, Any] = risk.linked_entities or {}
        return risk.category in cats or any(k in links for k in keys)
    return False


def check_read(user: Principal, risk: Risk) -> None:
    if not can_read(user, risk):
        raise deny("risk", risk_id=risk.id)


def check_write(user: Principal, risk: Risk) -> None:
    """`risk:write` holders: RISK_MANAGER (●) or MANAGER (◑d)."""
    if user.role in DEPARTMENT_ROLES and risk.department_id != user.department_id:
        raise deny("risk", risk_id=risk.id)


def pin_department(user: Principal, requested: uuid.UUID | None) -> uuid.UUID | None:
    """MANAGER creates risks for their own department only."""
    if user.role not in DEPARTMENT_ROLES:
        return requested
    if user.department_id is None or requested not in (None, user.department_id):
        raise deny("department", department_id=requested)
    return user.department_id

"""Risk data scope (02 §5.3, §6.2; DEC-219) — one source of truth for REST, dashboard, AI tools.

- CEO, Risk-DIR (S), Finance-DIR (F): whole register (`risk:read ●`).
- Sales-DIR (C) / HR-DIR (O) / Product-DIR (U) (`◑l` linked to their domain): a risk is visible
  when its `linked_entities` holds a key of their domain or its category is their domain category.
- MGR (`◑d`): risks of their own department; writes pinned to it.
- REV (`◑r`): review assignments arrive with IDP (T-4xx) → every read is
  `403 FORBIDDEN_SCOPE` until then (same approach as DEC-196).

R-DEC-12a: 5 C-level nền v2.1 gộp vào ROLE-DIR; phân biệt khối bằng `scope_pillars`
(ex CFO→DIR+F, RISK_MANAGER→DIR+S, VP_SALES→DIR+C, HR_MANAGER→DIR+O, CPO→DIR+U).
"""

import uuid
from typing import Any

from sqlalchemy import ColumnElement, Text, or_
from sqlalchemy.dialects.postgresql import array

from app.core.deps import Principal
from app.core.errors import ScopeDeniedError
from app.modules.risk.models import Risk

DEPARTMENT_ROLES = frozenset({"MGR"})
NO_RECORD_ROLES = frozenset({"REV"})
# pillar → (linked_entities keys, categories) of "their" domain (02 §6.2) — R-DEC-12a.
LINKED_BY_PILLAR: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "C": (("deal_id", "client_id", "contract_id"), ("customer",)),  # ex VP_SALES
    "O": (("hiring_plan_id", "employee_id", "department_id"), ("people",)),  # ex HR_MANAGER
    "U": (("product_id", "feature_id", "roadmap_item_id"), ("product",)),  # ex CPO
}
_FULL_PILLARS = frozenset({"S", "F"})  # Risk/Finance-DIR → full register (ex RISK_MANAGER/CFO)


def _is_full_reader(user: Principal) -> bool:
    if user.role == "CEO":
        return True
    full = not user.scope_pillars or bool(_FULL_PILLARS & user.scope_pillars)
    return user.role == "DIR" and full


def _linked_domains(user: Principal) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    """Merge the (keys, categories) of the DIR's linked pillars (C/O/U); None if not linked DIR."""
    if user.role != "DIR":
        return None
    pillars = user.scope_pillars or frozenset(LINKED_BY_PILLAR)
    keys: tuple[str, ...] = ()
    cats: tuple[str, ...] = ()
    for p in pillars:
        if p in LINKED_BY_PILLAR:
            k, c = LINKED_BY_PILLAR[p]
            keys += k
            cats += c
    return (keys, cats) if keys or cats else None


def deny(what: str, **details: object) -> ScopeDeniedError:
    return ScopeDeniedError(
        f"{what} outside your scope", details={k: str(v) for k, v in details.items()}
    )


def read_filter(user: Principal) -> list[ColumnElement[bool]]:
    """SQL predicates restricting a risk list to the caller's scope."""
    if _is_full_reader(user):
        return []
    if user.role in DEPARTMENT_ROLES:
        if user.department_id is None:
            raise deny("risk register", role=user.role)
        return [Risk.department_id == user.department_id]
    linked = _linked_domains(user)
    if linked is not None:
        keys, cats = linked
        return [or_(Risk.linked_entities.has_any(array(keys, type_=Text)), Risk.category.in_(cats))]
    raise deny("risk register", role=user.role)


def can_read(user: Principal, risk: Risk) -> bool:
    if _is_full_reader(user):
        return True
    if user.role in DEPARTMENT_ROLES:
        return user.department_id is not None and risk.department_id == user.department_id
    linked = _linked_domains(user)
    if linked is not None:
        keys, cats = linked
        links: dict[str, Any] = risk.linked_entities or {}
        return risk.category in cats or any(k in links for k in keys)
    return False


def check_read(user: Principal, risk: Risk) -> None:
    if not can_read(user, risk):
        raise deny("risk", risk_id=risk.id)


def check_write(user: Principal, risk: Risk) -> None:
    """`risk:write` holders: Risk-DIR (●) or MGR (◑d)."""
    if user.role in DEPARTMENT_ROLES and risk.department_id != user.department_id:
        raise deny("risk", risk_id=risk.id)


def pin_department(user: Principal, requested: uuid.UUID | None) -> uuid.UUID | None:
    """MANAGER creates risks for their own department only."""
    if user.role not in DEPARTMENT_ROLES:
        return requested
    if user.department_id is None or requested not in (None, user.department_id):
        raise deny("department", department_id=requested)
    return user.department_id

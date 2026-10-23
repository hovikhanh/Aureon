"""Execution data scope (02 §5.3, §6.2) — one source of truth for REST, dashboard, AI tools.

02 §5.3 marks per role (mirrored from `auth.permission_matrix.ROLE_SCOPES`, which `execution`
may not import — DEC-125):
- CEO: everything (`●`); DIR `execution:query` is `●` (workload of the company).
- `◑d` (DIR = ex CFO/VP_SALES/HR_MANAGER/CPO/RISK_MANAGER, MGR): rows of their own
  department **plus** rows where they are the owner / assignee / chair / attendee (DEC-220).
- `◑o` (EMP): only rows where they are owner / assignee (task), chair / attendee
  (meeting), owner (decision, objective, KR, KPI, initiative).
A `◑d` caller without `department_id` in the JWT keeps only the "own" part.
Role codes v3 (R-DEC-12): CEO/DIR/MGR/EMP/REV/ADM/AI.
"""

import uuid
from collections.abc import Iterable
from typing import Any, Literal

from sqlalchemy import ColumnElement, false, or_

from app.core.deps import Principal
from app.core.errors import ScopeDeniedError

Level = Literal["all", "d", "o"]

_D_ROLES = frozenset({"DIR", "MGR"})  # ex 5 C-level + MANAGER (R-DEC-12)
_O_ROLES = frozenset({"EMP"})
_FULL_QUERY = frozenset({"CEO", "DIR"})  # ex {CEO, HR_MANAGER}; HR_MANAGER → DIR


def level(user: Principal, action: str = "read") -> Level:
    if user.role in _O_ROLES:
        return "o"
    if action == "query" and user.role in _FULL_QUERY:
        return "all"
    if user.role in _D_ROLES:
        return "d"
    return "all"


def deny(what: str, **details: object) -> ScopeDeniedError:
    return ScopeDeniedError(
        f"{what} outside your scope", details={k: str(v) for k, v in details.items()}
    )


def predicate(
    user: Principal, action: str, *, dept: Any = None, own: Iterable[ColumnElement[bool]] = ()
) -> ColumnElement[bool] | None:
    """SQL filter for a list (`None` = unrestricted). `own` = "row is mine" clauses."""
    lvl = level(user, action)
    if lvl == "all":
        return None
    clauses = list(own)
    if lvl == "d" and dept is not None and user.department_id is not None:
        clauses.append(dept == user.department_id)
    return or_(*clauses) if clauses else false()


def allowed(
    user: Principal, action: str, *, dept: uuid.UUID | None, owners: Iterable[uuid.UUID | None]
) -> bool:
    lvl = level(user, action)
    if lvl == "all":
        return True
    if user.user_id in set(owners):
        return True
    return lvl == "d" and dept is not None and dept == user.department_id


def check(
    user: Principal, action: str, *, dept: uuid.UUID | None, owners: Iterable[uuid.UUID | None],
    what: str = "record",
) -> None:  # fmt: skip
    if not allowed(user, action, dept=dept, owners=owners):
        raise deny(what, department_id=dept)


def pin_department(user: Principal, requested: uuid.UUID | None) -> uuid.UUID | None:
    """Department of a new / moved row: `◑d` may only use their own department."""
    lvl = level(user, "write")
    if lvl == "all":
        return requested
    if lvl == "o":
        if requested is not None and requested != user.department_id:
            raise deny("department", department_id=requested)
        return user.department_id
    if user.department_id is None or requested not in (None, user.department_id):
        raise deny("department", department_id=requested)
    return user.department_id


def require_self(user: Principal, *ids: uuid.UUID | None, field: str) -> None:
    """EMPLOYEE (`◑o`) may only name themselves in owner / assignee fields."""
    if level(user, "write") == "o" and any(i is not None and i != user.user_id for i in ids):
        raise deny(field, field=field)

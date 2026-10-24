"""Goal data scope (R-DEC-57, 10 §7.2.3) — Strategy / StrategicObjective now, KPI/OKR at T-632.

Skeleton (T-626): `execution/services/scope.py` stays unchanged (M1.3 shares it). This module
holds the M1.4 rules that already have data to act on:

- **Strategy:** every `execution:read` caller reads (company level); only CEO writes →
  others `403 FORBIDDEN_ROLE`.
- **StrategicObjective:** read = CEO all; others = company level (`department_id IS NULL`) ∪
  own department ∪ owner ∪ (DIR) `pillar ∈ scope_pillars` (empty `scope_pillars` → all).
  Write = CEO; DIR only when `pillar ∈ scope_pillars` (empty → all) → else `403 FORBIDDEN_SCOPE`;
  MGR / EMP → `403 FORBIDDEN_ROLE`.

T-632 adds the department subtree (`core/org_scope.py department_subtree()`, DIR "khối" / MGR
"team" = department + children), EMP restricted ancestors and the KPI/OKR/check-in rules; until
then a department means the caller's own `department_id` only.
"""

import uuid
from typing import Any

from sqlalchemy import ColumnElement, or_

from app.core.deps import Principal
from app.core.errors import PermissionDeniedError
from app.modules.execution.services.scope import deny, self_ids

FULL = frozenset({"CEO"})
SO_WRITERS = frozenset({"CEO", "DIR"})


def _pillar_ok(user: Principal, pillar: str | None) -> bool:
    """DIR pillar rule: empty `scope_pillars` = every pillar (10 §7.2.3)."""
    return not user.scope_pillars or (pillar is not None and pillar in user.scope_pillars)


def require_strategy_writer(user: Principal) -> None:
    if user.role not in FULL:
        raise PermissionDeniedError("only CEO writes strategies", details={"rule": "R-DEC-57"})


def so_predicate(
    user: Principal, *, dept: Any, owner: Any, pillar: Any
) -> ColumnElement[bool] | None:
    """List filter for strategic objectives (`None` = unrestricted)."""
    if user.role in FULL:
        return None
    clauses: list[ColumnElement[bool]] = [dept.is_(None), owner.in_(self_ids(user))]
    if user.department_id is not None:
        clauses.append(dept == user.department_id)
    if user.role == "DIR":
        if not user.scope_pillars:
            return None
        clauses.append(pillar.in_(sorted(user.scope_pillars)))
    return or_(*clauses)


def so_readable(
    user: Principal, *, dept: uuid.UUID | None, owner: uuid.UUID, pillar: str | None
) -> bool:
    if user.role in FULL or dept is None or owner in self_ids(user):
        return True
    if dept == user.department_id:
        return True
    return user.role == "DIR" and _pillar_ok(user, pillar)


def check_so_read(
    user: Principal, *, dept: uuid.UUID | None, owner: uuid.UUID, pillar: str | None
) -> None:
    if not so_readable(user, dept=dept, owner=owner, pillar=pillar):
        raise deny("strategic objective")


def check_so_write(user: Principal, pillar: str | None) -> None:
    if user.role not in SO_WRITERS:
        raise PermissionDeniedError(
            "only CEO / DIR write strategic objectives", details={"rule": "R-DEC-57"}
        )
    if user.role == "DIR" and not _pillar_ok(user, pillar):
        raise deny("strategic objective", pillar=pillar, rule="R-DEC-57")

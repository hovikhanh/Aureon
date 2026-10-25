"""Goal data scope (R-DEC-57, 10 §7.2.3) — Strategy / SO / KPI / OKR / Initiative / check-in.

`execution/services/scope.py` stays unchanged (M1.3 tasks share it). `await resolve(db, user)`
builds a `GoalScope` once per call; the department subtree comes from `core/org_scope.py`
(`hr` registers the provider — `execution` never imports `hr`).

- **Read:** CEO all · DIR = khối (own department subtree) ∪ `pillar ∈ scope_pillars` (empty →
  all) ∪ own ∪ company level (`department_id IS NULL`) · MGR = department subtree ∪ own ∪
  company level · EMP = own only (`owner_id` ∈ {user id, employee id}, R-DEC-41); the tree adds
  their ancestors as `restricted` nodes. Strategy: everyone with `execution:read`.
- **Write KPI / Objective / KR / Initiative:** CEO all · DIR / MGR rows of the department
  subtree or their own (company-level rows read-only); `pin_department` accepts any department
  of the subtree · EMP → `403 FORBIDDEN_ROLE`.
- **Check-in (EP-PRF-02/04):** CEO all · DIR / MGR like write (on behalf, `user_id` = caller) ·
  EMP only KR / KPI they own → else `403 FORBIDDEN_SCOPE`.
- **Strategy:** CEO only → `403 FORBIDDEN_ROLE`. **SO:** CEO; DIR when `pillar ∈ scope_pillars`
  (empty → all) → else `403 FORBIDDEN_SCOPE`; MGR / EMP → `403 FORBIDDEN_ROLE`.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import ColumnElement, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import PermissionDeniedError
from app.core.org_scope import department_subtree
from app.modules.execution.services.scope import deny, self_ids

Action = Literal["read", "write", "check_in"]
FULL = frozenset({"CEO"})
SO_WRITERS = frozenset({"CEO", "DIR"})
DEPT_ROLES = frozenset({"DIR", "MGR"})
OWN_ROLES = frozenset({"EMP"})
RULE = "R-DEC-57"


def _pillar_ok(user: Principal, pillar: str | None) -> bool:
    """DIR pillar rule: empty `scope_pillars` = every pillar (10 §7.2.3)."""
    return not user.scope_pillars or (pillar is not None and pillar in user.scope_pillars)


def _role_denied(what: str) -> PermissionDeniedError:
    return PermissionDeniedError(f"your role cannot write {what}", details={"rule": RULE})


@dataclass(frozen=True)
class GoalScope:
    user: Principal
    departments: frozenset[uuid.UUID]  # DIR / MGR: own department + sub-departments

    @property
    def full(self) -> bool:
        return self.user.role not in DEPT_ROLES | OWN_ROLES  # CEO

    @property
    def me(self) -> tuple[uuid.UUID, ...]:
        return self_ids(self.user)

    def mine(self, owners: Iterable[uuid.UUID | None]) -> bool:
        return bool(set(self.me) & set(owners))

    # ---------- read ----------
    def readable(
        self, *, dept: uuid.UUID | None, owners: Iterable[uuid.UUID | None],
        pillar: str | None = None,
    ) -> bool:  # fmt: skip
        if self.full or self.mine(owners):
            return True
        if self.user.role in OWN_ROLES:
            return False
        if dept is None or dept in self.departments:
            return True
        return self.user.role == "DIR" and _pillar_ok(self.user, pillar)

    def predicate(self, *, dept: Any, owner: Any, pillar: Any = None) -> ColumnElement[bool] | None:
        """List filter (`None` = unrestricted)."""
        if self.full or (self.user.role == "DIR" and not self.user.scope_pillars):
            return None
        clauses: list[ColumnElement[bool]] = [owner.in_(self.me)]
        if self.user.role in DEPT_ROLES:
            clauses.append(dept.is_(None))
            if self.departments:
                clauses.append(dept.in_(sorted(self.departments)))
            if self.user.role == "DIR" and pillar is not None:
                clauses.append(pillar.in_(sorted(self.user.scope_pillars)))
        return or_(*clauses)

    # ---------- write / check-in ----------
    def allows(
        self, action: Action, *, dept: uuid.UUID | None, owners: Iterable[uuid.UUID | None],
        pillar: str | None = None,
    ) -> bool:  # fmt: skip
        owners = tuple(owners)
        if action == "read":
            return self.readable(dept=dept, owners=owners, pillar=pillar)
        if self.full:
            return True
        if self.user.role in OWN_ROLES:
            return action == "check_in" and self.mine(owners)
        return self.mine(owners) or (dept is not None and dept in self.departments)

    def check(
        self, action: Action, *, dept: uuid.UUID | None, owners: Iterable[uuid.UUID | None],
        pillar: str | None = None, what: str = "record",
    ) -> None:  # fmt: skip
        owners = tuple(owners)
        if action == "write" and self.user.role in OWN_ROLES:
            if not self.readable(dept=dept, owners=owners, pillar=pillar):
                raise deny(what, department_id=dept)
            raise _role_denied(what)
        if not self.allows(action, dept=dept, owners=owners, pillar=pillar):
            raise deny(what, department_id=dept)

    def require_writer(self, what: str) -> None:
        """Create / edit KPI / Objective / KR / Initiative: EMP → `403 FORBIDDEN_ROLE`."""
        if self.user.role in OWN_ROLES:
            raise _role_denied(what)

    def pin_department(self, requested: uuid.UUID | None) -> uuid.UUID | None:
        """Department of a new / moved row: DIR / MGR any department of their subtree."""
        if self.full:
            return requested
        self.require_writer("goals")
        if requested is None:
            if self.user.department_id is None:
                raise deny("department", department_id=requested)
            return self.user.department_id
        if requested not in self.departments:
            raise deny("department", department_id=requested)
        return requested

    def check_department_filter(self, department_id: uuid.UUID | None) -> None:
        """`department_id` query filter inside the caller's scope → else `403 FORBIDDEN_SCOPE`."""
        if department_id is None or self.full:
            return
        ok = (department_id in self.departments if self.user.role in DEPT_ROLES
              else department_id == self.user.department_id)  # fmt: skip
        if not ok:
            raise deny("department", department_id=department_id)


async def resolve(db: AsyncSession, user: Principal) -> GoalScope:
    if user.role in DEPT_ROLES and user.department_id is not None:
        depts = await department_subtree(db, (user.department_id,))
        return GoalScope(user, frozenset(depts))
    return GoalScope(user, frozenset())


# ---------- Strategy / StrategicObjective ----------
def require_strategy_writer(user: Principal) -> None:
    if user.role not in FULL:
        raise PermissionDeniedError("only CEO writes strategies", details={"rule": RULE})


def so_predicate(
    gs: GoalScope, *, dept: Any, owner: Any, pillar: Any
) -> ColumnElement[bool] | None:
    """List filter for strategic objectives: company level readable by every role."""
    pred = gs.predicate(dept=dept, owner=owner, pillar=pillar)
    return None if pred is None else or_(dept.is_(None), pred)


def so_readable(
    gs: GoalScope, *, dept: uuid.UUID | None, owner: uuid.UUID, pillar: str | None
) -> bool:
    return dept is None or gs.readable(dept=dept, owners=(owner,), pillar=pillar)


def check_so_read(
    gs: GoalScope, *, dept: uuid.UUID | None, owner: uuid.UUID, pillar: str | None
) -> None:
    if not so_readable(gs, dept=dept, owner=owner, pillar=pillar):
        raise deny("strategic objective")


def check_so_write(user: Principal, pillar: str | None) -> None:
    if user.role not in SO_WRITERS:
        raise PermissionDeniedError(
            "only CEO / DIR write strategic objectives", details={"rule": RULE}
        )
    if user.role == "DIR" and not _pillar_ok(user, pillar):
        raise deny("strategic objective", pillar=pillar, rule=RULE)

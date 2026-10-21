"""Sales data scope (02 §5.3, §6.2) — one source of truth for REST, dashboard and AI tools.

- MANAGER (`◑d`): deals of their own department only; new deals are pinned to it; contracts
  only through a deal of their department; clients/targets have no `department_id` → master
  data readable, client create allowed (needed to open a deal), other client/target writes
  denied (DEC-193).
- CEO `sales:write ◑t`: writes **targets only** — any other sales write → `FORBIDDEN_SCOPE`.
- Deal delete: VP_SALES only (FR-SAL-01) → `FORBIDDEN_ROLE` for everyone else.
- `sales:query` without `sales:read` (`○`, CFO/CPO/RISK_MANAGER): aggregates only — per-owner
  breakdowns are refused (02 §6.1 #5).
"""

import uuid

from app.core.deps import Principal
from app.core.errors import PermissionDeniedError, ScopeDeniedError

DEPARTMENT_SCOPED_ROLES = frozenset({"MANAGER"})
TARGET_ONLY_WRITERS = frozenset({"CEO"})
DEAL_DELETERS = frozenset({"VP_SALES"})


def is_department_scoped(user: Principal) -> bool:
    return user.role in DEPARTMENT_SCOPED_ROLES


def check_department(user: Principal, department_id: uuid.UUID | None) -> None:
    if is_department_scoped(user) and department_id != user.department_id:
        raise ScopeDeniedError(
            "deal outside your department", details={"department_id": str(department_id)}
        )


def require_record_writer(user: Principal) -> None:
    """Writes on clients / deals / stage / contracts (everything except targets)."""
    if user.role in TARGET_ONLY_WRITERS:
        raise ScopeDeniedError("sales:write is limited to revenue targets for this role")


def require_full_writer(user: Principal) -> None:
    """Update / delete of master data without a department (clients) — MANAGER excluded."""
    require_record_writer(user)
    if is_department_scoped(user):
        raise ScopeDeniedError("record has no department — outside your scope")


def require_deal_deleter(user: Principal) -> None:
    if user.role not in DEAL_DELETERS:
        raise PermissionDeniedError("only VP_SALES may delete deals (FR-SAL-01)")


def require_target_writer(user: Principal) -> None:
    if is_department_scoped(user):
        raise ScopeDeniedError("targets are company-level — outside your scope")


def require_detail_reader(user: Principal) -> None:
    """Per-person breakdowns need `sales:read` (02 §6.1 #5)."""
    if not user.has("sales:read"):
        raise ScopeDeniedError("aggregate-only access: per-owner breakdown not allowed")

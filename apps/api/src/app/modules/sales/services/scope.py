"""Sales data scope (02 §5.3, §6.2) — one source of truth for REST, dashboard and AI tools.

- MGR (`◑d`): deals of their own department only; new deals are pinned to it; contracts
  only through a deal of their department; clients/targets have no `department_id` → master
  data readable, client create allowed (needed to open a deal), other client/target writes
  denied (DEC-193).
- REV (`◑r`): only inside an assigned review session; every general sales read →
  `FORBIDDEN_SCOPE` (D-07, same pattern as hr / product / risk).
- CEO: full create / update / delete on every sales record (D-21, R-DEC-198 — replaces the
  former `◑t` "targets only" mark).
- Deal delete: Sales-DIR or CEO (ex VP_SALES, FR-SAL-01; D-21) → `FORBIDDEN_ROLE` for everyone
  else.
- `sales:query` without `sales:read` (`○`, non-Sales DIR): aggregates only — per-owner
  breakdowns are refused (02 §6.1 #5).

R-DEC-12a: VP_SALES → DIR phụ trách khối C (sales); phân biệt bằng `scope_pillars`.
"""

import uuid

from app.core.deps import Principal
from app.core.errors import PermissionDeniedError, ScopeDeniedError

DEPARTMENT_SCOPED_ROLES = frozenset({"MGR"})
REVIEW_SCOPED_ROLES = frozenset({"REV"})


def is_department_scoped(user: Principal) -> bool:
    return user.role in DEPARTMENT_SCOPED_ROLES


def _is_sales_dir(user: Principal) -> bool:
    """Sales director: DIR phụ trách khối C (scope_pillars rỗng = toàn khối)."""
    return user.role == "DIR" and (not user.scope_pillars or "C" in user.scope_pillars)


def check_department(user: Principal, department_id: uuid.UUID | None) -> None:
    if is_department_scoped(user) and department_id != user.department_id:
        raise ScopeDeniedError(
            "deal outside your department", details={"department_id": str(department_id)}
        )


def require_record_reader(user: Principal) -> None:
    if user.role in REVIEW_SCOPED_ROLES:
        raise ScopeDeniedError("sales records are readable only inside an assigned review")


def require_record_writer(user: Principal) -> None:
    """Writes on clients / deals / stage / contracts (everything except targets).

    Kept as the single hook for record-level write rules; every `sales:write` holder passes
    today (CEO included since D-21).
    """


def require_full_writer(user: Principal) -> None:
    """Update / delete of master data without a department (clients) — MANAGER excluded."""
    require_record_writer(user)
    if is_department_scoped(user):
        raise ScopeDeniedError("record has no department — outside your scope")


def require_deal_deleter(user: Principal) -> None:
    if not (_is_sales_dir(user) or user.role == "CEO"):
        raise PermissionDeniedError("only the sales director or the CEO may delete deals")


def require_target_writer(user: Principal) -> None:
    if is_department_scoped(user):
        raise ScopeDeniedError("targets are company-level — outside your scope")


def require_detail_reader(user: Principal) -> None:
    """Per-person breakdowns cần quyền đọc chi tiết khối C (02 §6.1 #5).

    Nền v2.1: vai ngoài khối có `sales:query` nhưng không có `sales:read`. Khi gộp về DIR
    union (R-DEC-12a) ta tái lập ranh giới bằng khối: chỉ Sales-DIR / CEO xem được breakdown.
    """
    if not (user.has("sales:read") and user.in_pillar("sales")):
        raise ScopeDeniedError("aggregate-only access: per-owner breakdown not allowed")

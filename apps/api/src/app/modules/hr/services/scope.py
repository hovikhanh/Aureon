"""HR data scoping + level-4 visibility (02 §6.2–6.3) — one source of truth for REST, dashboard
and (later) AI tools.

- CEO, HR-DIR (DIR phụ trách khối O): whole company, level-4 visible.
- MGR: own department (`d`); level-4 masked.
- EMP: own profile only (`o`), matched by the JWT e-mail (DEC-196); level-4 masked.
- REV: `hr:read ◑r` = only records of an assigned review — assignments arrive with IDP
  (T-4xx), so until then every employee / hiring-plan read is `403 FORBIDDEN_SCOPE` (DEC-196).
- Everyone else reaching an `hr:query` endpoint (Finance-DIR, CEO): company aggregates.

R-DEC-12a: 5 C-level nền v2.1 gộp vào ROLE-DIR; phân biệt khối bằng `scope_pillars`.
Level-4 lương chỉ CEO + HR-DIR (DIR có pillar `O`) — không nới cho DIR khối khác.
"""

import uuid

from app.core.deps import Principal
from app.core.errors import ScopeDeniedError

DEPARTMENT_ROLES = frozenset({"MGR"})
SELF_ROLES = frozenset({"EMP"})
NO_RECORD_ROLES = frozenset({"REV"})


def _dir_with_pillar(user: Principal, pillar: str) -> bool:
    """DIR phụ trách khối `pillar` (scope_pillars rỗng = toàn khối, dùng cho role cấp cao)."""
    return user.role == "DIR" and (not user.scope_pillars or pillar in user.scope_pillars)


def sees_level4(user: Principal) -> bool:
    # CEO toàn phần; HR-DIR (khối O) thấy level-4 (02 §6.2). ex-HR_MANAGER → DIR+O.
    return user.role == "CEO" or _dir_with_pillar(user, "O")


def sees_payroll(user: Principal) -> bool:
    # Quỹ lương tổng (không phải lương cá nhân): CEO + HR-DIR (O) + Finance-DIR (F) (02 §6.2).
    return user.role == "CEO" or _dir_with_pillar(user, "O") or _dir_with_pillar(user, "F")


# Dashboard HR (headcount/attrition) mở cho CEO + DIR khối O/F/S (People/Finance/Risk quan tâm
# nhân sự); DIR khối C/U (Sales/Product) KHÔNG xem → FORBIDDEN_ROLE. Nền v2.1: hr:query chỉ
# CEO/CFO/HR_MANAGER/RISK_MANAGER có — R-DEC-12a tái lập bằng scope_pillars.
_HR_DASHBOARD_PILLARS = frozenset({"O", "F", "S"})


def sees_hr_dashboard(user: Principal) -> bool:
    if user.role != "DIR":
        return True  # CEO/MGR… do permission dependency + department scope quyết định
    return not user.scope_pillars or bool(_HR_DASHBOARD_PILLARS & user.scope_pillars)


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

"""Product data scope (02 §5.3, §6.2 — DEC-212). One source of truth for REST and AI tools.

- Product rows (products, features, roadmap, releases, metrics) carry no `department_id`.
- MGR (`◑d`): reads / dashboard allowed (catalog data, INTERNAL); any write →
  `403 FORBIDDEN_SCOPE` (no department to pin the record to — default deny).
- REV (`◑r`): record reads only inside an assigned review (IDP, T-4xx) → until then
  `403 FORBIDDEN_SCOPE` (same as DEC-196).
Role codes v3 (R-DEC-12): MANAGER→MGR, REVIEWER→REV.
"""

from app.core.deps import Principal
from app.core.errors import ScopeDeniedError

DEPARTMENT_SCOPED_ROLES = frozenset({"MGR"})
REVIEW_SCOPED_ROLES = frozenset({"REV"})


def require_reader(user: Principal) -> None:
    if user.role in REVIEW_SCOPED_ROLES:
        raise ScopeDeniedError("product records are readable only inside an assigned review")
    # R-DEC-12a: DIR ngoài khối U chỉ xem tổng hợp (product:query), không đọc bản ghi chi tiết.
    if not user.in_pillar("product"):
        raise ScopeDeniedError("product records are outside your pillar scope")


def require_writer(user: Principal) -> None:
    if user.role in DEPARTMENT_SCOPED_ROLES:
        raise ScopeDeniedError("product records have no department — outside your scope")

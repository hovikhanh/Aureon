"""Permission catalog `<domain>:<action>` (02 §5.1–5.2, 10 §2.2).

Only the permissions listed here exist; anything else is undefined → default deny. The
role × permission matrix lives in the `auth` module (seed source); `core` only knows the catalog
so `require_permission` can reject typos at import time.
"""

DOMAINS: tuple[str, ...] = (
    "finance", "sales", "hr", "product", "risk", "execution", "idp", "ai", "dashboard", "platform",
)  # fmt: skip
ACTIONS: tuple[str, ...] = ("read", "write", "query", "approve", "admin")

# 02 §5.2 (+ §5.6 `platform:approve`).
VALID_PERMISSIONS: frozenset[str] = frozenset(
    {
        "finance:read", "finance:write", "finance:query",
        "sales:read", "sales:write", "sales:query",
        "hr:read", "hr:write", "hr:query", "hr:approve",
        "product:read", "product:write", "product:query",
        "risk:read", "risk:write", "risk:query", "risk:approve",
        "execution:read", "execution:write", "execution:query",
        "idp:read", "idp:write", "idp:approve", "idp:admin",
        "ai:query", "ai:write", "ai:admin",
        "dashboard:read", "dashboard:write", "dashboard:admin",
        "platform:read", "platform:approve", "platform:admin",
    }
)  # fmt: skip


def permission_name(domain: str, action: str | None = None) -> str:
    """Normalise `("finance", "read")` or `("finance:read",)` and validate against 02 §5.2."""
    perm = domain if action is None else f"{domain}:{action}"
    if perm not in VALID_PERMISSIONS:
        raise ValueError(f"undefined permission {perm!r} (02 §5.2)")
    return perm


# Domain ↔ pillar F.O.C.U.S (R-DEC-12a): dùng để thu hẹp ROLE-DIR theo khối phụ trách.
# Domain không có trong map là cross-pillar (execution, idp, ai, dashboard, platform) → không lọc.
DOMAIN_PILLAR: dict[str, str] = {
    "finance": "F",
    "hr": "O",
    "sales": "C",
    "product": "U",
    "risk": "S",
}


def pillar_allows(scope_pillars: frozenset[str], perm: str) -> bool:
    """R-DEC-12a: khối (`scope_pillars`) KHÔNG lọc ở tầng permission — luôn True.

    Nền v2.1 cô lập khối theo cách KHÔNG đồng nhất giữa các domain (VD Finance-DIR được
    duyệt kế hoạch tuyển dụng như một cổng ngân sách; Sales-DIR đọc được risk gắn với
    sales; nhưng sales/finance/hr chặn executive ngoài khối đọc bản ghi chi tiết). Một
    cổng pillar toàn cục không biểu diễn được sự bất đối xứng đó, nên việc cô lập khối của
    ROLE-DIR gộp được giao cho tầng data-scope mỗi module (`services/scope.py`) và cho các
    helper khối-aware (`Principal.in_pillar`, `dashboard.visible_pillars`,
    `product.require_reader`, `sales.require_pillar_permission`). Dữ liệu mức 4 (lương) vẫn
    do `hr/scope.py` giữ chặt (chỉ CEO + HR-DIR). Giữ hàm này để tương thích chữ ký `has()`.
    """
    return True

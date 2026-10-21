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

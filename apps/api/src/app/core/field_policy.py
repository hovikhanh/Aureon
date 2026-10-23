"""Field-level security registry (T-615, R-DEC-34, 05 §2.4, 02 §5–§6.3) — one source of truth.

Every API field that carries level 3 (Mật) or level 4 (Tuyệt mật) data is declared here once.
The same registry drives:

* serializers of every module — `mask_fields(entity, principal, values)` replaces a hidden
  field with `{ "masked": true }` (10 §7.2.1);
* `core.audit.MASKED_KEYS` (before/after masking) and `core.events.outbox` forbidden payload
  keys — via `SENSITIVE_KEYS`;
* the LLM PII filter — `strip_for_model(payload)` drops level-4 keys and pseudonymises level-3
  keys of tool results before they enter a prompt (CLAUDE.md §5.5).

Level-2 entries are listed explicitly (reviewed, not sensitive) so the schema scan test can
prove no sensitive-looking field escapes the registry. `core` imports no module: visibility
rules are expressed on the `Principal` fields (role, scope_pillars).
"""

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel

Level = Literal[2, 3, 4]
# Who may see the real value (besides the data scope already enforced by the service):
# - "level4": CEO + DIR khối O (02 §6.2; REV in an assigned review session — IDP, later).
# - "record": any caller that passed the record data scope, except structure-only roles (ADM
#   with `hr:read ◑s`, R-DEC-30).
# - "account_admin": the account owner or a platform admin (`auth.users.email`).
# - "all": no mask (level 2).
Audience = Literal["level4", "record", "account_admin", "all"]


class Masked(BaseModel):
    """Placeholder for a field the caller may not see (02 §6.3, 10 §7.2.1)."""

    masked: Literal[True] = True


class _Principal(Protocol):
    @property
    def role(self) -> str: ...
    @property
    def scope_pillars(self) -> frozenset[str]: ...


@dataclass(frozen=True)
class FieldRule:
    entity: str  # `<schema>.<table>` (05)
    field: str  # API field name (10)
    level: Level
    audience: Audience
    note: str = ""


def _rules(
    entity: str, level: Level, audience: Audience, *fields: str, note: str = ""
) -> list[FieldRule]:
    return [FieldRule(entity, f, level, audience, note) for f in fields]


FIELD_POLICY: tuple[FieldRule, ...] = (
    *_rules("hr.employees", 4, "level4",
            "date_of_birth", "address", "national_id", "bank_account", "emergency_contact"),
    *_rules("hr.salary_history", 4, "level4", "base_salary",
            note="list gated by FORBIDDEN_SALARY (EP-83)"),
    *_rules("hr.employees", 3, "record", "email", "phone"),
    *_rules("auth.users", 3, "account_admin", "email",
            note="ADM (platform:read) + owner (/auth/me); never in event/email body"),
    *_rules("sales.contacts", 3, "record", "email", "phone",
            note="client contact — pseudonymised CLI-xxxx for the LLM"),
    *_rules("hr.hiring_plans", 2, "all", "salary_min", "salary_max",
            note="recruitment budget range, not an individual's salary"),
    *_rules("hr.organizations", 2, "all", "tax_code", note="public company identifier"),
    *_rules("sales.clients", 2, "all", "tax_code", "address", note="business, not personal"),
    *_rules("finance.invoices", 2, "all", "counterparty_tax_code", note="business identifier"),
)  # fmt: skip

LEVEL4_KEYS: frozenset[str] = frozenset(r.field for r in FIELD_POLICY if r.level == 4)
LEVEL3_KEYS: frozenset[str] = frozenset(r.field for r in FIELD_POLICY if r.level == 3)
SENSITIVE_KEYS: frozenset[str] = LEVEL4_KEYS | LEVEL3_KEYS
STRUCTURE_ONLY_ROLES = frozenset({"ADM"})  # R-DEC-30 (`hr:read ◑s`)


def rules_for(entity: str) -> tuple[FieldRule, ...]:
    return tuple(r for r in FIELD_POLICY if r.entity == entity and r.level >= 3)


def sees_level4(user: _Principal) -> bool:
    """CEO toàn phần; DIR khối O (scope rỗng = toàn khối) — 02 §6.2."""
    return user.role == "CEO" or (
        user.role == "DIR" and (not user.scope_pillars or "O" in user.scope_pillars)
    )


def visible(user: _Principal, rule: FieldRule, *, owner: bool = False) -> bool:
    if rule.audience == "all":
        return True
    if rule.audience == "level4":
        return sees_level4(user)
    if rule.audience == "record":
        return user.role not in STRUCTURE_ONLY_ROLES
    return owner or user.role == "ADM" or user.role == "CEO"


def mask_fields(
    entity: str, user: _Principal | None, values: Mapping[str, Any], *, owner: bool = False
) -> dict[str, Any]:
    """Copy of `values` with every registry field the caller may not see → `Masked()`.

    `user=None` = trusted internal view (audit before/after — masked again by `core.audit`).
    """
    out = dict(values)
    if user is None:
        return out
    for rule in rules_for(entity):
        if rule.field in out and not visible(user, rule, owner=owner):
            out[rule.field] = Masked()
    return out


def _token(value: Any, prefix: str) -> str:
    digest = hashlib.sha256(str(value).encode()).hexdigest()[:4].upper()
    return f"{prefix}-{digest}"


def strip_for_model(payload: Any, *, client_keys: Iterable[str] = ()) -> Any:
    """LLM PII filter on structured data: drop level-4 keys, pseudonymise level-3 keys.

    `client_keys` = parent keys whose level-3 children belong to external parties (→ `CLI-`).
    """
    clients = frozenset(client_keys)

    def walk(node: Any, prefix: str) -> Any:
        if isinstance(node, Mapping):
            out: dict[str, Any] = {}
            for k, v in node.items():
                key = str(k).lower()
                if key in LEVEL4_KEYS:
                    continue
                if key in LEVEL3_KEYS and v is not None and not isinstance(v, Mapping):
                    out[k] = _token(v, prefix)
                    continue
                out[k] = walk(v, "CLI" if key in clients else prefix)
            return out
        if isinstance(node, list | tuple):
            return [walk(v, prefix) for v in node]
        return node

    return walk(payload, "EMP")

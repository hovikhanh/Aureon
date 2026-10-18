"""PostgreSQL ENUM types shared across modules (05 §6; C10: Python PascalCase, SCREAMING values).

Each Python enum maps 1-1 to a PostgreSQL ENUM type of the same snake_case name. Adding or
changing a value is a schema change: update 05 §6 first, then a reversible migration.
"""

from enum import StrEnum


class Pillar(StrEnum):
    """`pillar` — the 4 dashboard pillars (roles, source_documents, business_records, metrics)."""

    FIN = "FIN"
    CUS = "CUS"
    OPS = "OPS"
    HR = "HR"


class RoleKey(StrEnum):
    """`role_key` — value used by ``require_role(...)`` (10 §1.4)."""

    CEO = "CEO"
    CFO = "CFO"
    SALES_DIRECTOR = "SALES_DIRECTOR"
    HR_MANAGER = "HR_MANAGER"
    REVIEWER = "REVIEWER"


class ActorType(StrEnum):
    """`actor_type` — who performed an audited action (audit_logs)."""

    USER = "USER"
    AI = "AI"
    SYSTEM = "SYSTEM"

"""Deterministic seed ids shared by every module seed (cross-schema refs without FKs).

`seed_uuid("department", "SAL")`, `seed_uuid("client", "0309876543")` (client by tax code),
`seed_uuid("employee", "EMP-0001")`, … — same input → same UUID on every run (idempotent).
"""

import uuid

SEED_NAMESPACE = uuid.UUID("6d1f3c8e-2a4b-5c6d-8e9f-a0b1c2d3e4f5")


def seed_uuid(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"aureon.seed.{kind}.{key}")

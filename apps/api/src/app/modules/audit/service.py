"""Append-only audit service — 10 §1.7, 05 §4.12, §10 S6 (T-102; FR-DC-22).

The only write path to ``audit_logs``:

- ``record_audit`` *adds* an ``AuditLog`` to the caller's session and flushes nothing / commits
  nothing: the row lives or dies with the caller's transaction (TC-SYS-005).
- Salary values in ``before`` / ``after`` / ``metadata`` are replaced by ``SALARY_MASK``.
- ``metadata.request_id`` is filled from the current request (``X-Request-Id``).

There is intentionally no update/delete function. A ``before_flush`` guard (models.py) rejects
ORM updates/deletes of audit rows, and the DB trigger from migration 0003 rejects raw SQL ones.
"""

import ipaddress
import uuid
from collections.abc import Mapping
from typing import Any

from pydantic_core import to_jsonable_python
from sqlalchemy.orm import Session

from app.core.request_id import get_request_id
from app.db.enums import ActorType
from app.modules.audit.models import AuditLog, AuditLogImmutableError

SALARY_MASK = "••••"
# 05 §4.8 `business_records.salary` and schema field `salary` (05 §4.6, §9.2) are SALARY.
SALARY_KEYS: frozenset[str] = frozenset({"salary"})
# 05 §4.6 `extracted_fields`: when `sensitivity='SALARY'` these keys carry the salary value.
SALARY_VALUE_KEYS: frozenset[str] = frozenset(
    {"value", "raw_text", "corrected_value", "final_value"}
)
SALARY_SENSITIVITY = "SALARY"

JsonDict = dict[str, Any]
IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address

__all__ = ["SALARY_MASK", "AuditLogImmutableError", "mask_salary", "record_audit"]


def _is_salary_record(data: Mapping[str, Any]) -> bool:
    sensitivity = data.get("sensitivity")
    if isinstance(sensitivity, str) and sensitivity.upper() == SALARY_SENSITIVITY:
        return True
    field_key = data.get("field_key")
    return isinstance(field_key, str) and field_key.lower() in SALARY_KEYS


def mask_salary(value: Any) -> Any:
    """Return a JSON-compatible copy of ``value`` with every salary value masked (05 §10 S6).

    Masked: any key named ``salary`` (any depth), and the value-carrying keys of an object
    labelled ``sensitivity='SALARY'`` (or ``field_key='salary'``) such as an extracted field.
    """
    if isinstance(value, Mapping):
        salary_record = _is_salary_record(value)
        masked: JsonDict = {}
        for key, item in value.items():
            name = str(key)
            if name.lower() in SALARY_KEYS or (salary_record and name in SALARY_VALUE_KEYS):
                masked[name] = SALARY_MASK
            else:
                masked[name] = mask_salary(item)
        return masked
    if isinstance(value, list | tuple):
        return [mask_salary(item) for item in value]
    return value


def _to_json(value: Mapping[str, Any] | None) -> JsonDict | None:
    if value is None:
        return None
    # uuid/datetime/Decimal/Enum → JSON primitives so the dict fits in jsonb.
    jsonable = to_jsonable_python(dict(value))
    masked: JsonDict = mask_salary(jsonable)
    return masked


def _ip(value: str | IpAddress | None) -> IpAddress | None:
    if value is None or isinstance(value, ipaddress.IPv4Address | ipaddress.IPv6Address):
        return value
    return ipaddress.ip_address(value)


def record_audit(
    db: Session,
    *,
    action: str,
    target_type: str,
    actor_type: ActorType = ActorType.USER,
    actor_user_id: uuid.UUID | None = None,
    actor_role_id: uuid.UUID | None = None,
    target_id: uuid.UUID | None = None,
    source_document_id: uuid.UUID | None = None,
    before: Mapping[str, Any] | None = None,
    after: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    ip_address: str | IpAddress | None = None,
    idempotency_key: str | None = None,
) -> AuditLog:
    """Add one audit row to ``db`` (same transaction as the mutation; does NOT flush/commit).

    ``actor_user_id`` is required for ``USER`` actors and must be ``None`` for ``AI`` /
    ``SYSTEM`` (05 §4.12). ``metadata.request_id`` / ``metadata.idempotency_key`` are filled
    from the current request / argument unless already present (10 §1.7).
    """
    if not action or not target_type:
        raise ValueError("action and target_type are required")
    if actor_type is ActorType.USER and actor_user_id is None:
        raise ValueError("actor_user_id is required when actor_type is USER")
    if actor_type is not ActorType.USER and actor_user_id is not None:
        raise ValueError("actor_user_id must be None for AI/SYSTEM actors")

    meta: JsonDict = dict(metadata or {})
    request_id = get_request_id()
    if request_id is not None:
        meta.setdefault("request_id", request_id)
    if idempotency_key is not None:
        meta.setdefault("idempotency_key", idempotency_key)

    entry = AuditLog(
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        actor_role_id=actor_role_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        source_document_id=source_document_id,
        before=_to_json(before),
        after=_to_json(after),
        metadata_=_to_json(meta) if meta else None,
        ip_address=_ip(ip_address),
    )
    db.add(entry)
    return entry

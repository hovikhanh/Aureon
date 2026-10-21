"""`ENT-AuditLog` writer (10 §1.8, 05 `platform.audit_logs`) — append-only.

Three layers keep the log immutable:
1. DB trigger `trg_audit_logs_immutable` (migration 0001) rejects UPDATE/DELETE for any role.
2. DB role `app_audit_writer` (migration 0007) has only `INSERT, SELECT` — defense in depth;
   the app still connects as the shared role in S0 (05: "app DB user chỉ có INSERT, SELECT").
3. Code: this module and `AuditRepository` expose only insert + read; the `AuditLog` mapper
   refuses ORM UPDATE/DELETE (platform/models/audit_guard.py).

`record_audit` writes in the caller's session → same transaction as the mutation; rollback
removes both. `@auditable(action, entity)` wraps a service method to do it automatically.
"""

import functools
import uuid
from collections.abc import Awaitable, Callable, Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from sqlalchemy import column, insert, table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import TableClause

from app.core.enums import ACTOR_TYPE, ROLE_CODE
from app.core.pii import MASK, mask_payload
from app.core.request_context import current_request_id

__all__ = [
    "MASK", "SYSTEM", "Actor", "auditable", "current_actor", "mask", "record_audit", "set_actor",
]  # fmt: skip

ActorType = Literal["USER", "AI", "SYSTEM"]

# Level 3–4 fields masked in before/after (10 §1.8, 02 §6.3).
MASKED_KEYS: frozenset[str] = frozenset(
    {
        "salary", "base_salary", "gross_salary", "net_salary", "salary_amount", "allowance",
        "date_of_birth", "address", "national_id", "cccd", "bank_account",
        "bank_account_number", "emergency_contact", "password", "password_hash", "token",
        "refresh_token", "token_hash", "access_token",
    }
)  # fmt: skip

AUDIT_LOGS: TableClause = table(
    "audit_logs",
    column("id"),
    column("occurred_at"),
    column("actor_type", ACTOR_TYPE),
    column("actor_user_id"),
    column("on_behalf_of"),
    column("actor_role", ROLE_CODE),
    column("action"),
    column("target_schema"),
    column("target_table"),
    column("target_id"),
    column("source_document_id"),
    column("before", JSONB),
    column("after", JSONB),
    column("why"),
    column("metadata", JSONB),
    schema="platform",
)


@dataclass(frozen=True)
class Actor:
    type: ActorType = "SYSTEM"
    user_id: uuid.UUID | None = None
    role: str | None = None
    on_behalf_of: uuid.UUID | None = None


SYSTEM = Actor()
_actor: ContextVar[Actor] = ContextVar("audit_actor", default=SYSTEM)


def set_actor(actor: Actor) -> None:
    """Set by `get_current_user` for the request; workers default to `SYSTEM`."""
    _actor.set(actor)


def current_actor() -> Actor:
    return _actor.get()


def mask(value: Any) -> Any:
    """Level 3–4 keys → `••••`; PII inside strings (CCCD, phone, e-mail, account) masked.

    Never raises — an audit row must always be writable (DEC-176).
    """
    return mask_payload(value, masked_keys=MASKED_KEYS)


def _validate_action(action: str) -> None:
    module, _, verb = action.partition(".")
    if not module or not verb:
        raise ValueError(f"audit action {action!r} must be <module>.<verb> (10 §1.8)")


async def record_audit(
    session: AsyncSession,
    *,
    action: str,
    target_schema: str | None = None,
    target_table: str | None = None,
    target_id: uuid.UUID | None = None,
    before: Any = None,
    after: Any = None,
    why: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    actor: Actor | None = None,
) -> uuid.UUID:
    """INSERT one audit row in the caller's transaction (no commit). Returns its id."""
    _validate_action(action)
    who = actor or current_actor()
    meta: dict[str, Any] = {"request_id": current_request_id()}
    meta.update(metadata or {})
    audit_id = uuid.uuid4()
    await session.execute(
        insert(AUDIT_LOGS).values(
            id=audit_id,
            actor_type=who.type,
            actor_user_id=who.user_id,
            on_behalf_of=who.on_behalf_of,
            actor_role=who.role,
            action=action,
            target_schema=target_schema,
            target_table=target_table,
            target_id=target_id,
            before=mask(before),
            after=mask(after),
            why=why,
            metadata=mask(meta),
        )
    )
    return audit_id


class _HasSession(Protocol):
    db: AsyncSession


def _target_id(result: Any) -> uuid.UUID | None:
    value = getattr(result, "id", None)
    return value if isinstance(value, uuid.UUID) else None


def _snapshot(result: Any) -> Any:
    dump = getattr(result, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    return None


def auditable[R](
    action: str, entity: str
) -> Callable[[Callable[..., Awaitable[R]]], Callable[..., Awaitable[R]]]:
    """Decorate an async service method on a class with `self.db: AsyncSession`.

    After the method returns (before the caller commits) one audit row is written in the same
    session: `action`, `target_schema.target_table` from `entity` ("finance.invoices"),
    `target_id` = `result.id`, `after` = `result.model_dump()` (masked) for Pydantic results.
    An exception in the method → no audit row (and the caller's rollback drops the change).
    """
    _validate_action(action)
    schema, _, tbl = entity.partition(".")
    if not schema or not tbl:
        raise ValueError(f"audit entity {entity!r} must be <schema>.<table>")

    def deco(fn: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
        @functools.wraps(fn)
        async def wrapper(self: _HasSession, *args: Any, **kwargs: Any) -> R:
            result = await fn(self, *args, **kwargs)
            await record_audit(
                self.db,
                action=action,
                target_schema=schema,
                target_table=tbl,
                target_id=_target_id(result),
                after=_snapshot(result),
            )
            return result

        return wrapper

    return deco

"""Tenant context (R-DEC-13/21, 05 §2.3) — the tenant of the current unit of work.

Set from the JWT `tenant_id` claim (request), the event envelope (Celery consumer) or the
per-tenant loop of a beat job. Business data is filtered by TWO independent layers:

1. `BaseRepository` adds `WHERE tenant_id = :tenant` / assigns `tenant_id` explicitly.
2. A `Session` hook (`install_tenant_guard`) adds the same criteria to EVERY ORM statement
   touching a `TenantMixin` entity (aggregates, joins, bulk UPDATE/DELETE) and stamps new
   rows on flush.

Both fail closed: no tenant context → `TenantContextMissingError`, never an implicit default.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria
from sqlalchemy.sql.util import find_tables

from app.core.base_model import DEFAULT_TENANT_ID, Base, TenantMixin
from app.core.errors import AppError

_current_tenant: ContextVar[uuid.UUID | None] = ContextVar("current_tenant", default=None)


class TenantContextMissingError(AppError):
    """Programming/infra error: tenant-scoped data touched outside a tenant context (500)."""


class TenantMismatchError(AppError):
    """A row of another tenant was about to be written in this tenant's context (500)."""


def current_tenant() -> uuid.UUID | None:
    return _current_tenant.get()


def require_tenant() -> uuid.UUID:
    tenant = _current_tenant.get()
    if tenant is None:
        raise TenantContextMissingError("no tenant context (fail closed, R-DEC-21)")
    return tenant


def set_tenant(tenant_id: uuid.UUID | None) -> Token[uuid.UUID | None]:
    return _current_tenant.set(tenant_id)


def reset_tenant(token: Token[uuid.UUID | None]) -> None:
    _current_tenant.reset(token)


@contextmanager
def tenant_scope(tenant_id: uuid.UUID) -> Iterator[uuid.UUID]:
    """Run a block (consumer, job, seed, script) as `tenant_id`; restores the previous value."""
    token = _current_tenant.set(tenant_id)
    try:
        yield tenant_id
    finally:
        _current_tenant.reset(token)


def active_tenant_ids() -> tuple[uuid.UUID, ...]:
    """Tenants a beat job iterates over. MVP is single-tenant (R-DEC-07): no tenant registry
    exists in 05 yet, so the only active tenant is the fixed system tenant."""
    return (DEFAULT_TENANT_ID,)


def _tenant_tables() -> frozenset[Any]:
    return frozenset(
        m.local_table
        for m in Base.registry.mappers
        if issubclass(m.class_, TenantMixin) and m.local_table is not None
    )


def _touches_tenant_data(statement: Any) -> bool:
    found = find_tables(
        statement, check_columns=True, include_aliases=True, include_joins=True,
        include_selects=True, include_crud=True,
    )  # fmt: skip
    tenant_tables = _tenant_tables()
    return any(getattr(t, "element", t) in tenant_tables for t in found)


def _on_execute(state: ORMExecuteState) -> None:
    """Layer 2: every ORM SELECT/UPDATE/DELETE gets `tenant_id = current_tenant`."""
    if state.is_column_load or state.is_relationship_load:
        return  # criteria propagate from the parent query
    if not (state.is_select or state.is_update or state.is_delete):
        return
    tenant = current_tenant()
    if tenant is None:
        if _touches_tenant_data(state.statement):
            raise TenantContextMissingError("tenant-scoped query without tenant context")
        return
    state.statement = state.statement.options(
        with_loader_criteria(TenantMixin, lambda cls: cls.tenant_id == tenant, include_aliases=True)
    )


def _on_flush(session: Session, _ctx: Any, _instances: Any) -> None:
    """Layer 2 (writes): stamp new tenant rows; refuse rows of another tenant."""
    for obj in session.new:
        if not isinstance(obj, TenantMixin):
            continue
        tenant = require_tenant()
        if obj.tenant_id is None:
            obj.tenant_id = tenant
        elif obj.tenant_id != tenant:
            raise TenantMismatchError("row tenant differs from tenant context")


class TenantContextMiddleware:
    """Each HTTP request starts WITHOUT a tenant (fail closed until the JWT is verified) and
    the caller's context is restored afterwards — in-process transports (tests) share the task."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        token = _current_tenant.set(None)
        try:
            await self.app(scope, receive, send)
        finally:
            _current_tenant.reset(token)


_installed = False


def install_tenant_guard() -> None:
    """Idempotent; called once at import of `core.tenant` (all `Session`s, sync + async)."""
    global _installed
    if _installed:
        return
    event.listen(Session, "do_orm_execute", _on_execute)
    event.listen(Session, "before_flush", _on_flush)
    _installed = True


install_tenant_guard()

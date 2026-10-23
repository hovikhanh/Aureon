"""Shared helpers for HR integration tests (unique codes: the DB is shared, rows roll back)."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_LOGS
from app.core.events.envelope import OUTBOX
from tests.conftest import ApiClient

# ex 10-role F.O.C.U.S → 7-role v3 (+ scope_pillars khối) — R-DEC-12/12a.
_LEGACY: dict[str, tuple[str, tuple[str, ...]]] = {
    "CEO": ("CEO", ()), "CFO": ("DIR", ("F",)), "VP_SALES": ("DIR", ("C",)),
    "HR_MANAGER": ("DIR", ("O",)), "CPO": ("DIR", ("U",)), "RISK_MANAGER": ("DIR", ("S",)),
    "MANAGER": ("MGR", ()), "EMPLOYEE": ("EMP", ()), "REVIEWER": ("REV", ()), "ADMIN": ("ADM", ()),
}  # fmt: skip


def token_headers(role: str, *, email: str, department_id: Any = None) -> dict[str, str]:
    """Like `ApiClient.headers` but with a chosen e-mail (EMPLOYEE self-scope, DEC-196)."""
    from app.core.security import sign_access_token
    from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

    v3, pillars = _LEGACY.get(role, (role, ()))
    token, _ = sign_access_token(
        user_id=uuid.uuid4(), email=email, role=v3, role_id=v3,
        permissions=list(ROLE_PERMISSIONS[v3]), department_id=department_id,
        scope_pillars=pillars,
    )  # fmt: skip
    return {"Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid.uuid4())}


def uniq(prefix: str = "T") -> str:
    return f"{prefix}{uuid.uuid4().hex[:10].upper()}"


async def make_department(api: ApiClient, **kw: Any) -> dict[str, Any]:
    body = {"name": "Phòng thử", "code": uniq("D"), **kw}
    r = await api.call("POST", "/hr/departments", "HR_MANAGER", json=body)
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


def employee_body(dept: str, **kw: Any) -> dict[str, Any]:
    code = uniq("E")
    return {
        "employee_code": code, "full_name": "Nguyễn Văn An", "email": f"{code.lower()}@abc.test",
        "department_id": dept, "title": "Kế toán viên", "contract_type": "full_time",
        "status": "probation", "hire_date": "2025-01-15", "date_of_birth": "1990-05-01",
        "address": "12 Lê Lợi, Q1", "national_id": "079090001234", "bank_account": "0123456789012",
        **kw,
    }  # fmt: skip


async def make_employee(api: ApiClient, dept: str, **kw: Any) -> dict[str, Any]:
    r = await api.call("POST", "/hr/employees", "HR_MANAGER", json=employee_body(dept, **kw))
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


async def events(db: AsyncSession, aggregate_id: str, event_type: str | None = None) -> list[Any]:
    stmt = select(OUTBOX.c.event_type, OUTBOX.c.payload).where(
        OUTBOX.c.aggregate_id == uuid.UUID(aggregate_id)
    )
    if event_type:
        stmt = stmt.where(OUTBOX.c.event_type == event_type)
    return list((await db.execute(stmt)).all())


async def audit_rows(db: AsyncSession, target_id: str) -> list[Any]:
    stmt = select(AUDIT_LOGS.c.action, AUDIT_LOGS.c.before, AUDIT_LOGS.c.after).where(
        AUDIT_LOGS.c.target_id == uuid.UUID(target_id)
    )
    return list((await db.execute(stmt)).all())

"""Public service interface of `hr` — the only entry point for other modules.

T-121: EP-81 departments, EP-82 employees, EP-83 salary history. Every mutation writes
`ENT-AuditLog` in the caller's transaction (level-4 keys masked by `core.audit`); events go
through `publish_in_tx` with ids + dates only — never a salary amount or PII (10 §8.1,
FR-HR-02). The route commits.
"""

import re
import unicodedata
import uuid
from datetime import date
from typing import Any, cast

from sqlalchemy import ColumnElement, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.base_model import Base
from app.core.deps import Principal
from app.core.errors import (
    BusinessRuleError,
    DuplicateResourceError,
    NotFoundError,
    SalaryDeniedError,
)
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.hr.models import Department, Employee, SalaryHistory
from app.modules.hr.repositories import (
    DepartmentRepository,
    EmployeeRepository,
    PositionRepository,
    SalaryRepository,
)
from app.modules.hr.schemas import (
    ContractType,
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeOut,
    EmployeeStatus,
    EmployeeUpdate,
    Masked,
    SalaryCreate,
    SalaryOut,
)
from app.modules.hr.services.scope import (
    SELF_ROLES,
    check_department,
    deny,
    department_scope,
    sees_level4,
)

# 10 §4.8 API enum ↔ 05 `hr.contract_type` (DEC-195).
CONTRACT_TO_DB: dict[str, str] = {
    "full_time": "permanent", "part_time": "contractor", "contract": "fixed_term",
    "intern": "intern",
}  # fmt: skip
CONTRACT_FROM_DB: dict[str, ContractType] = {
    "permanent": "full_time", "probation": "full_time", "contractor": "part_time",
    "fixed_term": "contract", "intern": "intern",
}  # fmt: skip
LEVEL4_FIELDS = ("date_of_birth", "address", "national_id", "bank_account", "emergency_contact")
ONBOARD_FROM = frozenset({None, "probation", "terminated"})
MAX_TREE_DEPTH = 256


def normalize_name(name: str) -> str:
    """Lowercase, accent-free, single-spaced (trigram matching XD-03)."""
    text = unicodedata.normalize("NFKD", name.replace("đ", "d").replace("Đ", "D"))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().lower()


def department_out(d: Department) -> DepartmentOut:
    return DepartmentOut(
        id=d.id, version=d.version, created_at=d.created_at, updated_at=d.updated_at,
        name=d.name, code=d.code, parent_id=d.parent_id, manager_id=d.head_employee_id,
    )  # fmt: skip


def salary_out(s: SalaryHistory) -> SalaryOut:
    return SalaryOut(
        id=s.id, employee_id=s.employee_id, effective_date=s.effective_date,
        base_salary=s.base_salary, currency=s.currency, reason=s.reason, created_at=s.created_at,
    )  # fmt: skip


def employee_out(e: Employee, title: str | None, *, level4: bool) -> EmployeeOut:
    """Build the DTO; without `level4` every level-4 field is `{ masked: true }` (02 §6.3)."""
    sensitive: dict[str, Any] = {f: getattr(e, f) if level4 else Masked() for f in LEVEL4_FIELDS}
    return EmployeeOut(
        id=e.id, version=e.version, created_at=e.created_at, updated_at=e.updated_at,
        employee_code=e.employee_code, full_name=e.full_name, email=e.email, phone=e.phone,
        department_id=e.department_id, title=title,
        contract_type=CONTRACT_FROM_DB.get(e.contract_type) if e.contract_type else None,
        status=cast(EmployeeStatus, e.status), hire_date=e.hire_date,
        termination_date=e.termination_date, manager_id=e.manager_id, **sensitive,
    )  # fmt: skip


class HrService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.departments = DepartmentRepository(db)
        self.positions = PositionRepository(db)
        self.employees = EmployeeRepository(db)
        self.salaries = SalaryRepository(db)

    # ---------- shared ----------
    async def _audit(
        self, action: str, table: str, obj: Base, before: Any = None, after: Any = None
    ) -> None:
        await record_audit(
            self.db, action=action, target_schema="hr", target_table=table,
            target_id=getattr(obj, "id", None),
            before=before.model_dump(mode="json") if before is not None else None,
            after=after.model_dump(mode="json") if after is not None else None,
        )  # fmt: skip

    async def _flush_unique(self, what: str) -> None:
        try:
            async with self.db.begin_nested():
                await self.db.flush()
        except IntegrityError as exc:  # concurrent insert won the UQ race
            raise DuplicateResourceError(f"{what} already exists") from exc

    async def _publish(self, event_type: str, table: str, aggregate: uuid.UUID, **p: Any) -> None:
        await publish_in_tx(
            self.db, event_type=event_type, producer="hr", aggregate_schema="hr",
            aggregate_table=table, aggregate_id=aggregate,
            payload={k: str(v) if isinstance(v, uuid.UUID | date) else v for k, v in p.items()},
        )  # fmt: skip

    async def department_exists(self, department_id: uuid.UUID) -> bool:
        """Public: soft-ref integrity check for `department_id` in other modules (05 C7)."""
        return await self.departments.get(department_id) is not None

    # ---------- EP-81 departments ----------
    async def list_departments(
        self, page: PageParams, *, parent_id: uuid.UUID | None
    ) -> tuple[list[DepartmentOut], int]:
        filters = {"parent_id": parent_id} if parent_id else {}
        items, total = await self.departments.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters,
        )  # fmt: skip
        return [department_out(d) for d in items], total

    async def get_department(self, id_: uuid.UUID) -> Department:
        obj = await self.departments.get(id_)
        if obj is None:
            raise NotFoundError("department not found")
        return obj

    async def _check_refs(self, parent_id: uuid.UUID | None, manager_id: uuid.UUID | None) -> None:
        if parent_id is not None and await self.departments.get(parent_id) is None:
            raise BusinessRuleError("parent department not found", details={"field": "parent_id"})
        if manager_id is not None and await self.employees.get(manager_id) is None:
            raise BusinessRuleError("manager employee not found", details={"field": "manager_id"})

    async def _check_tree(self, id_: uuid.UUID, parent_id: uuid.UUID | None) -> None:
        """Walking up from the new parent must never reach `id_` (EP-81: no cycle → 422)."""
        node, depth = parent_id, 0
        while node is not None and depth < MAX_TREE_DEPTH:
            if node == id_:
                raise BusinessRuleError(
                    "department tree would contain a cycle", details={"field": "parent_id"}
                )
            parent = await self.departments.get(node)
            node, depth = (parent.parent_id if parent else None), depth + 1

    async def create_department(self, user: Principal, body: DepartmentCreate) -> DepartmentOut:
        if await self.departments.by_code(body.code) is not None:
            raise DuplicateResourceError("department code exists", details={"code": body.code})
        await self._check_refs(body.parent_id, body.manager_id)
        obj = Department(
            code=body.code, name=body.name, aliases=[], parent_id=body.parent_id,
            head_employee_id=body.manager_id, source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        self.db.add(obj)
        await self._flush_unique("department code")
        await self.db.refresh(obj)
        out = department_out(obj)
        await self._audit("hr.department_create", "departments", obj, after=out)
        return out

    async def update_department(
        self, user: Principal, id_: uuid.UUID, body: DepartmentUpdate, expected: int
    ) -> DepartmentOut:
        obj = await self.get_department(id_)
        before = department_out(obj)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        if "code" in data and data["code"] != obj.code:
            if await self.departments.by_code(data["code"]) is not None:
                raise DuplicateResourceError(
                    "department code exists", details={"code": data["code"]}
                )
        await self._check_refs(data.get("parent_id"), data.get("manager_id"))
        if "parent_id" in data:
            await self._check_tree(id_, data["parent_id"])
        if "manager_id" in data:
            data["head_employee_id"] = data.pop("manager_id")
        data["updated_by"] = user.user_id
        await self.departments.update(obj, expected_version=expected, **data)
        await self.db.refresh(obj)
        out = department_out(obj)
        await self._audit("hr.department_update", "departments", obj, before, out)
        return out

    # ---------- EP-82 employees ----------
    def _employee_scope(self, user: Principal, e: Employee) -> None:
        if user.role in SELF_ROLES:
            if not user.email or (e.email or "").lower() != user.email.lower():
                raise deny("employee profile", employee_id=e.id)
            return
        check_department(user, e.department_id)

    async def _out(self, user: Principal, e: Employee) -> EmployeeOut:
        titles = await self.positions.titles([e.position_id] if e.position_id else [])
        return employee_out(e, titles.get(e.position_id) if e.position_id else None,
                            level4=sees_level4(user))  # fmt: skip

    async def list_employees(
        self, user: Principal, page: PageParams, *, department_id: uuid.UUID | None,
        status: str | None, q: str | None,
    ) -> tuple[list[EmployeeOut], int]:  # fmt: skip
        where: list[ColumnElement[bool]] = []
        if user.role in SELF_ROLES:
            where.append(func.lower(Employee.email) == (user.email or "").lower())
        else:
            department_id = department_scope(user, department_id)
        if department_id is not None:
            where.append(Employee.department_id == department_id)
        if status:
            where.append(Employee.status == status)
        if q:
            like = f"%{normalize_name(q)}%"
            code_like = func.lower(Employee.employee_code).like(f"%{q.lower()}%")
            where.append(or_(Employee.normalized_name.like(like), code_like))
        items, total = await self.employees.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            where=where,
        )  # fmt: skip
        titles = await self.positions.titles([e.position_id for e in items if e.position_id])
        lvl4 = sees_level4(user)
        return [
            employee_out(e, titles.get(e.position_id) if e.position_id else None, level4=lvl4)
            for e in items
        ], total

    async def get_employee_row(self, user: Principal, id_: uuid.UUID) -> Employee:
        obj = await self.employees.get(id_)
        if obj is None:
            raise NotFoundError("employee not found")
        self._employee_scope(user, obj)
        return obj

    async def get_employee(self, user: Principal, id_: uuid.UUID) -> EmployeeOut:
        return await self._out(user, await self.get_employee_row(user, id_))

    async def _position_for(
        self, user: Principal, department_id: uuid.UUID, title: str
    ) -> uuid.UUID:
        """EP-82 `title` → `positions` row of the department (found or created, DEC-195)."""
        found = await self.positions.by_title(department_id, title)
        if found is not None:
            return found.id
        dept = await self.get_department(department_id)
        code = f"{dept.code}-{normalize_name(title).replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
        pos = await self.positions.create(
            department_id=department_id, code=code.upper(), title=title, headcount_budget=0,
            source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        await record_audit(self.db, action="hr.position_create", target_schema="hr",
                           target_table="positions", target_id=pos.id,
                           after={"code": pos.code, "title": title,
                                  "department_id": str(department_id)})  # fmt: skip
        return pos.id

    async def _validate_employee(self, data: dict[str, Any], current: Employee | None) -> None:
        dept = data.get("department_id")
        if dept is not None and await self.departments.get(dept) is None:
            raise BusinessRuleError("department not found", details={"field": "department_id"})
        code = data.get("employee_code")
        if code is not None and await self.employees.code_taken(
            code, current.id if current else None
        ):
            raise DuplicateResourceError("employee_code exists", details={"employee_code": code})
        email = data.get("email")
        if email is not None:
            other = await self.employees.by_email(email)
            if other is not None and (current is None or other.id != current.id):
                raise DuplicateResourceError("email exists", details={"field": "email"})
        status = data.get("status", current.status if current else None)
        hire = data.get("hire_date", current.hire_date if current else None)
        term = data.get("termination_date", current.termination_date if current else None)
        if status == "terminated" and term is None:
            raise BusinessRuleError("terminated needs termination_date",
                                    details={"field": "termination_date"})  # fmt: skip
        if term is not None and hire is not None and term < hire:
            raise BusinessRuleError("termination_date before hire_date",
                                    details={"field": "termination_date"})  # fmt: skip
        manager = data.get("manager_id")
        if manager is not None:
            if await self.employees.get(manager) is None:
                raise BusinessRuleError("manager not found", details={"field": "manager_id"})
            node, depth = manager, 0
            while current is not None and node is not None and depth < MAX_TREE_DEPTH:
                if node == current.id:
                    raise BusinessRuleError("manager chain would contain a cycle",
                                            details={"field": "manager_id"})  # fmt: skip
                node, depth = await self.employees.manager_of(node), depth + 1

    async def _lifecycle_events(self, e: Employee, old_status: str | None) -> None:
        if e.status == old_status:
            return
        if e.status == "active" and old_status in ONBOARD_FROM:
            await self._publish("hr.employee_onboarded", "employees", e.id, employee_id=e.id,
                                department_id=e.department_id, hire_date=e.hire_date)  # fmt: skip
        elif e.status == "terminated":
            await self._publish("hr.employee_terminated", "employees", e.id, employee_id=e.id,
                                department_id=e.department_id,
                                termination_date=e.termination_date)  # fmt: skip

    async def create_employee(self, user: Principal, body: EmployeeCreate) -> EmployeeOut:
        data = body.model_dump()
        await self._validate_employee(data, None)
        title = data.pop("title")
        contract = data.pop("contract_type")
        position_id = await self._position_for(user, body.department_id, title) if title else None
        obj = Employee(
            **data, normalized_name=normalize_name(body.full_name),
            contract_type=CONTRACT_TO_DB[contract] if contract else None,
            position_id=position_id,
            source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        self.db.add(obj)
        await self._flush_unique("employee")
        await self.db.refresh(obj)
        out = await self._out(user, obj)
        await self._audit("hr.employee_create", "employees", obj, after=employee_out(
            obj, out.title, level4=True))  # fmt: skip
        await self._lifecycle_events(obj, None)
        return out

    async def update_employee(
        self, user: Principal, id_: uuid.UUID, body: EmployeeUpdate, expected: int
    ) -> EmployeeOut:
        obj = await self.get_employee_row(user, id_)
        old_status = obj.status
        before = employee_out(obj, (await self._out(user, obj)).title, level4=True)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        await self._validate_employee(data, obj)
        if "title" in data:
            title = data.pop("title")
            dept = data.get("department_id", obj.department_id)
            data["position_id"] = await self._position_for(user, dept, title) if title else None
        if "contract_type" in data:
            c = data.pop("contract_type")
            data["contract_type"] = CONTRACT_TO_DB[c] if c else None
        if "full_name" in data:
            data["normalized_name"] = normalize_name(data["full_name"])
        data["updated_by"] = user.user_id
        await self.employees.update(obj, expected_version=expected, **data)
        await self._flush_unique("employee")
        await self.db.refresh(obj)
        out = await self._out(user, obj)
        await self._audit("hr.employee_update", "employees", obj, before,
                          employee_out(obj, out.title, level4=True))  # fmt: skip
        await self._lifecycle_events(obj, old_status)
        return out

    async def delete_employee(self, user: Principal, id_: uuid.UUID) -> None:
        obj = await self.get_employee_row(user, id_)
        before = employee_out(obj, None, level4=True)
        obj.updated_by = user.user_id
        await self.employees.soft_delete(obj)
        await self._audit("hr.employee_delete", "employees", obj, before=before)

    # ---------- EP-83 salary history (level 4) ----------
    @staticmethod
    def _salary_gate(user: Principal) -> None:
        if not sees_level4(user):
            raise SalaryDeniedError("salary history is level-4 data", details={"role": user.role})

    async def list_salary(
        self, user: Principal, employee_id: uuid.UUID, page: PageParams
    ) -> tuple[list[SalaryOut], int]:
        self._salary_gate(user)
        await self.get_employee_row(user, employee_id)
        sort = "effective_date" if page.sort_by == "effective_date" else "created_at"
        items, total = await self.salaries.list_page(
            limit=page.limit, offset=page.offset, sort_by=sort, order=page.order,
            filters={"employee_id": employee_id},
        )  # fmt: skip
        return [salary_out(s) for s in items], total

    async def add_salary(
        self, user: Principal, employee_id: uuid.UUID, body: SalaryCreate
    ) -> SalaryOut:
        self._salary_gate(user)
        emp = await self.get_employee_row(user, employee_id)
        if body.base_salary <= 0:
            raise BusinessRuleError("base_salary must be > 0", details={"field": "base_salary"})
        if await self.salaries.exists(employee_id, body.effective_date):
            raise DuplicateResourceError(
                "salary for this effective_date exists",
                details={"effective_date": body.effective_date.isoformat()},
            )
        obj = SalaryHistory(
            employee_id=employee_id, base_salary=body.base_salary, currency=body.currency,
            effective_date=body.effective_date, reason=body.reason,
        )  # fmt: skip
        self.db.add(obj)
        await self._flush_unique("salary for this effective_date")
        await self.db.refresh(obj)
        out = salary_out(obj)
        await self._audit("hr.salary_create", "salary_history", obj, after=out)
        # FR-HR-02 / 05 §5.3: ids + date only — never the amount.
        await self._publish("hr.salary_updated", "salary_history", obj.id, employee_id=emp.id,
                            department_id=emp.department_id,
                            effective_date=body.effective_date)  # fmt: skip
        return out

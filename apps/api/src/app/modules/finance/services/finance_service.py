"""Public service interface of `finance` — the only entry point for other modules.

Every mutation writes `ENT-AuditLog` in the caller's transaction (10 §1.8); the route commits.
Scope (02 §7): MANAGER sees / writes only expenses of their own department (FORBIDDEN_SCOPE).
"""

import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.base_model import Base
from app.core.deps import Principal
from app.core.errors import (
    BusinessRuleError,
    DuplicateResourceError,
    NotFoundError,
    ScopeDeniedError,
)
from app.core.pagination import PageParams
from app.modules.finance.models import CashPosition, Expense, Revenue
from app.modules.finance.repositories import (
    CashPositionRepository,
    ExpenseRepository,
    RevenueRepository,
)
from app.modules.finance.schemas import (
    CashPositionCreate,
    CashPositionOut,
    CashPositionUpdate,
    ExpenseCreate,
    ExpenseOut,
    ExpenseUpdate,
    RevenueCreate,
    RevenueOut,
    RevenueUpdate,
)
from app.modules.finance.services.budget_service import BudgetService

DEPARTMENT_SCOPED_ROLES = frozenset({"MANAGER"})


def period_of(d: Any) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _positive(amount: int | None, field: str) -> None:
    if amount is not None and amount <= 0:
        raise BusinessRuleError(
            f"{field} must be > 0", details={"field": field, "rule": "FR-FIN-01"}
        )


def revenue_out(r: Revenue) -> RevenueOut:
    return RevenueOut(
        id=r.id, version=r.version, created_at=r.created_at, updated_at=r.updated_at,
        amount=r.amount, currency=r.currency, category=r.category,
        recognized_on=r.revenue_date, period=r.period_key, client_id=r.client_id,
        product_id=r.product_id, invoice_id=r.invoice_id, source_note=r.source_note,
        description=r.description,
    )  # fmt: skip


def expense_out(e: Expense) -> ExpenseOut:
    return ExpenseOut(
        id=e.id, version=e.version, created_at=e.created_at, updated_at=e.updated_at,
        title=e.title, amount=e.amount, currency=e.currency, category=e.category,
        department_id=e.department_id, budget_id=e.budget_id, spent_on=e.expense_date,
        period=e.period_key, is_recurring=e.is_recurring, recurrence_period=e.recurrence_period,
        vendor=e.counterparty_name, description=e.description,
    )  # fmt: skip


class FinanceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.revenues = RevenueRepository(db)
        self.expenses = ExpenseRepository(db)
        self.cash = CashPositionRepository(db)

    # ---------- shared ----------
    async def _audit(
        self, action: str, table: str, obj: Base, before: Any = None, after: Any = None
    ) -> None:
        await record_audit(
            self.db,
            action=action,
            target_schema="finance",
            target_table=table,
            target_id=getattr(obj, "id", None),
            before=before.model_dump(mode="json") if before is not None else None,
            after=after.model_dump(mode="json") if after is not None else None,
        )

    async def _flush_unique(self, what: str) -> None:
        try:
            await self.db.flush()
        except IntegrityError as exc:  # concurrent insert won the partial UQ race
            raise DuplicateResourceError(f"{what} already exists") from exc

    # ---------- EP-61 revenues ----------
    async def list_revenues(
        self, page: PageParams, *, period: str | None, category: str | None,
        client_id: uuid.UUID | None,
    ) -> tuple[list[RevenueOut], int]:  # fmt: skip
        filters: dict[str, Any] = {}
        if period:
            filters["period_key"] = period
        if category:
            filters["category"] = category
        if client_id:
            filters["client_id"] = client_id
        sort = {"recognized_on": "revenue_date"}.get(page.sort_by, page.sort_by)
        items, total = await self.revenues.list_page(
            limit=page.limit, offset=page.offset, sort_by=sort, order=page.order,
            filters=filters,
        )  # fmt: skip
        return [revenue_out(r) for r in items], total

    async def get_revenue(self, id_: uuid.UUID) -> Revenue:
        obj = await self.revenues.get(id_)
        if obj is None:
            raise NotFoundError("revenue not found")
        return obj

    async def create_revenue(self, user: Principal, body: RevenueCreate) -> RevenueOut:
        _positive(body.amount, "amount")
        obj = await self.revenues.create(
            amount=body.amount, currency=body.currency, category=body.category,
            revenue_date=body.recognized_on, period_key=period_of(body.recognized_on),
            client_id=body.client_id, product_id=body.product_id,
            source_note=body.source_note or "manual", description=body.description,
            origin="manual", source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        await self.db.refresh(obj)
        out = revenue_out(obj)
        await self._audit("finance.revenue_create", "revenues", obj, after=out)
        return out

    async def update_revenue(
        self, user: Principal, id_: uuid.UUID, body: RevenueUpdate, expected: int
    ) -> RevenueOut:
        obj = await self.get_revenue(id_)
        before = revenue_out(obj)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        data["updated_by"] = user.user_id
        _positive(data.get("amount"), "amount")
        if "recognized_on" in data:
            d = data.pop("recognized_on")
            data["revenue_date"], data["period_key"] = d, period_of(d)
        await self.revenues.update(obj, expected_version=expected, **data)
        await self.db.refresh(obj)
        out = revenue_out(obj)
        await self._audit("finance.revenue_update", "revenues", obj, before, out)
        return out

    async def delete_revenue(self, user: Principal, id_: uuid.UUID) -> None:
        obj = await self.get_revenue(id_)
        before = revenue_out(obj)
        obj.updated_by = user.user_id
        await self.revenues.soft_delete(obj)
        await self._audit("finance.revenue_delete", "revenues", obj, before=before)

    # ---------- EP-62 expenses ----------
    @staticmethod
    def _scope_department(user: Principal, department_id: uuid.UUID | None) -> None:
        if user.role in DEPARTMENT_SCOPED_ROLES and department_id != user.department_id:
            raise ScopeDeniedError(
                "expense outside your department", details={"department_id": str(department_id)}
            )

    async def list_expenses(
        self, user: Principal, page: PageParams, *, period: str | None,
        department_id: uuid.UUID | None, category: str | None,
    ) -> tuple[list[ExpenseOut], int]:  # fmt: skip
        filters: dict[str, Any] = {}
        if user.role in DEPARTMENT_SCOPED_ROLES:
            if department_id is not None:
                self._scope_department(user, department_id)
            department_id = user.department_id
            filters["department_id"] = department_id
        elif department_id:
            filters["department_id"] = department_id
        if period:
            filters["period_key"] = period
        if category:
            filters["category"] = category
        sort = {"spent_on": "expense_date"}.get(page.sort_by, page.sort_by)
        items, total = await self.expenses.list_page(
            limit=page.limit, offset=page.offset, sort_by=sort, order=page.order,
            filters=filters,
        )  # fmt: skip
        return [expense_out(e) for e in items], total

    async def get_expense(self, user: Principal, id_: uuid.UUID) -> Expense:
        obj = await self.expenses.get(id_)
        if obj is None:
            raise NotFoundError("expense not found")
        self._scope_department(user, obj.department_id)
        return obj

    async def create_expense(self, user: Principal, body: ExpenseCreate) -> ExpenseOut:
        _positive(body.amount, "amount")
        self._scope_department(user, body.department_id)
        if body.is_recurring and body.recurrence_period is None:
            raise BusinessRuleError(
                "recurring expense needs recurrence_period",
                details={"field": "recurrence_period"},
            )
        obj = await self.expenses.create(
            title=body.title, amount=body.amount, currency=body.currency,
            category=body.category, department_id=body.department_id, budget_id=body.budget_id,
            expense_date=body.spent_on, period_key=period_of(body.spent_on),
            is_recurring=body.is_recurring, recurrence_period=body.recurrence_period,
            counterparty_name=body.vendor, description=body.description,
            origin="manual", source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        await self.db.refresh(obj)
        out = expense_out(obj)
        await self._audit("finance.expense_create", "expenses", obj, after=out)
        await BudgetService(self.db).on_expense_changed(obj.department_id, obj.period_key)
        return out

    async def update_expense(
        self, user: Principal, id_: uuid.UUID, body: ExpenseUpdate, expected: int
    ) -> ExpenseOut:
        obj = await self.get_expense(user, id_)
        before = expense_out(obj)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        data["updated_by"] = user.user_id
        _positive(data.get("amount"), "amount")
        if "department_id" in data:
            self._scope_department(user, data["department_id"])
        if "spent_on" in data:
            d = data.pop("spent_on")
            data["expense_date"], data["period_key"] = d, period_of(d)
        if "vendor" in data:
            data["counterparty_name"] = data.pop("vendor")
        await self.expenses.update(obj, expected_version=expected, **data)
        await self.db.refresh(obj)
        out = expense_out(obj)
        await self._audit("finance.expense_update", "expenses", obj, before, out)
        await BudgetService(self.db).on_expense_changed(obj.department_id, obj.period_key)
        return out

    async def delete_expense(self, user: Principal, id_: uuid.UUID) -> None:
        obj = await self.get_expense(user, id_)
        before = expense_out(obj)
        obj.updated_by = user.user_id
        await self.expenses.soft_delete(obj)
        await self._audit("finance.expense_delete", "expenses", obj, before=before)

    # ---------- EP-65 cash positions ----------
    async def cash_out(self, c: CashPosition) -> CashPositionOut:
        prev = await self.cash.previous(c.period_key)
        return CashPositionOut(
            id=c.id, version=c.version, created_at=c.created_at, updated_at=c.updated_at,
            period=c.period_key, opening_balance=prev.closing_balance if prev else None,
            closing_balance=c.closing_balance, currency=c.currency, cash_source=c.cash_source,
            note=c.note, recorded_by=c.recorded_by,
        )  # fmt: skip

    async def list_cash_positions(
        self, page: PageParams, *, from_: str | None, to: str | None
    ) -> tuple[list[CashPositionOut], int]:
        where = []
        if from_:
            where.append(CashPosition.period_key >= from_)
        if to:
            where.append(CashPosition.period_key <= to)
        sort = {"period": "period_key"}.get(page.sort_by, page.sort_by)
        items, total = await self.cash.list_page(
            limit=page.limit, offset=page.offset, sort_by=sort, order=page.order, where=where
        )
        return [await self.cash_out(c) for c in items], total

    async def get_cash_position(self, id_: uuid.UUID) -> CashPosition:
        obj = await self.cash.get(id_)
        if obj is None:
            raise NotFoundError("cash position not found")
        return obj

    async def create_cash_position(
        self, user: Principal, body: CashPositionCreate
    ) -> CashPositionOut:
        if await self.cash.by_period(body.period) is not None:
            raise DuplicateResourceError(
                "cash position for this period already exists", details={"period": body.period}
            )
        obj = CashPosition(
            period_key=body.period, closing_balance=body.closing_balance,
            currency=body.currency, cash_source=body.cash_source, note=body.note,
            recorded_by=user.user_id, source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        self.db.add(obj)
        await self._flush_unique("cash position for this period")
        await self.db.refresh(obj)
        out = await self.cash_out(obj)
        await self._audit("finance.cash_position_create", "cash_positions", obj, after=out)
        return out

    async def update_cash_position(
        self, user: Principal, id_: uuid.UUID, body: CashPositionUpdate, expected: int
    ) -> CashPositionOut:
        obj = await self.get_cash_position(id_)
        before = await self.cash_out(obj)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        data["updated_by"] = user.user_id
        await self.cash.update(obj, expected_version=expected, **data)
        await self.db.refresh(obj)
        out = await self.cash_out(obj)
        await self._audit("finance.cash_position_update", "cash_positions", obj, before, out)
        return out

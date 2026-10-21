"""EP-63 budgets, EP-64 status, BR-FIN-05 `EVT-finance.budget_exceeded` (T-102).

10 §4.6 lists a single `category` per budget while 05 stores `categories` jsonb and the UQ is
`(department_id, fiscal_year, quarter)` — API `category` maps to a one-item `categories`
(DEC-187). Utilization is per department × period (quarter / year) on the whole allocation;
the event fires at most once per budget (= department × period) — dedupe on the outbox row.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import DuplicateResourceError, NotFoundError
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.finance.models import Budget
from app.modules.finance.repositories import BudgetRepository
from app.modules.finance.rules import (
    budget_period_key,
    budget_status,
    quarter_periods,
    utilization_pct,
)
from app.modules.finance.schemas import (
    BudgetCategory,
    BudgetCreate,
    BudgetOut,
    BudgetStatusOut,
    BudgetUpdate,
)

EVT_BUDGET_EXCEEDED = "finance.budget_exceeded"


def budget_out(b: Budget) -> BudgetOut:
    cats = [BudgetCategory.model_validate(c) for c in (b.categories or [])]
    return BudgetOut(
        id=b.id, version=b.version, created_at=b.created_at, updated_at=b.updated_at,
        department_id=b.department_id, fiscal_year=b.fiscal_year, quarter=b.quarter,
        period=budget_period_key(b.fiscal_year, b.quarter), allocated_amount=b.allocated_amount,
        currency=b.currency, category=cats[0].category if len(cats) == 1 else None,
        categories=cats, notes=b.notes,
    )  # fmt: skip


def quarter_of(period_key: str) -> tuple[int, str]:
    year, month = int(period_key[:4]), int(period_key[5:7])
    return year, f"Q{(month - 1) // 3 + 1}"


class BudgetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = BudgetRepository(db)

    async def _audit(self, action: str, obj: Budget, before: Any = None, after: Any = None) -> None:
        await record_audit(
            self.db, action=action, target_schema="finance", target_table="budgets",
            target_id=obj.id,
            before=before.model_dump(mode="json") if before is not None else None,
            after=after.model_dump(mode="json") if after is not None else None,
        )  # fmt: skip

    async def list_budgets(
        self, page: PageParams, *, fiscal_year: int | None, quarter: str | None,
        department_id: uuid.UUID | None,
    ) -> tuple[list[BudgetOut], int]:  # fmt: skip
        filters: dict[str, Any] = {}
        if fiscal_year is not None:
            filters["fiscal_year"] = fiscal_year
        if quarter is not None:
            filters["quarter"] = quarter
        if department_id is not None:
            filters["department_id"] = department_id
        items, total = await self.repo.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters,
        )  # fmt: skip
        return [budget_out(b) for b in items], total

    async def get(self, id_: uuid.UUID) -> Budget:
        obj = await self.repo.get(id_)
        if obj is None:
            raise NotFoundError("budget not found")
        return obj

    async def create(self, user: Principal, body: BudgetCreate) -> BudgetOut:
        if await self.repo.find(body.department_id, body.fiscal_year, body.quarter):
            raise DuplicateResourceError(
                "budget for this department and period already exists",
                details={"department_id": str(body.department_id),
                         "period": budget_period_key(body.fiscal_year, body.quarter)},
            )  # fmt: skip
        cats = list(body.categories)
        if body.category is not None and not cats:
            cats = [BudgetCategory(category=body.category, allocated_amount=body.allocated_amount)]
        obj = await self.repo.create(
            department_id=body.department_id, fiscal_year=body.fiscal_year,
            quarter=body.quarter, allocated_amount=body.allocated_amount,
            currency=body.currency, categories=[c.model_dump() for c in cats],
            notes=body.notes, source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        await self.db.refresh(obj)
        out = budget_out(obj)
        await self._audit("finance.budget_create", obj, after=out)
        await self.check_exceeded(obj)
        return out

    async def update(
        self, user: Principal, id_: uuid.UUID, body: BudgetUpdate, expected: int
    ) -> BudgetOut:
        obj = await self.get(id_)
        before = budget_out(obj)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        if "categories" in data and data["categories"] is not None:
            data["categories"] = [dict(c) for c in data["categories"]]
        await self.repo.update(obj, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(obj)
        out = budget_out(obj)
        await self._audit("finance.budget_update", obj, before, out)
        await self.check_exceeded(obj)
        return out

    async def delete(self, user: Principal, id_: uuid.UUID) -> None:
        obj = await self.get(id_)
        before = budget_out(obj)
        obj.updated_by = user.user_id
        await self.repo.soft_delete(obj)
        await self._audit("finance.budget_delete", obj, before=before)

    # ---------- BR-FIN-05 ----------
    async def status_of(self, b: Budget) -> BudgetStatusOut:
        spent = await self.repo.spent(b.department_id, quarter_periods(b.fiscal_year, b.quarter))
        pct = utilization_pct(spent, b.allocated_amount)
        return BudgetStatusOut(
            budget_id=b.id, department_id=b.department_id,
            period=budget_period_key(b.fiscal_year, b.quarter),
            allocated_amount=b.allocated_amount, spent_amount=spent,
            budget_utilization_pct=pct, currency=b.currency, status=budget_status(pct),
        )  # fmt: skip

    async def statuses(
        self, *, period: str | None, department_id: uuid.UUID | None
    ) -> list[BudgetStatusOut]:
        filters: dict[str, Any] = {}
        if department_id is not None:
            filters["department_id"] = department_id
        if period is not None:
            year, quarter = _parse_period(period)
            filters["fiscal_year"] = year
            if quarter is not None:
                filters["quarter"] = quarter
        items, _ = await self.repo.list_page(
            limit=100, offset=0, sort_by="created_at", order="asc", filters=filters
        )
        return [await self.status_of(b) for b in items]

    async def check_exceeded(self, b: Budget) -> bool:
        """Publish `budget_exceeded` once per budget when utilization > 100 %."""
        st = await self.status_of(b)
        if st.budget_utilization_pct <= 100:
            return False
        if await self.repo.event_already_published(EVT_BUDGET_EXCEEDED, b.id):
            return False
        await publish_in_tx(
            self.db, event_type=EVT_BUDGET_EXCEEDED, producer="finance",
            aggregate_schema="finance", aggregate_table="budgets", aggregate_id=b.id,
            payload={
                "budget_id": str(b.id), "department_id": str(b.department_id),
                "period": st.period, "allocated_amount": st.allocated_amount,
                "spent_amount": st.spent_amount,
                "budget_utilization_pct": st.budget_utilization_pct, "currency": st.currency,
            },
        )  # fmt: skip
        return True

    async def on_expense_changed(self, department_id: uuid.UUID | None, period_key: str) -> None:
        """Called by the expense write path in the same transaction (EP-62 → BR-FIN-05)."""
        if department_id is None:
            return
        year, quarter = quarter_of(period_key)
        for b in await self.repo.covering(department_id, year, quarter):
            await self.check_exceeded(b)


def _parse_period(period: str) -> tuple[int, str | None]:
    """`YYYY`, `YYYY-Qn` or `YYYY-MM` (→ its quarter)."""
    if len(period) == 4:
        return int(period), None
    if period[5] == "Q":
        return int(period[:4]), period[5:]
    return quarter_of(period)

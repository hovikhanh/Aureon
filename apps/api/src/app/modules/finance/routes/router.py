"""HTTP routes for `finance` — EP-60..69, EP-128 (10 §3.6, §4.6).

Pattern for every domain module: one permission per route, `Idem` on create POSTs,
`IfMatch` + body `version` on PATCH, `Page` on lists, commit at the end of the request.
"""

import re
import uuid
from typing import Annotated, Any

from fastapi import Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_permission
from app.core.envelope import Page
from app.core.errors import BadRequestError
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.finance.schemas import (
    BudgetCreate,
    BudgetOut,
    BudgetStatusOut,
    BudgetUpdate,
    CashPositionCreate,
    CashPositionOut,
    CashPositionUpdate,
    ExpenseCategory,
    ExpenseCreate,
    ExpenseOut,
    ExpenseUpdate,
    Quarter,
    RevenueCategory,
    RevenueCreate,
    RevenueOut,
    RevenueUpdate,
    check_period,
)
from app.modules.finance.services.budget_service import BudgetService, budget_out
from app.modules.finance.services.finance_service import FinanceService, expense_out, revenue_out

router = EnvelopeRouter(tags=["finance"])

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_permission("finance:read"))]
Writer = Annotated[Principal, Depends(require_permission("finance:write"))]


def period_query(name: str = "period") -> Any:
    async def _dep(value: Annotated[str | None, Query(alias=name)] = None) -> str | None:
        try:
            return check_period(value)
        except ValueError as exc:
            raise BadRequestError(str(exc), details={"param": name}) from exc

    return Depends(_dep)


Period = Annotated[str | None, period_query()]


# ---------- EP-61 revenues ----------
@router.get("/finance/revenues", response_model=list[RevenueOut])
async def list_revenues(
    db: Db, _: Reader,
    page: Annotated[PageParams, Depends(page_params("recognized_on", "amount"))],
    period: Period = None, category: RevenueCategory | None = None,
    client_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    items, total = await FinanceService(db).list_revenues(
        page, period=period, category=category, client_id=client_id
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/finance/revenues", response_model=RevenueOut, status_code=201)
async def create_revenue(body: RevenueCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return RevenueOut.model_validate(hit)
    out = await FinanceService(db).create_revenue(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/finance/revenues/{revenue_id}", response_model=RevenueOut)
async def get_revenue(revenue_id: uuid.UUID, db: Db, _: Reader) -> Any:
    return revenue_out(await FinanceService(db).get_revenue(revenue_id))


@router.patch("/finance/revenues/{revenue_id}", response_model=RevenueOut)
async def update_revenue(
    revenue_id: uuid.UUID, body: RevenueUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await FinanceService(db).update_revenue(user, revenue_id, body, exp)
    await db.commit()
    return out


@router.delete("/finance/revenues/{revenue_id}", status_code=204, response_class=Response)
async def delete_revenue(revenue_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await FinanceService(db).delete_revenue(user, revenue_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-62 expenses ----------
@router.get("/finance/expenses", response_model=list[ExpenseOut])
async def list_expenses(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("spent_on", "amount"))],
    period: Period = None, department_id: uuid.UUID | None = None,
    category: ExpenseCategory | None = None,
) -> Any:  # fmt: skip
    items, total = await FinanceService(db).list_expenses(
        user, page, period=period, department_id=department_id, category=category
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/finance/expenses", response_model=ExpenseOut, status_code=201)
async def create_expense(body: ExpenseCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ExpenseOut.model_validate(hit)
    out = await FinanceService(db).create_expense(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/finance/expenses/{expense_id}", response_model=ExpenseOut)
async def get_expense(expense_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return expense_out(await FinanceService(db).get_expense(user, expense_id))


@router.patch("/finance/expenses/{expense_id}", response_model=ExpenseOut)
async def update_expense(
    expense_id: uuid.UUID, body: ExpenseUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await FinanceService(db).update_expense(user, expense_id, body, exp)
    await db.commit()
    return out


@router.delete("/finance/expenses/{expense_id}", status_code=204, response_class=Response)
async def delete_expense(expense_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await FinanceService(db).delete_expense(user, expense_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-65 cash positions (L C R U — no delete) ----------
@router.get("/finance/cash-positions", response_model=list[CashPositionOut])
async def list_cash_positions(
    db: Db, _: Reader,
    page: Annotated[PageParams, Depends(page_params("period", "closing_balance"))],
    from_: Annotated[str | None, period_query("from")] = None,
    to: Annotated[str | None, period_query("to")] = None,
) -> Any:  # fmt: skip
    items, total = await FinanceService(db).list_cash_positions(page, from_=from_, to=to)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/finance/cash-positions", response_model=CashPositionOut, status_code=201)
async def create_cash_position(body: CashPositionCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return CashPositionOut.model_validate(hit)
    out = await FinanceService(db).create_cash_position(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/finance/cash-positions/{position_id}", response_model=CashPositionOut)
async def get_cash_position(position_id: uuid.UUID, db: Db, _: Reader) -> Any:
    svc = FinanceService(db)
    return await svc.cash_out(await svc.get_cash_position(position_id))


@router.patch("/finance/cash-positions/{position_id}", response_model=CashPositionOut)
async def update_cash_position(
    position_id: uuid.UUID, body: CashPositionUpdate, db: Db, user: Writer,
    if_match: IfMatch = None,
) -> Any:  # fmt: skip
    exp = expected_version(if_match, body.version)
    out = await FinanceService(db).update_cash_position(user, position_id, body, exp)
    await db.commit()
    return out


# ---------- EP-63 budgets / EP-64 status ----------
_BUDGET_PERIOD = re.compile(r"^\d{4}(-Q[1-4]|-(0[1-9]|1[0-2]))?$")


async def _budget_period(period: str | None = None) -> str | None:
    if period is not None and not _BUDGET_PERIOD.match(period):
        raise BadRequestError(
            "period must be YYYY, YYYY-Qn or YYYY-MM", details={"param": "period"}
        )
    return period


@router.get("/finance/budgets/status", response_model=list[BudgetStatusOut])
async def budget_status(
    db: Db, _: Annotated[Principal, Depends(require_permission("finance:query"))],
    period: Annotated[str | None, Depends(_budget_period)] = None,
    department_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    return await BudgetService(db).statuses(period=period, department_id=department_id)


@router.get("/finance/budgets", response_model=list[BudgetOut])
async def list_budgets(
    db: Db, _: Reader,
    page: Annotated[PageParams, Depends(page_params("fiscal_year", "allocated_amount"))],
    fiscal_year: int | None = None, quarter: Quarter | None = None,
    department_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    items, total = await BudgetService(db).list_budgets(
        page, fiscal_year=fiscal_year, quarter=quarter, department_id=department_id
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/finance/budgets", response_model=BudgetOut, status_code=201)
async def create_budget(body: BudgetCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return BudgetOut.model_validate(hit)
    out = await BudgetService(db).create(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/finance/budgets/{budget_id}", response_model=BudgetOut)
async def get_budget(budget_id: uuid.UUID, db: Db, _: Reader) -> Any:
    return budget_out(await BudgetService(db).get(budget_id))


@router.patch("/finance/budgets/{budget_id}", response_model=BudgetOut)
async def update_budget(
    budget_id: uuid.UUID, body: BudgetUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await BudgetService(db).update(user, budget_id, body, exp)
    await db.commit()
    return out


@router.delete("/finance/budgets/{budget_id}", status_code=204, response_class=Response)
async def delete_budget(budget_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await BudgetService(db).delete(user, budget_id)
    await db.commit()
    return Response(status_code=204)

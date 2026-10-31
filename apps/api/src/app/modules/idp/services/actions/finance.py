"""ACT-create_invoice → `finance` `InvoiceService.create` (moved from
`commit_service._commit_invoice`, 10 §7.2.4; doc #7 INVOICE — P1, code kept).

Params are the extracted INVOICE fields (04 §5.5) as reviewed; VN number/date formats are
normalised here. `number_taken` → `DUPLICATE_RESOURCE` from finance (→ `ACTION_REJECTED`).
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today
from app.core.deps import Principal
from app.modules.finance.schemas import (
    CashPositionCreate,
    ExpenseCreate,
    InvoiceCreate,
    InvoiceLineIn,
    RevenueCreate,
)
from app.modules.finance.services.finance_service import FinanceService
from app.modules.finance.services.invoice_service import InvoiceService
from app.modules.idp.services.actions.registry import (
    ActionContext,
    ActionDef,
    ActionOutcome,
    RowError,
    ref,
    register,
)

_DEFAULT_PAYMENT_TERM_DAYS = 30


def as_str(value: Any) -> str | None:
    return None if value is None else (str(value).strip() or None)


def as_int(value: Any) -> int:
    if value is None or isinstance(value, bool):
        return 0
    if isinstance(value, int | float):
        return int(value)
    s = str(value).strip().replace(" ", "").replace(".", "").replace(",", "")  # VN grouping
    try:
        return int(s)
    except ValueError:
        return 0


def as_vat(value: Any) -> int:
    pct = as_int(value)
    return pct if pct in (0, 5, 8, 10) else 10


def as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None


class InvoiceParams(BaseModel):
    model_config = ConfigDict(extra="ignore")

    invoice_number: Any = None
    issue_date: Any = None
    seller_name: Any = None
    seller_tax_code: Any = None
    subtotal: Any = None
    vat_rate_pct: Any = None
    vat_amount: Any = None
    total_amount: Any = None


async def _validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    if as_int(p.subtotal) <= 0:
        return [{"field": "subtotal", "code": "subtotal<=0",
                 "message": "invoice subtotal must be positive to commit"}]  # fmt: skip
    return []


async def _run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    doc = ctx.source_document_id or uuid.uuid4()
    number = as_str(p.invoice_number) or f"IDP-{doc.hex[:8]}"
    issued = as_date(p.issue_date) or business_today()
    body = InvoiceCreate(
        direction="IN",  # a received supplier invoice (IDP ingest, 04 UC-08)
        counterparty_name=as_str(p.seller_name), counterparty_tax_code=as_str(p.seller_tax_code),
        number=number, issued_on=issued,
        due_date=issued + timedelta(days=_DEFAULT_PAYMENT_TERM_DAYS), status="sent",
        lines=[InvoiceLineIn(description=f"IDP invoice {number}", quantity=1,
                             unit_price=as_int(p.subtotal), vat_pct=as_vat(p.vat_rate_pct))],
        notes=f"Committed from IDP document {doc}",
    )  # fmt: skip
    out = await InvoiceService(db).create(user, body)
    return ActionOutcome([ref("finance", "invoices", out.id)], target_version=out.version)


async def _undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    await InvoiceService(db).delete(user, uuid.UUID(outcome.result_refs[0]["id"]))


register(ActionDef(
    name="ACT-create_invoice", module="finance", required_permission=("finance:write",),
    reversible=True, is_finance=True, params_model=InvoiceParams, validate=_validate, run=_run,
    undo=_undo,
))  # fmt: skip


# ── Doc type #6 "BC tài chính/sao kê số dư" → Revenue/Expense/CashBalance (M2.2, R-DEC-92) ──

_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_MONTH_RE = re.compile(r"^(0[1-9]|1[0-2])/(\d{4})$")
_REV_CATS = {"product_sales", "service", "consulting", "other"}
_EXP_CATS = {"cogs", "salary", "infrastructure", "marketing", "office", "travel", "other"}


def as_month(value: Any) -> str | None:
    """Normalise a period to `YYYY-MM` (accepts `YYYY-MM`, `MM/YYYY`, or a date)."""
    d = as_date(value)
    if d is not None:
        return f"{d.year:04d}-{d.month:02d}"
    s = as_str(value)
    if s and _PERIOD_RE.match(s):
        return s
    if s and (m := _MONTH_RE.match(s)):
        return f"{m.group(2)}-{m.group(1)}"
    return None


class RevenueParams(BaseModel):
    model_config = ConfigDict(extra="ignore")

    period: Any = None
    recognized_on: Any = None
    amount: Any = None
    currency: Any = None
    category: Any = None
    source_note: Any = None


def _rev_cat(value: Any) -> str:
    c = (as_str(value) or "").lower()
    return c if c in _REV_CATS else "other"


async def _rev_validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    if as_int(p.amount) <= 0:
        return [{"field": "amount", "code": "amount<=0", "message": "revenue amount must be > 0"}]
    if as_date(p.recognized_on) is None and as_month(p.period) is None:
        return [{"field": "period", "code": "no_date", "message": "need recognized_on or period"}]
    return []


async def _rev_run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    recognized = as_date(p.recognized_on)
    if recognized is None:
        month = as_month(p.period) or business_today().strftime("%Y-%m")
        recognized = as_date(f"{month}-01")
    body = RevenueCreate(
        amount=as_int(p.amount), currency=as_str(p.currency) or "VND",
        category=_rev_cat(p.category), recognized_on=recognized,
        source_note=as_str(p.source_note) or f"IDP doc {ctx.source_document_id}",
    )  # fmt: skip
    out = await FinanceService(db).create_revenue(user, body)
    return ActionOutcome([ref("finance", "revenues", out.id)], target_version=out.version)


async def _rev_undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    await FinanceService(db).delete_revenue(user, uuid.UUID(outcome.result_refs[0]["id"]))


register(ActionDef(
    name="ACT-record_revenue", module="finance", required_permission=("finance:write",),
    reversible=True, is_finance=True, params_model=RevenueParams, validate=_rev_validate,
    run=_rev_run, undo=_rev_undo,
))  # fmt: skip


class ExpenseParams(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: Any = None
    period: Any = None
    spent_on: Any = None
    amount: Any = None
    currency: Any = None
    category: Any = None
    vendor: Any = None


def _exp_cat(value: Any) -> str:
    c = (as_str(value) or "").lower()
    return c if c in _EXP_CATS else "other"


async def _exp_validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    if as_int(p.amount) <= 0:
        return [{"field": "amount", "code": "amount<=0", "message": "expense amount must be > 0"}]
    if as_date(p.spent_on) is None and as_month(p.period) is None:
        return [{"field": "period", "code": "no_date", "message": "need spent_on or period"}]
    return []


async def _exp_run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    spent = as_date(p.spent_on)
    if spent is None:
        month = as_month(p.period) or business_today().strftime("%Y-%m")
        spent = as_date(f"{month}-01")
    body = ExpenseCreate(
        title=as_str(p.title) or f"IDP expense {ctx.source_document_id}",
        amount=as_int(p.amount), currency=as_str(p.currency) or "VND",
        category=_exp_cat(p.category), spent_on=spent,
        vendor=as_str(p.vendor),
    )  # fmt: skip
    out = await FinanceService(db).create_expense(user, body)
    return ActionOutcome([ref("finance", "expenses", out.id)], target_version=out.version)


async def _exp_undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    await FinanceService(db).delete_expense(user, uuid.UUID(outcome.result_refs[0]["id"]))


register(ActionDef(
    name="ACT-record_expense", module="finance", required_permission=("finance:write",),
    reversible=True, is_finance=True, params_model=ExpenseParams, validate=_exp_validate,
    run=_exp_run, undo=_exp_undo,
))  # fmt: skip


class CashBalanceParams(BaseModel):
    model_config = ConfigDict(extra="ignore")

    period: Any = None
    as_of_date: Any = None
    balance: Any = None
    closing_balance: Any = None
    currency: Any = None


async def _cash_validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    bal = as_int(p.balance if p.balance is not None else p.closing_balance)
    if bal < 0:
        return [{"field": "balance", "code": "balance<0", "message": "cash balance must be >= 0"}]
    if as_month(p.period) is None and as_date(p.as_of_date) is None:
        return [{"field": "period", "code": "no_date", "message": "need period or as_of_date"}]
    return []


async def _cash_run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    month = as_month(p.period) or as_month(p.as_of_date) or business_today().strftime("%Y-%m")
    bal = as_int(p.balance if p.balance is not None else p.closing_balance)
    body = CashPositionCreate(
        period=month, closing_balance=bal, currency=as_str(p.currency) or "VND",
        cash_source="bank_statement", note=f"IDP doc {ctx.source_document_id}",
    )  # fmt: skip
    out = await FinanceService(db).create_cash_position(user, body)
    return ActionOutcome([ref("finance", "cash_positions", out.id)], target_version=out.version)


async def _cash_undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    await FinanceService(db).delete_cash_position(user, uuid.UUID(outcome.result_refs[0]["id"]))


register(ActionDef(
    name="ACT-record_cash_balance", module="finance", required_permission=("finance:write",),
    reversible=True, is_finance=True, params_model=CashBalanceParams, validate=_cash_validate,
    run=_cash_run, undo=_cash_undo,
))  # fmt: skip

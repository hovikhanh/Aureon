"""ACT-create_invoice → `finance` `InvoiceService.create` (moved from
`commit_service._commit_invoice`, 10 §7.2.4; doc #7 INVOICE — P1, code kept).

Params are the extracted INVOICE fields (04 §5.5) as reviewed; VN number/date formats are
normalised here. `number_taken` → `DUPLICATE_RESOURCE` from finance (→ `ACTION_REJECTED`).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today
from app.core.deps import Principal
from app.modules.finance.schemas import InvoiceCreate, InvoiceLineIn
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

"""EP-67 invoices (+ lines), EP-68 pay (FR-FIN-06, T-104).

DEC-189: 10 says `void` / `partially_paid`; the 05 enum is `cancelled` / `partial` — the DB enum
wins. VAT is one rate per invoice in 05 (`vat_rate_pct`), so all lines must share `vat_pct`.
Line `amount = round(quantity × unit_price)`; `vat_amount = round(subtotal × vat / 100)`.
Events (same transaction): create → `invoice_created`; fully paid → `invoice_paid`.
"""

import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.clock import business_today
from app.core.deps import Principal
from app.core.errors import (
    BusinessRuleError,
    ConflictStateError,
    DuplicateResourceError,
    NotFoundError,
)
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.finance.models import Invoice, InvoiceLine
from app.modules.finance.repositories import OPEN_STATUSES, InvoiceRepository
from app.modules.finance.schemas import (
    InvoiceCreate,
    InvoiceLineIn,
    InvoiceLineOut,
    InvoiceOut,
    InvoicePay,
    InvoiceUpdate,
)

EVT_CREATED = "finance.invoice_created"
EVT_PAID = "finance.invoice_paid"


def today() -> date:
    """Business today (08 §1 `DEMO_REFERENCE_DATE` in demo mode)."""
    return business_today()


def _round(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def price_lines(lines: list[InvoiceLineIn]) -> tuple[list[int], int, int, int]:
    """(line amounts, subtotal, vat_pct, vat_amount)."""
    rates = {ln.vat_pct for ln in lines}
    if len(rates) != 1:
        raise BusinessRuleError(
            "all lines must share one vat_pct (one VAT rate per invoice)",
            details={"field": "lines.vat_pct", "values": sorted(rates)},
        )
    vat = rates.pop()
    amounts = [_round(Decimal(str(ln.quantity)) * ln.unit_price) for ln in lines]
    subtotal = sum(amounts)
    return amounts, subtotal, vat, _round(Decimal(subtotal) * vat / 100)


def days_overdue(inv: Invoice, as_of: date) -> int:
    if inv.status not in OPEN_STATUSES or inv.due_date is None:
        return 0
    if inv.total_amount - inv.paid_amount <= 0:
        return 0
    return max(0, (as_of - inv.due_date).days)


class InvoiceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = InvoiceRepository(db)

    async def out(self, inv: Invoice) -> InvoiceOut:
        lines = await self.repo.lines(inv.id)
        late = days_overdue(inv, today())
        return InvoiceOut(
            id=inv.id, version=inv.version, created_at=inv.created_at,
            updated_at=inv.updated_at, direction=inv.direction, client_id=inv.client_id,
            client_name=inv.client_name_snapshot, counterparty_name=inv.counterparty_name,
            series=inv.series, number=inv.number, issued_on=inv.issue_date,
            due_date=inv.due_date, subtotal=inv.subtotal, vat_pct=float(inv.vat_rate_pct),
            vat_amount=inv.vat_amount, total_amount=inv.total_amount,
            paid_amount=inv.paid_amount, amount_due=inv.total_amount - inv.paid_amount,
            currency=inv.currency, status=inv.status, overdue=late > 0, days_overdue=late,
            paid_at=inv.paid_at, notes=inv.notes,
            lines=[
                InvoiceLineOut(
                    line_no=ln.line_no, description=ln.description,
                    quantity=float(ln.quantity), unit_price=ln.unit_price, amount=ln.amount,
                    vat_pct=float(inv.vat_rate_pct), product_id=ln.product_id,
                )
                for ln in lines
            ],
        )  # fmt: skip

    async def _audit(self, action: str, inv: Invoice, before: Any, after: Any) -> None:
        await record_audit(
            self.db, action=action, target_schema="finance", target_table="invoices",
            target_id=inv.id, before=before.model_dump(mode="json") if before else None,
            after=after.model_dump(mode="json") if after else None,
        )  # fmt: skip

    def _add_lines(self, inv: Invoice, lines: list[InvoiceLineIn], amounts: list[int]) -> None:
        self.db.add_all(
            InvoiceLine(
                invoice_id=inv.id, line_no=i, description=ln.description,
                quantity=Decimal(str(ln.quantity)), unit_price=ln.unit_price, amount=amt,
                currency=inv.currency, product_id=ln.product_id, source="MANUAL",
            )
            for i, (ln, amt) in enumerate(zip(lines, amounts, strict=True), start=1)
        )  # fmt: skip

    async def list_invoices(
        self, page: PageParams, *, status: str | None, client_id: uuid.UUID | None,
        overdue: bool | None, period: str | None, direction: str | None,
    ) -> tuple[list[InvoiceOut], int]:  # fmt: skip
        filters: dict[str, Any] = {}
        where = []
        if status:
            filters["status"] = status
        if client_id:
            filters["client_id"] = client_id
        if direction:
            filters["direction"] = direction
        if period:
            y, m = int(period[:4]), int(period[5:7])
            start = date(y, m, 1)
            end = date(y + (m == 12), m % 12 + 1, 1)
            where += [Invoice.issue_date >= start, Invoice.issue_date < end]
        if overdue is not None:
            late = (
                Invoice.status.in_(OPEN_STATUSES)
                & (Invoice.due_date < today())
                & (Invoice.total_amount > Invoice.paid_amount)
            )
            where.append(late if overdue else ~late)
        sort = {"issued_on": "issue_date"}.get(page.sort_by, page.sort_by)
        items, total = await self.repo.list_page(
            limit=page.limit, offset=page.offset, sort_by=sort, order=page.order,
            filters=filters, where=where,
        )  # fmt: skip
        return [await self.out(i) for i in items], total

    async def get(self, id_: uuid.UUID) -> Invoice:
        inv = await self.repo.get(id_)
        if inv is None:
            raise NotFoundError("invoice not found")
        return inv

    async def create(self, user: Principal, body: InvoiceCreate) -> InvoiceOut:
        if body.due_date <= body.issued_on:
            raise BusinessRuleError(
                "due_date must be after issued_on", details={"field": "due_date"}
            )
        if body.direction == "OUT" and body.client_id is None:
            raise BusinessRuleError(
                "client_id is required for OUT invoices", details={"field": "client_id"}
            )
        if await self.repo.number_taken(
            body.direction, body.counterparty_tax_code, body.series, body.number
        ):
            raise DuplicateResourceError(
                "invoice number already exists", details={"number": body.number}
            )
        amounts, subtotal, vat, vat_amount = price_lines(body.lines)
        inv = Invoice(
            direction=body.direction, series=body.series, number=body.number,
            issue_date=body.issued_on, due_date=body.due_date, client_id=body.client_id,
            client_name_snapshot=body.client_name, counterparty_name=body.counterparty_name,
            counterparty_tax_code=body.counterparty_tax_code, subtotal=subtotal,
            vat_rate_pct=vat, vat_amount=vat_amount, total_amount=subtotal + vat_amount,
            paid_amount=0, currency=body.currency, status=body.status, notes=body.notes,
            source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        self.db.add(inv)
        try:
            await self.db.flush()
        except IntegrityError as exc:  # concurrent insert won the business UQ
            raise DuplicateResourceError("invoice number already exists") from exc
        self._add_lines(inv, body.lines, amounts)
        await self.db.flush()
        await self.db.refresh(inv)
        out = await self.out(inv)
        await self._audit("finance.invoice_create", inv, None, out)
        await publish_in_tx(
            self.db, event_type=EVT_CREATED, producer="finance", aggregate_schema="finance",
            aggregate_table="invoices", aggregate_id=inv.id,
            payload={
                "invoice_id": str(inv.id), "direction": inv.direction,
                "client_id": str(inv.client_id) if inv.client_id else None,
                "total_amount": inv.total_amount, "currency": inv.currency,
                "issued_on": inv.issue_date.isoformat(), "due_date": body.due_date.isoformat(),
            },
        )  # fmt: skip
        return out

    async def update(
        self, user: Principal, id_: uuid.UUID, body: InvoiceUpdate, expected: int
    ) -> InvoiceOut:
        inv = await self.get(id_)
        before = await self.out(inv)
        data = body.model_dump(exclude_unset=True, exclude={"version", "lines"})
        if inv.status in ("paid", "cancelled"):
            raise ConflictStateError(f"invoice is {inv.status}", details={"status": inv.status})
        if data.get("status") == "cancelled" and inv.paid_amount > 0:
            raise ConflictStateError("invoice has payments", details={"paid": inv.paid_amount})
        if data.get("status") == "draft" and inv.status != "draft":
            raise ConflictStateError("cannot return to draft", details={"status": inv.status})
        due = data.get("due_date", inv.due_date)
        if due is not None and due <= inv.issue_date:
            raise BusinessRuleError(
                "due_date must be after issued_on", details={"field": "due_date"}
            )
        if body.lines is not None:
            if inv.status != "draft":
                raise ConflictStateError("lines can change only in draft")
            amounts, subtotal, vat, vat_amount = price_lines(body.lines)
            data.update(
                subtotal=subtotal, vat_rate_pct=vat, vat_amount=vat_amount,
                total_amount=subtotal + vat_amount,
            )  # fmt: skip
            for old in await self.repo.lines(inv.id):
                await self.db.delete(old)
            await self.db.flush()
            self._add_lines(inv, body.lines, amounts)
        await self.repo.update(inv, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(inv)
        out = await self.out(inv)
        await self._audit("finance.invoice_update", inv, before, out)
        return out

    async def delete(self, user: Principal, id_: uuid.UUID) -> None:
        inv = await self.get(id_)
        if inv.paid_amount > 0:
            raise ConflictStateError("invoice has payments", details={"paid": inv.paid_amount})
        before = await self.out(inv)
        inv.updated_by = user.user_id
        await self.repo.soft_delete(inv)
        await self._audit("finance.invoice_delete", inv, before, None)

    async def pay(self, user: Principal, id_: uuid.UUID, body: InvoicePay) -> InvoiceOut:
        inv = await self.get(id_)
        if inv.status in ("paid", "cancelled", "draft"):
            raise ConflictStateError(
                f"cannot pay a {inv.status} invoice", details={"status": inv.status}
            )
        due = inv.total_amount - inv.paid_amount
        if body.amount_paid > due:
            raise BusinessRuleError(
                "amount_paid exceeds amount_due",
                details={"amount_due": due, "amount_paid": body.amount_paid},
            )
        before = await self.out(inv)
        paid = inv.paid_amount + body.amount_paid
        full = paid == inv.total_amount
        await self.repo.update(
            inv, paid_amount=paid, status="paid" if full else "partial",
            paid_at=body.paid_at if full else inv.paid_at, updated_by=user.user_id,
        )  # fmt: skip
        await self.db.refresh(inv)
        out = await self.out(inv)
        await record_audit(
            self.db, action="finance.invoice_pay", target_schema="finance",
            target_table="invoices", target_id=inv.id,
            before=before.model_dump(mode="json"), after=out.model_dump(mode="json"),
            metadata={"amount_paid": body.amount_paid, "method": body.method},
        )  # fmt: skip
        if full:
            await publish_in_tx(
                self.db, event_type=EVT_PAID, producer="finance", aggregate_schema="finance",
                aggregate_table="invoices", aggregate_id=inv.id,
                payload={
                    "invoice_id": str(inv.id), "direction": inv.direction,
                    "client_id": str(inv.client_id) if inv.client_id else None,
                    "total_amount": inv.total_amount, "currency": inv.currency,
                    "paid_at": body.paid_at.isoformat(),
                    "days_to_pay": (body.paid_at.date() - inv.issue_date).days,
                },
            )  # fmt: skip
        return out

    async def mark_overdue(self, as_of: date | None = None) -> int:
        """Daily job (METRIC-FIN-05): open invoices past due → `overdue`. Idempotent."""
        ids = await self.repo.mark_overdue(as_of or today())
        for inv_id in ids:
            await record_audit(
                self.db, action="finance.invoice_overdue", target_schema="finance",
                target_table="invoices", target_id=inv_id, after={"status": "overdue"},
            )  # fmt: skip
        return len(ids)

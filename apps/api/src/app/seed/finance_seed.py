"""Finance seed — company ABC (08 §3 DOC-01/02, §5, §7 E9, §10.4). Idempotent per group.

Each group is skipped when a row with `source='SEED'` already exists. Events (budget_exceeded,
burn_over_forecast, cash_flow_forecast_updated) go through the normal services / outbox.
"""

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.outbox import publish_in_tx
from app.modules.finance.models import (
    Budget,
    CashFlowForecast,
    CashFlowForecastLine,
    CashPosition,
    Expense,
    Forecast,
    ForecastLine,
    Invoice,
    InvoiceLine,
    Revenue,
)
from app.modules.finance.services.analytics_service import FinanceAnalyticsService
from app.modules.finance.services.budget_service import BudgetService
from app.modules.finance.services.cash_flow_service import band
from app.modules.finance.services.forecast_service import confidence_band
from app.modules.finance.services.invoice_service import InvoiceService
from app.seed import finance_data as D
from app.seed.ids import seed_uuid

REFERENCE = date(2026, 10, 20)
SEED: dict[str, Any] = {"source": "SEED"}
Report = dict[str, int]


def _at(d: date) -> datetime:
    return datetime.combine(d, time(3, 0), tzinfo=UTC)


async def _has(db: AsyncSession, model: Any) -> bool:
    stmt = select(func.count()).select_from(model).where(model.source == "SEED")
    return int((await db.execute(stmt)).scalar_one()) > 0


def _split(total: int, weights: list[int]) -> list[int]:
    """Integer split proportional to weights; remainder on the last part (sum is exact)."""
    parts = [total * w // sum(weights) for w in weights[:-1]]
    return [*parts, total - sum(parts)]


async def seed_revenues(db: AsyncSession) -> int:
    if await _has(db, Revenue):
        return 0
    rows = []
    for period, mil in D.MONTHLY_REVENUE_MIL.items():
        day = date(int(period[:4]), int(period[5:]), 10 if period == "2026-10" else 15)
        amounts = _split(mil * D.TR, [w for _, _, w in D.PRODUCT_SPLIT])
        for (name, cat, _), amount in zip(D.PRODUCT_SPLIT, amounts, strict=True):
            rows.append(Revenue(
                source_note="Dữ liệu seed lịch sử", category=cat, amount=amount,
                currency="VND", revenue_date=day, period_key=period, origin="imported",
                description=name, **SEED,
            ))  # fmt: skip
    db.add_all(rows)
    return len(rows)


def _expense(title: str, cat: str, amount: int, day: date, dept: uuid.UUID | None) -> Expense:
    return Expense(
        title=title, category=cat, department_id=dept, amount=amount, currency="VND",
        expense_date=day, period_key=f"{day.year:04d}-{day.month:02d}",
        is_recurring=cat == "salary", recurrence_period="monthly" if cat == "salary" else None,
        origin="imported", **SEED,
    )  # fmt: skip


async def seed_expenses(db: AsyncSession) -> int:
    """COGS (no department) + opex by department (Q3 actuals of DOC-01 each month, payroll
    share 8.775/10.200); October = MTD 01–20/10."""
    if await _has(db, Expense):
        return 0
    rows: list[Expense] = []
    q3_actual = sum(a for _, a in D.Q3_BUDGET_ACTUAL_MIL.values())
    for period, rev in D.MONTHLY_REVENUE_MIL.items():
        if period == "2026-10":
            continue
        day = date(int(period[:4]), int(period[5:]), 25)
        cogs = D.COGS_MIL.get(period, rev * D.COGS_RATIO_PCT // 100) * D.TR
        rows.append(_expense("Giá vốn hàng bán", "cogs", cogs, day, None))
        q = int(period[5:]) - 1
        q_start = period[:5] + f"{q - q % 3 + 1:02d}"
        for code, (_, actual) in D.Q3_BUDGET_ACTUAL_MIL.items():
            month = actual * D.TR // 3 + (actual * D.TR % 3 if period == q_start else 0)
            salary, office = _split(month, [D.Q3_PAYROLL_MIL, q3_actual - D.Q3_PAYROLL_MIL])
            dept: uuid.UUID | None = seed_uuid("department", code)
            rows.append(_expense(f"Lương phân bổ {code}", "salary", salary, day, dept))
            rows.append(_expense(f"Chi phí vận hành {code}", "office", office, day, dept))
    for cat, mil in D.OCT_MTD_EXPENSE_MIL.items():
        dept = None if cat == "cogs" else seed_uuid("department", "BOD")
        rows.append(_expense(f"Chi T10 ({cat})", cat, mil * D.TR, date(2026, 10, 15), dept))
    db.add_all(rows)
    return len(rows)


async def seed_cash_positions(db: AsyncSession, recorded_by: uuid.UUID) -> int:
    if await _has(db, CashPosition):
        return 0
    rows = [
        CashPosition(period_key=p, closing_balance=mil * D.TR, currency="VND",
                     cash_source="bank_statement", recorded_by=recorded_by,
                     note="Số dư 18/10/2026" if p == "2026-10" else None, **SEED)
        for p, mil in D.CASH_MIL.items()
    ]  # fmt: skip
    db.add_all(rows)
    return len(rows)


async def seed_budgets(db: AsyncSession) -> int:
    """Q3/2026 budgets for 7 departments (DOC-01 trang 9); SAL 109 % → budget_exceeded."""
    if await _has(db, Budget):
        return 0
    budgets = [
        Budget(department_id=seed_uuid("department", code), fiscal_year=2026, quarter="Q3",
               allocated_amount=alloc * D.TR, currency="VND", categories=[],
               notes=f"Ngân sách vận hành Q3/2026 — {code}", **SEED)
        for code, (alloc, _) in D.Q3_BUDGET_ACTUAL_MIL.items()
    ]  # fmt: skip
    db.add_all(budgets)
    await db.flush()
    svc = BudgetService(db)
    for b in budgets:
        await svc.check_exceeded(b)
    return len(budgets)


async def seed_invoices(db: AsyncSession) -> int:
    if await _has(db, Invoice):
        return 0
    count = 0
    for number, issued, client, tax, subtotal, vat, paid, due in (
        *D.INVOICES,
        *D.HISTORICAL_OPEN_INVOICES,
    ):
        vat_amount = subtotal * vat // 100
        total = subtotal + vat_amount
        if number in D.HV_PAID_IN_FULL:  # T-237: close most Sep HV invoices (FIN-04/05 green)
            paid = total
        status = "paid" if paid >= total else "partial" if paid else "sent"
        due_d = date.fromisoformat(due)
        inv = Invoice(
            direction="OUT", series="AB/26E", number=number,
            issue_date=date.fromisoformat(issued), due_date=due_d,
            client_id=seed_uuid("client", tax), client_name_snapshot=client,
            client_tax_code=tax, subtotal=subtotal, vat_rate_pct=vat, vat_amount=vat_amount,
            total_amount=total, paid_amount=paid, currency="VND",
            status=status, paid_at=_at(min(due_d, REFERENCE)) if status == "paid" else None,
            **SEED,
        )  # fmt: skip
        db.add(inv)
        await db.flush()
        db.add(InvoiceLine(
            invoice_id=inv.id, line_no=1, description="Hàng hóa / dịch vụ theo hợp đồng",
            quantity=1, unit_price=subtotal, amount=subtotal, currency="VND", **SEED,
        ))  # fmt: skip
        count += 1
    await db.flush()
    await InvoiceService(db).mark_overdue(REFERENCE)
    return count


async def seed_forecasts(db: AsyncSession) -> int:
    if await _has(db, Forecast):
        return 0
    created = 0
    for scenario, months in D.FORECAST_MIL.items():
        current = await db.execute(
            select(func.count()).select_from(Forecast).where(
                Forecast.scenario == scenario, Forecast.is_current.is_(True),
                Forecast.deleted_at.is_(None),
            )
        )  # fmt: skip
        conf = D.FORECAST_CONFIDENCE[scenario]
        f = Forecast(
            horizon_months=3, scenario=scenario, generated_at=_at(date(2026, 10, 1)),
            generated_by="SYSTEM", is_current=int(current.scalar_one()) == 0,
            assumptions={"confidence_pct": conf, "basis": "Kế hoạch Q4/2026"}, **SEED,
        )  # fmt: skip
        db.add(f)
        await db.flush()
        closing = D.CASH_MIL["2026-09"] * D.TR
        for period, (rev, exp) in months.items():
            closing += (rev - exp) * D.TR
            db.add(ForecastLine(
                forecast_id=f.id, period_key=period, projected_revenue=rev * D.TR,
                projected_expenses=exp * D.TR, projected_net_profit=(rev - exp) * D.TR,
                projected_closing_cash=closing, currency="VND",
                confidence_level=confidence_band(conf), **SEED,
            ))  # fmt: skip
        created += 1
    await db.flush()
    return created


async def seed_cash_flow(db: AsyncSession) -> int:
    """08 §10.4: 3 scenarios × 13 weeks; base is current → E9 cash_flow_forecast_updated."""
    if await _has(db, CashFlowForecast):
        return 0
    start = date.fromisoformat(D.CASH_FLOW_START)
    existing = await db.execute(
        select(func.count()).select_from(CashFlowForecast).where(
            CashFlowForecast.is_current.is_(True), CashFlowForecast.deleted_at.is_(None)
        )
    )  # fmt: skip
    base_current = int(existing.scalar_one()) == 0
    for scenario, pct in D.COLLECTION_PCT.items():
        closing = D.CASH_FLOW_OPENING_MIL
        lines = []
        for i, (rec, other_in, pay, payroll, opex, other_out) in enumerate(D.CASH_FLOW_BASE_MIL):
            rec_s = round(rec * pct / 85)
            net = rec_s + other_in - pay - payroll - opex - other_out
            closing += net
            lines.append((i + 1, rec_s, other_in, pay, payroll, opex, other_out, net, closing))
        low = min(lines, key=lambda ln: ln[8])
        f = CashFlowForecast(
            start_week=start, weeks=13, opening_cash=D.CASH_FLOW_OPENING_MIL * D.TR,
            currency="VND", min_projected_cash=low[8] * D.TR, min_cash_week=low[0],
            generated_at=_at(REFERENCE), generated_by="SYSTEM",
            is_current=scenario == "base" and base_current,
            assumptions={"scenario": scenario, "collection_on_time_pct": pct}, **SEED,
        )  # fmt: skip
        db.add(f)
        await db.flush()
        db.add_all(
            CashFlowForecastLine(
                forecast_id=f.id, week_no=w, week_start=start + timedelta(weeks=w - 1),
                inflow_receivables=r * D.TR, inflow_other=oi * D.TR,
                outflow_payables=p * D.TR, outflow_payroll=pr * D.TR, outflow_opex=op * D.TR,
                outflow_other=oo * D.TR, net_flow=n * D.TR, closing_cash=c * D.TR,
                currency="VND", confidence_level=band(w), **SEED,
            )
            for w, r, oi, p, pr, op, oo, n, c in lines
        )  # fmt: skip
        if f.is_current:
            await publish_in_tx(
                db, event_type="finance.cash_flow_forecast_updated", producer="finance",
                aggregate_schema="finance", aggregate_table="cash_flow_forecasts",
                aggregate_id=f.id,
                payload={"forecast_id": str(f.id), "min_projected_cash": f.min_projected_cash,
                         "min_cash_week": f.min_cash_week, "currency": "VND"},
            )  # fmt: skip
    await db.flush()
    return len(D.COLLECTION_PCT)


async def seed_finance(db: AsyncSession, recorded_by: uuid.UUID) -> Report:
    """Run inside the caller's transaction (no commit)."""
    report: Report = {
        "revenues": await seed_revenues(db),
        "expenses": await seed_expenses(db),
        "cash_positions": await seed_cash_positions(db, recorded_by),
    }
    await db.flush()
    report["budgets"] = await seed_budgets(db)
    report["invoices"] = await seed_invoices(db)
    report["forecasts"] = await seed_forecasts(db)
    report["cash_flow_forecasts"] = await seed_cash_flow(db)
    report["burn_over_forecast"] = int(
        await FinanceAnalyticsService(db).check_burn_over_forecast(REFERENCE)
    )
    return report

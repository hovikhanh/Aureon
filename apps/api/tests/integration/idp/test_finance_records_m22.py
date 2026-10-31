"""TC-M22-02/03 (M2.2, R-DEC-92) — doc type #6 "BC tài chính/sao kê số dư" → the three
finance-record ACTs via the Action Registry executor: plan → validate → run writes
Revenue/Expense/CashPosition in one SAVEPOINT; undo soft-deletes; `finance:write` is required;
a non-positive amount → `ACTION_REJECTED` (no row written).
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.deps import Principal
from app.core.errors import ActionRejectedError
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.finance.models import CashPosition, Expense, Revenue
from app.modules.idp.services.actions import finance as fin_acts  # noqa: F401  (registers ACTs)
from app.modules.idp.services.actions.executor import build_plan, missing_permissions, run_all
from app.modules.idp.services.actions.registry import ActionContext
from app.modules.idp.services.catalog import FINANCE_REPORT

pytestmark = pytest.mark.integration

_FIELDS = FINANCE_REPORT["fields"]
_ACTS = FINANCE_REPORT["action_names"]

# Periods far beyond the demo seed (08 §4 covers FY2026) so no DuplicateResourceError on cash.
_P1, _P2, _P3 = "2031-11", "2031-10", "2031-09"
_EXP_TITLE = "Thuê văn phòng M22"


def _p(role: str, pillars: tuple[str, ...] = ()) -> Principal:
    return Principal(user_id=uuid.uuid4(), role=role, scope_pillars=pillars,
                     permissions=frozenset(ROLE_PERMISSIONS[role]))  # fmt: skip


async def _live_cash(db, period: str) -> list[CashPosition]:
    stmt = select(CashPosition).where(
        CashPosition.period_key == period, CashPosition.deleted_at.is_(None)
    )
    return list((await db.execute(stmt)).scalars().all())


def _row(period: str, **over: object) -> list[tuple[str, int | None, object]]:
    base: dict[str, object] = {
        "period": period, "revenue_amount": 500_000_000, "revenue_category": "service",
        "expense_title": _EXP_TITLE, "expense_amount": 120_000_000,
        "expense_category": "office", "closing_balance": 9_000_000_000,
    }  # fmt: skip
    base.update(over)
    return [(k, 0, v) for k, v in base.items()]


async def test_finance_report_plan_runs_three_acts(db_session, idp_store) -> None:
    cfo = _p("DIR", ("F",))
    steps = build_plan(_ACTS, _FIELDS, _row(_P1))
    assert {s.act.name for s in steps} == set(_ACTS)
    assert missing_permissions(cfo, steps) == []  # DIR-F has finance:write

    done = await run_all(db_session, cfo, steps, ActionContext(source="IDP"))
    assert {o.result_refs[0]["table"] for _, o in done} == {
        "revenues", "expenses", "cash_positions",
    }  # fmt: skip

    rev = (await db_session.execute(
        select(Revenue).where(Revenue.period_key == _P1))).scalars().all()  # fmt: skip
    exp = (await db_session.execute(
        select(Expense).where(Expense.title == _EXP_TITLE))).scalars().all()  # fmt: skip
    cash = (await db_session.execute(
        select(CashPosition).where(CashPosition.period_key == _P1))).scalars().all()  # fmt: skip
    assert rev and rev[0].amount == 500_000_000 and rev[0].category == "service"
    assert exp and exp[0].amount == 120_000_000 and exp[0].category == "office"
    assert cash and cash[0].closing_balance == 9_000_000_000


async def test_undo_soft_deletes_each_record(db_session, idp_store) -> None:
    cfo = _p("DIR", ("F",))
    steps = build_plan(_ACTS, _FIELDS, _row(_P2))
    done = await run_all(db_session, cfo, steps, ActionContext(source="IDP"))
    for step, outcome in done:
        await step.act.undo(db_session, cfo, outcome)
    await db_session.flush()
    # live queries (BaseRepository filters deleted_at) see nothing for this period
    rev = (await db_session.execute(select(Revenue).where(
        Revenue.period_key == _P2, Revenue.deleted_at.is_(None)))).scalars().all()  # fmt: skip
    assert await _live_cash(db_session, _P2) == [] and rev == []


async def test_emp_cannot_run_finance_records(db_session, idp_store) -> None:
    emp = _p("EMP")
    steps = build_plan(_ACTS, _FIELDS, _row(_P1))
    assert "finance:write" in missing_permissions(emp, steps)


async def test_nonpositive_amount_rejected_no_write(db_session, idp_store) -> None:
    cfo = _p("DIR", ("F",))
    steps = build_plan(_ACTS, _FIELDS, _row(_P3, revenue_amount=0))
    with pytest.raises(ActionRejectedError) as exc:
        await run_all(db_session, cfo, steps, ActionContext(source="IDP"))
    assert exc.value.details["action_name"] == "ACT-record_revenue"
    # whole document rolled back: no expense/cash written either
    exp = (await db_session.execute(select(Expense).where(
        Expense.title == _EXP_TITLE, Expense.deleted_at.is_(None)))).scalars().all()  # fmt: skip
    assert exp == [] and await _live_cash(db_session, _P3) == []


async def test_expense_nonpositive_amount_rejected(db_session, idp_store) -> None:
    cfo = _p("DIR", ("F",))
    # revenue ok, expense amount <= 0 → ACT-record_expense rejects, whole doc rolls back
    steps = build_plan(_ACTS, _FIELDS, _row(_P3, expense_amount=0))
    with pytest.raises(ActionRejectedError) as exc:
        await run_all(db_session, cfo, steps, ActionContext(source="IDP"))
    assert exc.value.details["action_name"] == "ACT-record_expense"
    rev = (await db_session.execute(select(Revenue).where(
        Revenue.period_key == _P3, Revenue.deleted_at.is_(None)))).scalars().all()  # fmt: skip
    assert rev == []


async def test_cash_negative_balance_rejected(db_session, idp_store) -> None:
    cfo = _p("DIR", ("F",))
    steps = build_plan(_ACTS, _FIELDS, _row(_P3, closing_balance=-1))
    with pytest.raises(ActionRejectedError) as exc:
        await run_all(db_session, cfo, steps, ActionContext(source="IDP"))
    assert exc.value.details["action_name"] == "ACT-record_cash_balance"
    assert await _live_cash(db_session, _P3) == []


async def test_record_revenue_missing_date_rejected(db_session, idp_store) -> None:
    # only ACT-record_revenue, no period/recognized_on → validate returns a `no_date` row error
    cfo = _p("DIR", ("F",))
    vals: list[tuple[str, int | None, object]] = [
        ("revenue_amount", 0, 500_000_000),
        ("revenue_category", 0, "service"),
    ]
    steps = build_plan(["ACT-record_revenue"], _FIELDS, vals)
    with pytest.raises(ActionRejectedError) as exc:
        await run_all(db_session, cfo, steps, ActionContext(source="IDP"))
    assert exc.value.details["action_name"] == "ACT-record_revenue"

"""T-106 — EP-128 13-week cash flow + recompute consumers (TC-FIN-007)."""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.config import get_config
from app.core.events.envelope import OUTBOX, EventEnvelope
from app.modules.finance.events import consumers
from app.modules.finance.services.cash_flow_service import band, monday, week_index
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration

TODAY = date(2036, 3, 4)
START = monday(TODAY)
M = 1_000_000


@pytest.fixture(autouse=True)
def _reference_date(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = get_config()
    monkeypatch.setattr(cfg, "demo_mode", True)
    monkeypatch.setattr(cfg, "demo_reference_date", TODAY.isoformat())


async def _cash(api: ApiClient, balance: int = 5_000 * M) -> None:
    body = {"period": "2036-02", "closing_balance": balance, "cash_source": "bank_statement"}
    assert (await api.call("POST", "/finance/cash-positions", json=body)).status_code == 201


async def _recompute(api: ApiClient, **assumptions: Any) -> dict[str, Any]:
    body = {"assumptions": assumptions} if assumptions else None
    r = await api.call("POST", "/finance/cash-flow-forecast/recompute", json=body)
    assert r.status_code == 202, r.text
    got = await api.call("GET", "/finance/cash-flow-forecast")
    assert got.status_code == 200
    data: dict[str, Any] = got.json()["data"]
    assert data["id"] == r.json()["data"]["job_id"]
    return data


async def _invoice(api: ApiClient, due: date, amount: int, direction: str = "OUT") -> None:
    body: dict[str, Any] = {
        "direction": direction, "number": f"CF{uuid.uuid4().hex[:8]}",
        "issued_on": (due - timedelta(days=60)).isoformat(), "due_date": due.isoformat(),
        "lines": [{"description": "x", "quantity": 1, "unit_price": amount, "vat_pct": 0}],
    }  # fmt: skip
    if direction == "OUT":
        body["client_id"] = str(uuid.uuid4())
    else:
        body["counterparty_tax_code"] = uuid.uuid4().hex[:10]
    assert (await api.call("POST", "/finance/invoices", json=body)).status_code == 201


def _col(fc: dict[str, Any], key: str) -> list[int]:
    return [ln[key] for ln in fc["lines"]]


async def test_shape_and_running_balance(api: ApiClient, db_session: AsyncSession) -> None:
    await _cash(api)
    fc = await _recompute(api, fixed_opex_weekly=100 * M, payroll_monthly_override=1_000 * M)
    assert fc["weeks"] == 13 and len(fc["lines"]) == 13 and fc["start_week"] == START.isoformat()
    assert fc["opening_cash"] == 5_000 * M and fc["stale"] is False
    closing = fc["opening_cash"]
    for ln in fc["lines"]:
        net = (ln["inflow_receivables"] + ln["inflow_other"] - ln["outflow_payables"]
               - ln["outflow_payroll"] - ln["outflow_opex"] - ln["outflow_other"])  # fmt: skip
        closing += net
        assert ln["net_flow"] == net and ln["closing_cash"] == closing
    closes = _col(fc, "closing_cash")
    assert fc["min_projected_cash"] == min(closes)
    assert closes[fc["min_cash_week"] - 1] == min(closes)
    # payroll paid in the week containing each month end (Mar, Apr, May 2036)
    assert sum(_col(fc, "outflow_payroll")) == 3_000 * M
    assert set(_col(fc, "outflow_opex")) == {100 * M}
    rows = await db_session.execute(
        select(OUTBOX.c.payload).where(OUTBOX.c.event_type == "finance.cash_flow_forecast_updated")
    )
    payloads = [p for (p,) in rows if p["forecast_id"] == fc["id"]]
    assert payloads == [{"forecast_id": fc["id"], "min_projected_cash": fc["min_projected_cash"],
                         "min_cash_week": fc["min_cash_week"], "currency": "VND"}]  # fmt: skip


async def test_receivables_and_payables_by_due_week(api: ApiClient) -> None:
    await _cash(api)
    base = await _recompute(api, collection_on_time_pct=80, fixed_opex_weekly=0,
                            payroll_monthly_override=0)  # fmt: skip
    await _invoice(api, START + timedelta(days=15), 1_000 * M)  # week 3
    await _invoice(api, START - timedelta(days=30), 500 * M)  # overdue → week 1
    await _invoice(api, START + timedelta(days=8), 300 * M, direction="IN")  # week 2
    fc = await _recompute(api)  # reuses stored assumptions
    assert fc["assumptions"]["collection_on_time_pct"] == 80
    d_in = [a - b for a, b in zip(_col(fc, "inflow_receivables"),
                                  _col(base, "inflow_receivables"), strict=True)]  # fmt: skip
    assert d_in[0] == 400 * M and d_in[2] == 800 * M  # 80 % on time
    assert d_in[4] == 100 * M and d_in[6] == 200 * M  # 20 % four weeks late
    d_out = [a - b for a, b in zip(_col(fc, "outflow_payables"),
                                   _col(base, "outflow_payables"), strict=True)]  # fmt: skip
    assert d_out[1] == 300 * M and sum(d_out) == 300 * M
    old = await api.call("GET", "/finance/cash-flow-forecast", params={"as_of": "2036-03-01"})
    assert old.status_code == 404  # current forecast starts after as_of


async def test_defaults_from_history_and_stale(api: ApiClient) -> None:
    await _cash(api)
    for period in ("2035-12", "2036-01", "2036-02"):
        for amount, cat in ((900 * M, "salary"), (520 * M, "office"), (77 * M, "cogs")):
            body = {"title": "x", "amount": amount, "category": cat, "spent_on": f"{period}-05"}
            assert (await api.call("POST", "/finance/expenses", json=body)).status_code == 201
    fc = await _recompute(api)
    assert fc["assumptions"]["payroll_monthly"] == 900 * M
    assert fc["assumptions"]["opex_weekly"] == 120 * M  # 520 × 12 / 52
    assert fc["stale"] is False
    body = {"title": "y", "amount": 1, "category": "office", "spent_on": "2036-03-02"}
    await api.call("POST", "/finance/expenses", json=body)
    assert (await api.call("GET", "/finance/cash-flow-forecast")).json()["data"]["stale"] is True


async def test_no_cash_position_and_permissions(
    api: ApiClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_config(), "demo_reference_date", "1990-01-10")
    r = await api.call("GET", "/finance/cash-flow-forecast", params={"as_of": "1990-01-10"})
    assert r.status_code == 404
    assert r.json()["error"]["details"]["status_reason"] == "NO_CASH_POSITION"
    rc = await api.call("POST", "/finance/cash-flow-forecast/recompute", json={})
    assert rc.status_code == 404
    deny = await api.call("POST", "/finance/cash-flow-forecast/recompute", "CEO", json={})
    assert deny.status_code == 403
    bad = await api.call("POST", "/finance/cash-flow-forecast/recompute",
                         json={"assumptions": {"collection_on_time_pct": 120}})  # fmt: skip
    assert bad.status_code == 422


async def test_consumers_recompute(api: ApiClient, db_session: AsyncSession) -> None:
    def env(event_type: str) -> EventEnvelope:
        return EventEnvelope(
            event_id=uuid.uuid4(), event_type=event_type, occurred_at=datetime.now(UTC),
            producer="test", payload={}, tenant_id=DEFAULT_TENANT_ID,
        )  # fmt: skip

    await consumers.on_invoice_created(db_session, env("finance.invoice_created"))
    await _cash(api)
    await consumers.on_invoice_created(db_session, env("finance.invoice_created"))
    first = (await api.call("GET", "/finance/cash-flow-forecast")).json()["data"]
    assert first["assumptions"]["reason"] == "finance.invoice_created"
    await consumers.on_invoice_paid(db_session, env("finance.invoice_paid"))
    await consumers.on_salary_updated(db_session, env("hr.salary_updated"))
    cur = (await api.call("GET", "/finance/cash-flow-forecast")).json()["data"]
    assert cur["id"] != first["id"] and cur["assumptions"]["reason"] == "hr.salary_updated"


def test_helpers() -> None:
    assert monday(date(2036, 3, 9)) == date(2036, 3, 3)
    assert week_index(date(2036, 3, 3), None) == 0
    assert week_index(date(2036, 3, 3), date(2036, 3, 17)) == 2
    assert [band(w) for w in (1, 4, 5, 8, 9, 13)] == ["HIGH", "HIGH", "MEDIUM", "MEDIUM",
                                                       "LOW", "LOW"]  # fmt: skip

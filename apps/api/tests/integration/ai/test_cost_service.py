"""T-308 — AI cost & usage report (CostService, EP-119 /ai/usage, DEC-131).

TC-AI-016. Aggregates ENT-ModelCallLog over the window; budget from AI_MONTHLY_BUDGET_USD.
"""

import uuid

import pytest

from app.core.config import get_config
from app.modules.ai.models import ModelCallLog
from app.modules.ai.services.cost_service import CostService

pytestmark = pytest.mark.integration

_MICRO = 1_000_000


def _log(provider: str, model: str, *, cost_micro: int, status: str = "ok",
         latency: int = 500, tin: int = 100, tout: int = 50) -> ModelCallLog:  # fmt: skip
    return ModelCallLog(
        caller_module="ai", task_kind="chat", provider=provider, model=model,
        tokens_in=tin, tokens_out=tout, estimated_cost_micro_usd=cost_micro,
        latency_ms=latency, status=status, user_id=uuid.uuid4(),
    )  # fmt: skip


async def test_usage_aggregates_cost_and_error_rate(db_session) -> None:
    # Relative to the dev DB's existing month (live chat logs may exist — T-509).
    before = await CostService(db_session).usage(group_by="provider")
    base = {r.key: r for r in before.rows}
    b_omni = base.get("omniroute")
    b_calls = b_omni.calls if b_omni else 0
    b_cost = b_omni.cost_usd if b_omni else 0.0
    b_errors = round(b_omni.error_rate * b_omni.calls) if b_omni else 0
    b_ds = base["deepseek"].cost_usd if "deepseek" in base else 0.0
    db_session.add_all([
        _log("omniroute", "claude", cost_micro=250_000),
        _log("omniroute", "claude", cost_micro=250_000),
        _log("omniroute", "claude", cost_micro=250_000),
        _log("omniroute", "claude", cost_micro=250_000),
        _log("omniroute", "claude", cost_micro=250_000, status="error"),
        _log("deepseek", "v4", cost_micro=100_000),
    ])  # fmt: skip
    await db_session.flush()
    out = await CostService(db_session).usage(group_by="provider")
    by_key = {r.key: r for r in out.rows}
    assert by_key["omniroute"].calls == b_calls + 5
    assert by_key["omniroute"].cost_usd == pytest.approx(b_cost + 1.25)
    assert by_key["omniroute"].error_rate == pytest.approx((b_errors + 1) / (b_calls + 5))
    assert by_key["deepseek"].cost_usd == pytest.approx(b_ds + 0.1)
    # rows ordered by cost desc
    assert [r.cost_usd for r in out.rows] == sorted((r.cost_usd for r in out.rows), reverse=True)
    assert out.used_usd == pytest.approx(before.used_usd + 1.35)
    assert out.budget_usd == float(get_config().ai_monthly_budget_usd)
    assert out.over_budget is False


async def test_usage_group_by_model_and_task(db_session) -> None:
    db_session.add_all([
        _log("omniroute", "claude", cost_micro=200_000),
        _log("deepseek", "v4", cost_micro=100_000),
    ])  # fmt: skip
    await db_session.flush()
    models = {r.key for r in (await CostService(db_session).usage(group_by="model")).rows}
    assert {"claude", "v4"} <= models
    tasks = {r.key for r in (await CostService(db_session).usage(group_by="task_kind")).rows}
    assert "chat" in tasks


async def test_usage_warn_and_over_budget_flags(db_session) -> None:
    budget = float(get_config().ai_monthly_budget_usd)
    # one call at 85% of budget → warn but not over
    db_session.add(_log("omniroute", "claude", cost_micro=int(budget * 0.85 * _MICRO)))
    await db_session.flush()
    out = await CostService(db_session).usage()
    assert out.warn_80pct is True and out.over_budget is False
    # push past 100%
    db_session.add(_log("omniroute", "claude", cost_micro=int(budget * 0.20 * _MICRO)))
    await db_session.flush()
    out2 = await CostService(db_session).usage()
    assert out2.over_budget is True


async def test_usage_endpoint_requires_admin(api) -> None:
    # ai:admin only — a non-admin (EMPLOYEE) is forbidden; ADMIN gets the summary
    forbidden = await api.call("GET", "/ai/usage", role="EMPLOYEE")
    assert forbidden.status_code == 403
    ok = await api.call("GET", "/ai/usage", role="ADMIN")
    assert ok.status_code == 200
    body = ok.json()["data"]
    assert "budget_usd" in body and "rows" in body

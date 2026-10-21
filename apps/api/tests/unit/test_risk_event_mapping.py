"""TC-RSK-003 (unit) — BR-RSK-03 event → proposal mapping (pure, DEC-218)."""

from app.modules.risk.services.event_risks import RISK_EVENT_SCORING, proposal_for


def test_every_scored_event_category_is_valid() -> None:
    from app.modules.risk.services.rules import CATEGORIES

    assert all(v[0] in CATEGORIES for v in RISK_EVENT_SCORING.values())


def test_forecast_drop_against_previous_baseline() -> None:
    base = {"scenario": "base", "forecast_id": "f"}
    assert proposal_for(
        "finance.forecast_updated",
        {**base, "projected_net_profit_total": 70, "previous_net_profit_total": 100},
    )
    assert (
        proposal_for(
            "finance.forecast_updated",
            {**base, "projected_net_profit_total": 85, "previous_net_profit_total": 100},
        )
        is None
    )
    assert proposal_for(
        "finance.forecast_updated",
        {**base, "projected_net_profit_total": -20, "previous_net_profit_total": -10},
    )
    assert (
        proposal_for(
            "finance.forecast_updated",
            {**base, "projected_net_profit_total": -5, "previous_net_profit_total": -10},
        )
        is None
    )
    assert proposal_for("finance.forecast_updated", base) is None


def test_unknown_or_incomplete_events() -> None:
    assert proposal_for("hr.salary_updated", {"x": 1}) is None
    assert proposal_for("finance.budget_exceeded", {}) is None
    assert proposal_for("finance.burn_over_forecast", {"period_key": ""}) is None
    lost = proposal_for("sales.deal_closed_lost", {"deal_id": "d", "deal_value": 10**9})
    assert lost is not None and lost.escalated is False and lost.links == {"deal_id": "d"}

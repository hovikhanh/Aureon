"""TC-M5-10 (R-DEC-158) — `MODEL_PRICING_JSON`: cached input, explicit `unpriced`, strict schema.

Prices below are test inputs, not the configured table (that lives in `.env`, sourced in R-DEC-158).
"""

import json

import pytest

from app.core.model_gateway.adapters import anthropic_usage, openai_usage
from app.core.model_gateway.cost import _pricing, estimate_cost_micro_usd, validate_pricing

TABLE = json.dumps({
    "_meta": {"currency": "USD", "unit": "per 1M tokens", "checked": "2026-11-03"},
    "omniroute:claude-sonnet-5": {"in": 2, "out": 10, "cached_in": 0.2, "cache_write": 2.5},
    "omniroute:deepseek/deepseek-v4.1-flash": {"in": 0.3, "out": 1.2, "cached_in": 0.006},
    "openrouter:legacy": {"in": 1, "out": 2},
    "openrouter:secret-sauce": {"unpriced": True, "note": "no public price"},
})  # fmt: skip


def test_legacy_in_out_entries_still_price_as_before() -> None:
    # 1000 in × $1/M + 500 out × $2/M = 1000 + 1000 µUSD
    assert estimate_cost_micro_usd(TABLE, "openrouter", "legacy", 1000, 500) == 2000


def test_matches_the_cost_deepseek_reported_on_a_live_call() -> None:
    """Live OmniRoute call 2026-11-03: 44 prompt + 20 completion tokens, provider `cost`
    3.72e-05 USD = 37.2 µUSD (peak price) → stored as 37 µUSD (integer micro-USD)."""
    assert estimate_cost_micro_usd(TABLE, "omniroute", "deepseek/deepseek-v4.1-flash", 44, 20) == 37


def test_cached_and_cache_write_tokens_use_their_own_price() -> None:
    # 10_000 prompt tokens: 6_000 cache reads, 1_000 cache writes, 3_000 fresh; 2_000 output
    got = estimate_cost_micro_usd(
        TABLE, "omniroute", "claude-sonnet-5", 10_000, 2_000, cached_in=6_000, cache_write=1_000
    )
    assert got == 3_000 * 2 + 6_000 * 0.2 + 1_000 * 2.5 + 2_000 * 10  # 29_700


def test_missing_cache_price_falls_back_to_input_price() -> None:
    # deepseek has no cache_write price → written tokens cost the input price
    got = estimate_cost_micro_usd(
        TABLE, "omniroute", "deepseek/deepseek-v4.1-flash", 1_000_000, 0, cache_write=1_000_000
    )
    assert got == 300_000


def test_cache_counts_never_exceed_the_prompt() -> None:
    # a bogus provider report (more cached than prompt) cannot produce a negative fresh count
    got = estimate_cost_micro_usd(
        TABLE, "omniroute", "claude-sonnet-5", 100, 0, cached_in=500, cache_write=50
    )
    assert got == round(100 * 0.2)


def test_unpriced_and_unknown_models_cost_zero_and_meta_is_ignored() -> None:
    assert estimate_cost_micro_usd(TABLE, "openrouter", "secret-sauce", 5_000, 5_000) == 0
    assert estimate_cost_micro_usd(TABLE, "openrouter", "never-listed", 5_000, 5_000) == 0
    table = _pricing(TABLE)
    assert table["openrouter:secret-sauce"] is None
    assert "_meta" not in table


@pytest.mark.parametrize(
    "bad",
    [
        "[]",
        '{"no-colon": {"in": 1, "out": 1}}',
        '{"p:m": {"in": 1}}',
        '{"p:m": {"in": -1, "out": 1}}',
        '{"p:m": {"in": true, "out": 1}}',
        '{"p:m": {"in": 1, "out": 1, "cached": 0.1}}',
        '{"p:m": {"unpriced": true, "in": 1}}',
        '{"p:m": 3}',
        "{not json",
    ],
)
def test_malformed_tables_fail_fast(bad: str) -> None:
    with pytest.raises(ValueError):
        validate_pricing(bad)


def test_openai_compatible_usage_keeps_cached_tokens_inside_the_prompt() -> None:
    u = openai_usage({
        "prompt_tokens": 44, "completion_tokens": 20,
        "prompt_tokens_details": {"cached_tokens": 30}, "cache_creation_input_tokens": 4,
    })  # fmt: skip
    assert (u.tokens_in, u.tokens_out, u.cached_in, u.cache_write) == (44, 20, 30, 4)
    assert openai_usage({"prompt_tokens": 48, "completion_tokens": 5}).cached_in == 0


def test_anthropic_usage_adds_cache_tokens_back_to_the_prompt() -> None:
    u = anthropic_usage({
        "input_tokens": 100, "output_tokens": 7,
        "cache_read_input_tokens": 900, "cache_creation_input_tokens": 50,
    })  # fmt: skip
    assert (u.tokens_in, u.cached_in, u.cache_write, u.tokens_out) == (1050, 900, 50, 7)

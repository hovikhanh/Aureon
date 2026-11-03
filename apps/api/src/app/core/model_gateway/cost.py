"""Cost estimate (07 §6.3): `MODEL_PRICING_JSON` = USD per 1M tokens by `provider:model`.

Integer micro-USD (no float in storage): cost = tokens × usd_per_1M (since 1 USD = 1e6 µUSD
and the price is per 1e6 tokens, the factors cancel). Unknown model → 0 (local / fixture).

Schema (R-DEC-158, backward compatible with the original `{"in", "out"}`)::

    {
      "_meta": {...},                                  # any "_"-key: documentation, ignored
      "omniroute:claude-sonnet-5": {
        "in": 2, "out": 10,                            # required, ≥ 0
        "cached_in": 0.2,                              # optional: prompt-cache read price
        "cache_write": 2.5                             # optional: prompt-cache write price
      },
      "openrouter:some/model": {"unpriced": true, "note": "no public price"}
    }

The key's model is the model **the provider returns** (OmniRoute answers `claude-sonnet-5` for a
request to `cc/claude-sonnet-5`), because that is what `ModelCallLog.model` stores. A provider
reports cached / cache-write tokens as parts of the prompt; they are priced at `cached_in` /
`cache_write` when given, else at `in`. `"unpriced": true` records explicitly that no public price
exists — the call is stored at $0 and EP-AI-15 counts it in `unpriced_calls` (R-DEC-155).
"""

import json
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from typing import Any

_PRICE_FIELDS = ("in", "out", "cached_in", "cache_write")
_ENTRY_FIELDS = frozenset({*_PRICE_FIELDS, "unpriced", "note", "source", "checked"})


@dataclass(frozen=True)
class Price:
    inp: Decimal
    out: Decimal
    cached_in: Decimal | None = None
    cache_write: Decimal | None = None


def _num(key: str, field: str, value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise ValueError(f"MODEL_PRICING_JSON[{key!r}].{field} must be a number")
    d = Decimal(str(value))
    if not d.is_finite() or d < 0:
        raise ValueError(f"MODEL_PRICING_JSON[{key!r}].{field} must be a finite number ≥ 0")
    return d


@lru_cache(maxsize=8)
def _pricing(raw: str) -> dict[str, Price | None]:
    """Parsed table: `None` for an explicit `unpriced` entry. Raises on any malformed entry so a
    typo fails fast at startup instead of silently pricing calls at $0."""
    data = json.loads(raw or "{}")
    if not isinstance(data, dict):
        raise ValueError("MODEL_PRICING_JSON must be an object")
    out: dict[str, Price | None] = {}
    for key, v in data.items():
        if key.startswith("_"):
            continue  # `_meta`: source, date, currency — documentation only
        if ":" not in key:
            raise ValueError(f"MODEL_PRICING_JSON key {key!r} must be 'provider:model'")
        if not isinstance(v, dict):
            raise ValueError(f"MODEL_PRICING_JSON[{key!r}] must be an object")
        unknown = set(v) - _ENTRY_FIELDS
        if unknown:
            raise ValueError(f"MODEL_PRICING_JSON[{key!r}] has unknown fields {sorted(unknown)}")
        if v.get("unpriced") is True:
            if any(f in v for f in _PRICE_FIELDS):
                raise ValueError(f"MODEL_PRICING_JSON[{key!r}] is unpriced but carries prices")
            out[key] = None
            continue
        if "in" not in v or "out" not in v:
            raise ValueError(f"MODEL_PRICING_JSON[{key!r}] needs both 'in' and 'out'")
        out[key] = Price(
            _num(key, "in", v["in"]), _num(key, "out", v["out"]),
            _num(key, "cached_in", v["cached_in"]) if "cached_in" in v else None,
            _num(key, "cache_write", v["cache_write"]) if "cache_write" in v else None,
        )  # fmt: skip
    return out


def validate_pricing(raw: str) -> None:
    """Startup check (fail fast, 07 §7): raises `ValueError` on a malformed table."""
    _pricing(raw)


def estimate_cost_micro_usd(
    pricing_json: str, provider: str, model: str, tin: int, tout: int,
    cached_in: int = 0, cache_write: int = 0,
) -> int:  # fmt: skip
    price = _pricing(pricing_json).get(f"{provider}:{model}")
    if price is None:
        return 0
    cached = max(0, min(cached_in, tin))
    written = max(0, min(cache_write, tin - cached))
    fresh = tin - cached - written
    cost = (
        Decimal(fresh) * price.inp
        + Decimal(cached) * (price.cached_in if price.cached_in is not None else price.inp)
        + Decimal(written) * (price.cache_write if price.cache_write is not None else price.inp)
        + Decimal(tout) * price.out
    )
    return int(cost.quantize(Decimal(1), rounding=ROUND_HALF_UP))

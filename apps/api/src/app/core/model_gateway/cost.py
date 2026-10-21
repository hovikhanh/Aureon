"""Cost estimate (07 §6.3): `MODEL_PRICING_JSON` = USD per 1M tokens by `provider:model`.

Integer micro-USD (no float in storage): cost = tokens × usd_per_1M (since 1 USD = 1e6 µUSD
and the price is per 1e6 tokens, the factors cancel). Unknown model → 0 (local / fixture).
"""

import json
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache


@lru_cache(maxsize=8)
def _pricing(raw: str) -> dict[str, tuple[Decimal, Decimal]]:
    data = json.loads(raw or "{}")
    if not isinstance(data, dict):
        raise ValueError("MODEL_PRICING_JSON must be an object")
    return {
        key: (Decimal(str(v.get("in", 0))), Decimal(str(v.get("out", 0))))
        for key, v in data.items()
    }


def estimate_cost_micro_usd(
    pricing_json: str, provider: str, model: str, tin: int, tout: int
) -> int:
    price = _pricing(pricing_json).get(f"{provider}:{model}")
    if price is None:
        return 0
    cost = Decimal(tin) * price[0] + Decimal(tout) * price[1]
    return int(cost.quantize(Decimal(1), rounding=ROUND_HALF_UP))

"""Trường trọng yếu (FR-DC-16, R-DEC-69) — the single rule for `is_critical`.

A field is critical when its name is in `CRITICAL_FIELD_NAMES`, its `value_type` is money or
tax code, or it is sensitivity level 4 — whatever the schema says (Admin cannot clear it; the
schema flag can only add fields). Critical fields never go STP and must be confirmed one by one
before approve (`accept_all_high` skips them); C1 values count as confirmed by their entrant.
"""

from collections.abc import Iterable
from typing import Any

CRITICAL_VALUE_TYPES = frozenset({"money", "tax_code"})
# FR-DC-16: số tiền, số tài khoản, MST, lương, giá trị hợp đồng (+ CCCD).
CRITICAL_FIELD_NAMES = frozenset({
    "amount", "subtotal", "vat_amount", "total_amount", "bank_account", "tax_code",
    "seller_tax_code", "buyer_tax_code", "salary", "contract_value", "national_id",
})  # fmt: skip


def forced_critical(spec: dict[str, Any]) -> bool:
    """True when the rule (not the schema flag) makes the field critical."""
    return (
        spec.get("name") in CRITICAL_FIELD_NAMES
        or spec.get("value_type") in CRITICAL_VALUE_TYPES
        or int(spec.get("sensitivity_level") or 2) >= 4
    )


def is_critical(spec: dict[str, Any]) -> bool:
    return bool(spec.get("is_critical")) or forced_critical(spec)


def unconfirmed(fields: Iterable[Any]) -> list[str]:
    """Names of critical fields nobody confirmed/corrected yet (approve guard, EP-DC-08)."""
    out: set[str] = set()
    for f in fields:
        manual = (f.source_location or {}).get("kind") == "manual"
        if f.is_critical and f.corrected_by is None and not manual:
            out.add(f.field_name)
    return sorted(out)

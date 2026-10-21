"""Content-based PII detection (DEC-176) — defense in depth beyond the key-name checks.

Used by the event outbox (reject) and the audit writer (mask). High-confidence patterns only:
CCCD (12 digits), VN mobile (0 + 9–10 digits), e-mail, bank account (10–16 digits; overlaps
the others — the more specific type wins). CMND (9 digits) is deliberately left out: too many
false positives on amounts / codes. Only `str` values are scanned — numbers are aggregates.

UUIDs are blanked before scanning so an all-digit UUID group is never a "CCCD". A hit never
carries the raw value: `value_masked` keeps at most the last 4 characters.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

PIIType = Literal["EMAIL", "CCCD", "PHONE", "BANK_ACCOUNT", "FIELD"]
MASK = "••••"

# Order = priority when spans overlap (most specific first).
PII_PATTERNS: tuple[tuple[PIIType, re.Pattern[str]], ...] = (
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("CCCD", re.compile(r"(?<![\d.,])\d{12}(?![\d.,]\d)")),
    ("PHONE", re.compile(r"(?<![\d.,])0\d{9,10}(?![\d.,]\d)")),
    ("BANK_ACCOUNT", re.compile(r"(?<![\d.,])\d{10,16}(?![\d.,]\d)")),
)
_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)


@dataclass(frozen=True)
class PIIHit:
    type: PIIType
    value_masked: str
    offset: int
    path: str = ""


def mask_value(value: str) -> str:
    """`••••` + last 4 chars (e-mail: `••••@domain`). Short values are fully masked."""
    if "@" in value:
        return MASK + value[value.index("@") :]
    return MASK + value[-4:] if len(value) > 8 else MASK


def _spans(text: str) -> list[tuple[PIIType, int, int]]:
    blanked = _UUID.sub(lambda m: "#" * len(m.group()), text)
    taken: list[tuple[PIIType, int, int]] = []
    for kind, pattern in PII_PATTERNS:
        for m in pattern.finditer(blanked):
            start, end = m.span()
            if not any(start < e and s < end for _, s, e in taken):
                taken.append((kind, start, end))
    return sorted(taken, key=lambda t: t[1])


def detect_content_pii(text: str) -> list[PIIHit]:
    return [PIIHit(k, mask_value(text[s:e]), s) for k, s, e in _spans(text)]


def mask_text(text: str) -> str:
    out, pos = [], 0
    for _, start, end in _spans(text):
        out += [text[pos:start], mask_value(text[start:end])]
        pos = end
    out.append(text[pos:])
    return "".join(out)


def scan_payload(
    payload: Any, *, forbidden_keys: frozenset[str] = frozenset(), path: str = "payload"
) -> list[PIIHit]:
    """Recursive scan: forbidden key names (`FIELD`) + PII patterns in every string value."""
    hits: list[PIIHit] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            sub = f"{path}.{key}"
            if str(key).lower() in forbidden_keys:
                hits.append(PIIHit("FIELD", MASK, 0, sub))
                continue
            hits += scan_payload(value, forbidden_keys=forbidden_keys, path=sub)
    elif isinstance(payload, list | tuple):
        for i, item in enumerate(payload):
            hits += scan_payload(item, forbidden_keys=forbidden_keys, path=f"{path}[{i}]")
    elif isinstance(payload, str):
        hits += [
            PIIHit(h.type, h.value_masked, h.offset, path) for h in detect_content_pii(payload)
        ]
    return hits


def mask_payload(payload: Any, *, masked_keys: frozenset[str] = frozenset()) -> Any:
    """Copy with masked-key values → `••••` and PII inside strings masked (audit, never raise)."""
    if isinstance(payload, Mapping):
        return {
            k: MASK if str(k).lower() in masked_keys else mask_payload(v, masked_keys=masked_keys)
            for k, v in payload.items()
        }
    if isinstance(payload, list | tuple):
        return [mask_payload(v, masked_keys=masked_keys) for v in payload]
    if isinstance(payload, str):
        return mask_text(payload)
    return payload

"""PII pre-scan + classification decision for an AI turn (T-303/T-309, FR-AI-10, 07 §Bảo mật).

Two guards run before any model call:

* `classify_prompt(text)` — scans the user's message for content PII (`core/pii`). A salary /
  level-4 signal (`SALARY`) → `SECRET` (the gateway then raises `SecretDataBlockedError`, never
  an LLM — 07 §6.5). Any other PII hit (CCCD / phone / e-mail / bank) → `CONFIDENTIAL`, which the
  gateway routes to the local model (`ollama`), never cloud. No PII → `INTERNAL`.
* `wrap_data(label, body)` — wraps tool results / document text in the `<<<DATA … DATA>>>`
  delimiter so the model treats them as data, not instructions (prompt-injection guard).

The scan is deliberately conservative: it elevates classification (safer routing) but never
lowers it. Tool-result classification (§7.4) is handled separately by the executor.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.core.model_gateway.types import Classification
from app.core.pii import PIIHit, PIIType, detect_content_pii, mask_text, pii_spans

# Salary / compensation signals (level-4, 02 §5.3) → SECRET. VI + EN, number-adjacent.
_SALARY = re.compile(
    r"(lương|tiền\s*lương|thu\s*nhập|bảng\s*lương|salary|payroll|compensation|"
    r"mức\s*lương|hệ\s*số\s*lương)",
    re.IGNORECASE,
)

DATA_OPEN, DATA_CLOSE = "<<<DATA", "DATA>>>"


@dataclass(frozen=True)
class PromptClassification:
    classification: Classification
    reason: str
    pii_hits: tuple[PIIHit, ...]
    has_salary: bool


def classify_prompt(text: str) -> PromptClassification:
    """Decide the routing classification for a user message (never downgrades below INTERNAL)."""
    has_salary = bool(_SALARY.search(text))
    hits = tuple(detect_content_pii(text))
    if has_salary:
        return PromptClassification("SECRET", "prompt: salary/level-4 term", hits, True)
    if hits:
        kinds = ",".join(sorted({h.type for h in hits}))
        return PromptClassification("CONFIDENTIAL", f"prompt: pii ({kinds})", hits, False)
    return PromptClassification("INTERNAL", "prompt: no pii", (), False)


def redact_for_log(text: str) -> str:
    """Mask PII in a message before it ever reaches a log line (never the raw prompt)."""
    return mask_text(text)


# 02 §5.3 sensitivity → 5.5 model-prompt rule: drop level-4, tokenise level-3.
_LEVEL_4: frozenset[PIIType] = frozenset({"CCCD", "BANK_ACCOUNT"})  # secret → never to any LLM
_LEVEL_3: frozenset[PIIType] = frozenset({"EMAIL", "PHONE"})  # confidential → stable pseudonym
_REDACTED = "[REDACTED]"
# a contact pattern (e-mail/phone) belongs to an internal employee or an external client
_CLIENT_HINT = re.compile(r"(khách|client|customer|đối\s*tác|nhà\s*cung\s*cấp|vendor)", re.I)


def _token(value: str, prefix: str) -> str:
    """Stable per-value pseudonym `EMP-xxxx` / `CLI-xxxx` (deterministic, no raw value)."""
    digest = hashlib.sha256(value.encode()).hexdigest()[:4].upper()
    return f"{prefix}-{digest}"


def scrub_for_model(text: str) -> str:
    """Sanitise text before it enters the model context (5.5): drop level-4 PII entirely and
    replace level-3 contact PII with a stable `EMP-xxxx` / `CLI-xxxx` code (salary numbers are
    handled upstream by `classify_prompt` → SECRET, so no LLM is called at all).
    """
    spans = pii_spans(text)
    if not spans:
        return text
    out: list[str] = []
    pos = 0
    for kind, start, end in spans:
        out.append(text[pos:start])
        raw = text[start:end]
        if kind in _LEVEL_4:
            out.append(_REDACTED)
        elif kind in _LEVEL_3:
            prefix = "CLI" if _CLIENT_HINT.search(text[max(0, start - 24) : start]) else "EMP"
            out.append(_token(raw, prefix))
        else:
            out.append(_REDACTED)
        pos = end
    out.append(text[pos:])
    return "".join(out)


def wrap_data(label: str, body: str) -> str:
    """Delimit untrusted data (tool result, document text) for the model (injection guard)."""
    return f"{DATA_OPEN} {label}\n{body}\n{DATA_CLOSE}"

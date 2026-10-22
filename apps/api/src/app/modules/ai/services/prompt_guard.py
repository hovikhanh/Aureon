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

import re
from dataclasses import dataclass

from app.core.model_gateway.types import Classification
from app.core.pii import PIIHit, detect_content_pii, mask_text

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


def wrap_data(label: str, body: str) -> str:
    """Delimit untrusted data (tool result, document text) for the model (injection guard)."""
    return f"{DATA_OPEN} {label}\n{body}\n{DATA_CLOSE}"

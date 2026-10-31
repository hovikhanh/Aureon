"""Hard grounding validator (10 §8, AI-R09/R10, FR-AIQ-01) — M2.4 R-DEC-105.

Every number the assistant states must trace to a `tool_result` / `SourceRef` (P05). This runs
AFTER the tool-calling loop and BEFORE the answer is persisted:

* collect the grounded value set — `SourceRef.value` plus every numeric leaf inside each
  `tool_result.data` (VND is stored in the smallest unit, so magnitudes are compared with a small
  relative tolerance and against common VI unit multipliers: nghìn / triệu / tỷ);
* scan the answer for number tokens (VI formatting: ``1.250.000``, ``1,2 tỷ``, ``12,5%``,
  ``300 tỷ``), and DROP any token that matches no grounded value, appending the warning
  ``ai.warn.ungrounded_number_removed``;
* if the answer carries no number at all and nothing was grounded (no sources), surface
  ``AI_NO_DATA_AVAILABLE`` (HTTP stays 200, 10 §1.4) — never fabricate.

Pure/stateless: no LLM, no DB. The caller owns persistence and the final warning list.
"""

from __future__ import annotations

import re
from typing import Any

UNGROUNDED_WARNING = "ai.warn.ungrounded_number_removed"
NO_DATA_WARNING = "AI_NO_DATA_AVAILABLE"

# relative tolerance for a magnitude match (rounding / unit display), plus VI unit multipliers
_REL_TOL = 0.02
_UNIT_MULT: dict[str, float] = {
    "nghìn": 1e3, "ngàn": 1e3, "triệu": 1e6, "tr": 1e6, "tỷ": 1e9, "tỉ": 1e9,
}  # fmt: skip
# Protected spans scanned first and left untouched: entity codes (``NV-0001``, ``EMP-1234``,
# ``CLI-42``) and dates (``06/11/2026``, ``2026-10-20``) — these carry digits that are labels, not
# grounded metric values.
_PROTECTED_RE = re.compile(
    r"[A-Za-zÀ-ỹ]+-?\d[\d.-]*"  # a code: letters then digits (optionally hyphenated)
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"  # dd/mm/yyyy or dd-mm-yyyy
    r"|\d{4}-\d{1,2}-\d{1,2}",  # ISO yyyy-mm-dd
)
# a number token: digits with VI thousands `.`/`,` grouping, optional decimal, optional unit word.
# `label` captures a leading period/ordinal word so "quý 3" / "năm 2026" / "Q4" are NOT treated as
# data numbers (they are time labels, not grounded metric values).
_NUM_RE = re.compile(
    r"(?P<label>(?:quý|q|tháng|năm|kỳ|tuần|ngày|lần|top|hạng)\s*)?"
    r"(?P<num>\d[\d.,]*)\s*(?P<unit>nghìn|ngàn|triệu|tr|tỷ|tỉ|%)?",
    re.IGNORECASE,
)
# a year-like bare integer (1900–2099) with no unit is a date label, not a metric
_YEAR_RE = re.compile(r"^(19|20)\d{2}$")


def _vi_to_float(raw: str) -> float | None:
    """Parse a VI-formatted numeric token (``1.250.000``, ``1,2``, ``12,5``) to a float."""
    s = raw.strip().rstrip(".,")
    if not s or not any(c.isdigit() for c in s):
        return None
    if "." in s and "," in s:  # grouping `.` + decimal `,`  → 1.250.000,50
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:  # decimal `,` (1,2) OR grouping used alone → treat `,` as decimal
        s = s.replace(".", "").replace(",", ".")
    else:  # only `.`: VI grouping when every group after the first is 3 digits
        parts = s.split(".")
        s = "".join(parts) if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]) else s
    try:
        return float(s)
    except ValueError:
        return None


def _numeric_leaves(value: Any, out: list[float]) -> None:
    """Collect every numeric leaf from a tool-result `data` structure (int/float, not bool)."""
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        out.append(float(value))
    elif isinstance(value, dict):
        for v in value.values():
            _numeric_leaves(v, out)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _numeric_leaves(v, out)


def grounded_values(sources: list[Any], tool_data: list[dict[str, Any]]) -> set[float]:
    """The set of magnitudes the answer is allowed to state (abs value of each grounded number)."""
    vals: list[float] = []
    for s in sources:
        v = s.get("value") if isinstance(s, dict) else getattr(s, "value", None)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            vals.append(float(v))
    for data in tool_data:
        _numeric_leaves(data, vals)
    return {abs(v) for v in vals}


def _matches(token: float, grounded: set[float]) -> bool:
    """A token is grounded if its magnitude (or a VI-unit scaling) matches within tolerance."""
    candidates = {token} | {token * m for m in _UNIT_MULT.values()}
    for g in grounded:
        for c in candidates:
            if g == 0 and c == 0:
                return True
            if g != 0 and abs(c - g) <= _REL_TOL * abs(g):
                return True
    return False


def enforce_grounding(
    answer: str,
    sources: list[Any],
    tool_data: list[dict[str, Any]],
    *,
    data_requested: bool = False,
) -> tuple[str, list[str]]:
    """Return `(clean_answer, warnings)`: ungrounded numbers removed, no-data flagged.

    `sources` / `tool_data` are the grounded evidence gathered during the turn. `data_requested`
    tells the validator the turn tried to answer with data (≥1 READ tool ran) — only then does an
    answer with no grounded evidence surface ``AI_NO_DATA_AVAILABLE`` (a plain action/confirmation
    reply with no numbers is not a no-data case).
    """
    warnings: list[str] = []
    grounded = grounded_values(sources, tool_data)
    saw_number = False
    removed = False

    def repl(m: re.Match[str]) -> str:
        nonlocal saw_number, removed
        unit = (m.group("unit") or "").lower()
        raw = m.group("num")
        # a time/ordinal label ("quý 3", "năm 2026", "Q4") or a bare year → not a data number
        if m.group("label") or (not unit and _YEAR_RE.match(raw.replace(".", ""))):
            return m.group(0)
        if unit == "%":  # percentages are compared on their bare value
            num = _vi_to_float(raw)
            saw_number = True
            if num is not None and _matches(num, grounded):
                return m.group(0)
            removed = True
            return ""
        num = _vi_to_float(raw)
        if num is None:
            return m.group(0)
        saw_number = True
        token = num * _UNIT_MULT.get(unit, 1.0)
        if _matches(token, grounded):
            return m.group(0)
        removed = True
        return ""

    # scan only the text OUTSIDE protected spans (codes / dates stay verbatim)
    parts: list[str] = []
    last = 0
    for pm in _PROTECTED_RE.finditer(answer):
        parts.append(_NUM_RE.sub(repl, answer[last : pm.start()]))
        parts.append(pm.group(0))
        last = pm.end()
    parts.append(_NUM_RE.sub(repl, answer[last:]))
    clean = "".join(parts)
    clean = re.sub(r"[ \t]{2,}", " ", clean).strip()
    if removed:
        warnings.append(UNGROUNDED_WARNING)
    if data_requested and not saw_number and not grounded:
        warnings.append(NO_DATA_WARNING)
    return clean, warnings

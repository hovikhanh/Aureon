"""Hard grounding validator (10 §8, AI-R09/R10, FR-AIQ-01) — M2.4 R-DEC-105, F-H1.

Every number the assistant states must trace to a `tool_result` / `SourceRef` (P05). This runs
AFTER the tool-calling loop and BEFORE the answer is persisted:

* collect the grounded value set — `SourceRef.value`, every numeric leaf inside each
  `tool_result.data`, and the length of every list there (VND is stored in the smallest unit);
* scan the answer for number tokens (VI formatting: ``1.250.000``, ``1,2 tỷ``, ``12,5%``,
  ``300 tỷ``, ``USD500000``) and spelled numbers with a scale (``ba trăm tỷ``, ``hai mươi phần
  trăm``). A token that matches no grounded value is replaced by a visible placeholder and the
  warning ``ai.warn.ungrounded_number_removed`` is appended;
* if the answer carries no number at all and nothing was grounded (no sources), surface
  ``AI_NO_DATA_AVAILABLE`` (HTTP stays 200, 10 §1.4) — never fabricate.

A match allows display rounding only: the token must round to the source at the precision it was
written in (``82%`` for 82,4 is fine, ``83,5%`` for 82 is not). There is no relative tolerance.

A word in front of a number makes it a time/ordinal label only when the number has no unit and is
in the range of that label (``tháng 9``, ``quý 3``, ``năm 2026``, ``top 5``). ``tháng 300 tỷ`` is
a data number. Codes are upper-case identifiers (``NV-0001``, ``EMP-1234``, ``Q4``), never a
currency prefix.

Limits: a number is matched against the whole evidence set, so the right number on the wrong
metric still passes. Derived numbers (a difference the model computed) are removed.

Pure/stateless: no LLM, no DB. The caller owns persistence and the final warning list.
"""

from __future__ import annotations

import re
from typing import Any

UNGROUNDED_WARNING = "ai.warn.ungrounded_number_removed"
NO_DATA_WARNING = "AI_NO_DATA_AVAILABLE"
PLACEHOLDER = {"vi": "[chưa có nguồn]", "en": "[no source]"}

# VI unit words; a chain multiplies (`nghìn tỷ`, `trăm triệu`).
_UNIT_MULT: dict[str, float] = {
    "chục": 10, "trăm": 100, "nghìn": 1e3, "ngàn": 1e3, "triệu": 1e6, "tr": 1e6, "tỷ": 1e9,
    "tỉ": 1e9,
}  # fmt: skip
_SCALES = (1.0, 1e3, 1e6, 1e9)  # a bare token may be written in a unit stated elsewhere
_ROUNDED_REL = 0.005  # trailing zeros are rounding, within 0,5 % of the value at most
_NOT_TY = r"(?!\s+(?:lệ|trọng|giá|suất))"  # `tỷ lệ`, `tỷ trọng`, `tỷ giá` are words, not units
_UNIT_WORD = rf"(?:chục|trăm|nghìn|ngàn|triệu|tr|tỷ{_NOT_TY}|tỉ{_NOT_TY})\b"
_MONEY_WORD = r"(?:\s*(?:đồng|đ|vnđ|vnd|usd)\b)?"

# Protected spans scanned first and left untouched: entity codes, dates, clock times, citations
# `[1]` and list numbering. These carry digits that are labels, not metric values.
_PROTECTED_RE = re.compile(
    r"\b(?!(?:USD|VND|EUR|GBP|JPY|SGD|CNY)\d)[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b"  # NV-0001
    r"|\b(?!(?:USD|VND|EUR|GBP|JPY|SGD|CNY)\d)[A-Z]{1,6}\d[0-9A-Z]*\b"  # Q4, T9, DOC09
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"  # dd/mm/yyyy or dd-mm-yyyy
    r"|\d{4}-\d{1,2}-\d{1,2}"  # ISO yyyy-mm-dd
    r"|(?i:(?:ngày|hạn|từ|đến)\s+)\d{1,2}/\d{1,2}\b"  # ngày 20/10
    r"|\b\d{1,2}:\d{2}\b"  # 14:30
    r"|\[\d{1,3}\]"  # citation [1]
    r"|^[ \t]*\d{1,2}[.)](?=\s)",  # list numbering
    re.MULTILINE,
)
# a number token: digits with `.`/`,` grouping, optional decimal, optional unit chain or percent
_NUM_RE = re.compile(
    r"(?:(?<![\w])(?P<label>quý|q|tháng|năm|kỳ|tuần|ngày|lần|top|hạng)\s*)?"
    r"(?<![\d.,])(?P<num>\d[\d.,]*)"
    rf"(?P<unit>\s*(?:%|phần\s+trăm\b|(?:{_UNIT_WORD}\s*)+))?"
    rf"(?P<money>{_MONEY_WORD})",
    re.IGNORECASE,
)
_LABEL_RANGE: dict[str, tuple[int, int]] = {
    "quý": (1, 4), "q": (1, 4), "tháng": (1, 12), "tuần": (1, 53), "ngày": (1, 31), "kỳ": (1, 24),
    "năm": (1900, 2099), "lần": (1, 99), "top": (1, 100), "hạng": (1, 100),
}  # fmt: skip
# a year-like bare integer (1900–2099) with no unit is a date label, not a metric
_YEAR_RE = re.compile(r"^(19|20)\d{2}$")

_DIGIT_WORD = {
    "không": 0, "một": 1, "mốt": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4, "năm": 5, "lăm": 5,
    "sáu": 6, "bảy": 7, "bẩy": 7, "tám": 8, "chín": 9,
}  # fmt: skip
_SCALE_WORD = {"nghìn": 1e3, "ngàn": 1e3, "triệu": 1e6, "tỷ": 1e9, "tỉ": 1e9}
_NUMBER_WORD = (
    "|".join(_DIGIT_WORD)
    + rf"|mười|mươi|chục|trăm|nghìn|ngàn|triệu|tỷ{_NOT_TY}|tỉ{_NOT_TY}|lẻ|linh|rưỡi"
)
_WORDS_RE = re.compile(
    rf"(?P<vague>(?<!\w)(?:hàng|vài|mấy|dăm)\s+)?"
    rf"(?<!\w)(?P<words>(?:(?:{_NUMBER_WORD})(?!\w)\s*)+)"
    rf"(?P<pct>phần\s+trăm\b)?(?P<money>{_MONEY_WORD})",
    re.IGNORECASE,
)


def _vi_numbers(raw: str) -> list[tuple[float, int]]:
    """Readings of a numeric token as `(value, decimals)` — two when it is ambiguous (`1.250` is
    1250 in VI and 1,25 in EN; `1,250` likewise)."""
    s = raw.strip().rstrip(".,")
    if not s or not any(c.isdigit() for c in s):
        return []
    dots, commas = s.count("."), s.count(",")
    if dots and commas:  # the last separator is the decimal one
        dec_sep, grp_sep = (",", ".") if s.rfind(",") > s.rfind(".") else (".", ",")
        return _reading(s.replace(grp_sep, "").replace(dec_sep, "."))
    sep = "." if dots else "," if commas else ""
    if not sep:
        return _reading(s)
    parts = s.split(sep)
    grouped = all(len(p) == 3 for p in parts[1:]) and 0 < len(parts[0]) <= 3 and s[0] != "0"
    if len(parts) > 2:  # several separators can only be grouping
        return _reading("".join(parts))
    if grouped:
        return _reading("".join(parts)) + _reading(".".join(parts))
    return _reading(".".join(parts))


def _reading(s: str) -> list[tuple[float, int]]:
    try:
        return [(float(s), len(s.partition(".")[2]))]
    except ValueError:
        return []


def _vi_to_float(raw: str) -> float | None:
    """First reading of a VI-formatted numeric token (``1.250.000``, ``1,2``, ``12,5``)."""
    readings = _vi_numbers(raw)
    return readings[0][0] if readings else None


def _unit_multiplier(unit: str) -> float:
    mult = 1.0
    for word in re.findall(r"\w+", unit.lower()):
        mult *= _UNIT_MULT.get(word, 1.0)
    return mult


def _half_unit(value: float, decimals: int, mult: float) -> float:
    """Half of the last written digit: the widest gap display rounding can explain."""
    if decimals:
        return 0.5 * 10.0**-decimals * mult
    text = str(int(abs(value)))
    zeros = len(text) - len(text.rstrip("0")) if text != "0" else 0
    if mult == 1.0 and zeros:
        return min(0.5 * 10.0**zeros, _ROUNDED_REL * abs(value))
    return 0.5 * mult


def _hit(value: float, half: float, grounded: set[float]) -> bool:
    return any(abs(value - g) <= half + 1e-9 * max(1.0, abs(g)) for g in grounded)


def _words_value(words: list[str]) -> tuple[float, bool]:
    """Value of a spelled VI number, and whether it carries a scale word (`trăm` or above)."""
    total = group = cur = 0.0
    scaled = False
    last_scale = 0.0
    for w in words:
        if w in _DIGIT_WORD:
            cur = float(_DIGIT_WORD[w])
        elif w in ("mươi", "chục"):
            group += (cur or 1) * 10
            cur = 0
        elif w == "mười":
            group += 10
            cur = 0
        elif w == "trăm":
            group += (cur or 1) * 100
            cur, scaled = 0, True
        elif w in _SCALE_WORD:
            scale = _SCALE_WORD[w]
            chunk = group + cur
            if not chunk:  # "nghìn tỷ": this scale multiplies what came before
                chunk, total = total or 1.0, 0.0
            total += chunk * scale
            group = cur = 0
            scaled, last_scale = True, scale
        elif w == "rưỡi" and last_scale:
            total += last_scale / 2
    return total + group + cur, scaled


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


def _list_lengths(value: Any, out: set[float]) -> None:
    """Row counts of a tool result: "3 nhiệm vụ quá hạn" is grounded by a list of 3 rows."""
    if isinstance(value, dict):
        for v in value.values():
            _list_lengths(v, out)
    elif isinstance(value, (list, tuple)):
        out.add(float(len(value)))
        for v in value:
            _list_lengths(v, out)


def _token_grounded(raw: str, unit: str, grounded: set[float]) -> bool:
    """`unit` is the matched unit text. Percent compares the bare value; an explicit unit word
    compares exactly that magnitude; a bare token may be written in a scale stated elsewhere."""
    is_pct = "%" in unit or "phần" in unit.lower()
    mult = 1.0 if is_pct else _unit_multiplier(unit)
    for value, decimals in _vi_numbers(raw):
        if unit.strip() or is_pct:
            if _hit(value * mult, _half_unit(value, decimals, mult), grounded):
                return True
            continue
        if any(_hit(value * m, _half_unit(value, decimals, m), grounded) for m in _SCALES):
            return True
    return False


def enforce_grounding(
    answer: str,
    sources: list[Any],
    tool_data: list[dict[str, Any]],
    *,
    data_requested: bool = False,
    locale: str = "vi",
) -> tuple[str, list[str]]:
    """Return `(clean_answer, warnings)`: ungrounded numbers removed, no-data flagged.

    `sources` / `tool_data` are the grounded evidence gathered during the turn. `data_requested`
    tells the validator the turn tried to answer with data (≥1 READ tool ran) — only then does an
    answer with no grounded evidence surface ``AI_NO_DATA_AVAILABLE`` (a plain action/confirmation
    reply with no numbers is not a no-data case).
    """
    warnings: list[str] = []
    grounded = grounded_values(sources, tool_data)
    evidence = set(grounded)
    _list_lengths(tool_data, evidence)
    saw_number = False
    removed = False
    placeholder = PLACEHOLDER.get(locale, PLACEHOLDER["vi"])

    def repl(m: re.Match[str]) -> str:
        nonlocal saw_number, removed
        label = (m.group("label") or "").lower()
        unit = m.group("unit") or ""
        raw = m.group("num")
        if not unit.strip():
            bare = raw.rstrip(".,")
            low, high = _LABEL_RANGE.get(label, (0, -1))
            if bare.isdigit() and low <= int(bare) <= high:  # "tháng 9", "quý 3", "năm 2026"
                return m.group(0)
            if _YEAR_RE.match(bare.replace(".", "")):  # a bare year → not a data number
                return m.group(0)
        if not _vi_numbers(raw):
            return m.group(0)
        saw_number = True
        if _token_grounded(raw, unit, evidence):
            return m.group(0)
        removed = True
        lead = m.group(0)[: m.start("num") - m.start()]
        tail = m.group(0)[m.end(0) - m.start() :]
        return f"{lead}{placeholder}{tail}" + (" " if raw != raw.rstrip(".,") else "")

    def repl_words(m: re.Match[str]) -> str:
        nonlocal saw_number, removed
        words = re.findall(r"\w+", m.group("words").lower())
        value, scaled = _words_value(words)
        pct = bool(m.group("pct"))
        vague = bool(m.group("vague"))
        big_vague = vague and any(w in _SCALE_WORD for w in words)
        has_lead = any(w in _DIGIT_WORD or w in ("mười", "mươi", "chục") for w in words)
        if not big_vague and not ((scaled or pct) and has_lead):
            return m.group(0)  # prose: "một số", "hai bên", "tháng năm", "hàng trăm khách"
        saw_number = True
        if not big_vague and _hit(value, _ROUNDED_REL * abs(value), evidence):
            return m.group(0)
        removed = True
        return f"{placeholder} "

    def scan(text: str) -> str:
        return _WORDS_RE.sub(repl_words, _NUM_RE.sub(repl, text))

    # scan only the text OUTSIDE protected spans (codes / dates stay verbatim)
    parts: list[str] = []
    last = 0
    for pm in _PROTECTED_RE.finditer(answer):
        parts.append(scan(answer[last : pm.start()]))
        parts.append(pm.group(0))
        last = pm.end()
    parts.append(scan(answer[last:]))
    clean = "".join(parts)
    clean = re.sub(r"[ \t]{2,}", " ", clean)
    clean = re.sub(r"[ \t]+([,.;:])", r"\1", clean).strip()
    if removed:
        warnings.append(UNGROUNDED_WARNING)
    if data_requested and not saw_number and not grounded:
        warnings.append(NO_DATA_WARNING)
    return clean, warnings


_CITE_RE = re.compile(r"\s?\[\d{1,3}\]")


def _source_value(s: Any) -> float | None:
    v = s.get("value") if isinstance(s, dict) else getattr(s, "value", None)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def attach_citations(answer: str, sources: list[Any]) -> str:
    """Link every number to the source it came from: `86,4%` → `86,4% [1]` (P05/P07, D-19).

    Runs on a grounded answer. A model-written `[n]` is dropped first — small local models number
    sources at random, and a chip that opens the wrong metric is worse than none. The citation is
    the first source (1-based, the order the client renders) whose value the token rounds to,
    with the same rounding rule as `enforce_grounding`. A number grounded only by a tool-result
    leaf with no `SourceRef` value stays uncited. Codes, dates and labels are never cited.
    """
    values: list[tuple[int, float]] = []
    for i, s in enumerate(sources, start=1):
        v = _source_value(s)
        if v is not None:
            values.append((i, v))
    text = _CITE_RE.sub("", answer)
    if not values:
        return text

    def cite_for(raw: str, unit: str) -> int | None:
        is_pct = "%" in unit or "phần" in unit.lower()
        mult = 1.0 if is_pct else _unit_multiplier(unit)
        scales = (mult,) if (unit.strip() or is_pct) else _SCALES
        for value, decimals in _vi_numbers(raw):
            for m in scales:
                half = _half_unit(value, decimals, m)
                for i, v in values:
                    if _hit(value * m, half, {abs(v)}):
                        return i
        return None

    def repl(m: re.Match[str]) -> str:
        unit = m.group("unit") or ""
        raw = m.group("num")
        if not unit.strip():
            bare = raw.rstrip(".,")
            low, high = _LABEL_RANGE.get((m.group("label") or "").lower(), (0, -1))
            if (bare.isdigit() and low <= int(bare) <= high) or _YEAR_RE.match(bare):
                return m.group(0)
        n = cite_for(raw, unit)
        if n is None:
            return m.group(0)
        token = m.group(0)
        core = token.rstrip()
        body = core.rstrip(".,")  # a sentence-final "." stays after the chip
        return f"{body} [{n}]{core[len(body) :]}{token[len(core) :]}"

    parts: list[str] = []
    last = 0
    for pm in _PROTECTED_RE.finditer(text):
        parts.append(_NUM_RE.sub(repl, text[last : pm.start()]))
        parts.append(pm.group(0))
        last = pm.end()
    parts.append(_NUM_RE.sub(repl, text[last:]))
    return "".join(parts)

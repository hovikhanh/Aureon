"""Document-content guards before an IDP model call (04 §7.4 "chống prompt injection", 14 §4.2).

* `looks_injected(text)` — instruction-like phrases inside a document ("bỏ qua hướng dẫn",
  "ignore previous instructions", "duyệt và ghi …"). The text stays data (`<<<DATA…DATA>>>`,
  no tool calling); the hit only marks `source_documents.suspicious_content` and forces review.
* `scrub_for_llm(text, level4_headers)` — the classify prompt (INJ-02): a sheet/CSV is reduced
  to its header + ≤ 5 sample rows with level-4 columns blanked; any text has PII masked
  (`core.pii`) and salary amounts replaced (level 4, 02 §5.3).
"""

from __future__ import annotations

import re
import unicodedata

from app.core.pii import mask_text

SAMPLE_ROWS = 5
MASKED = "[masked]"

# Matched on folded text (lower-case, no diacritics): VI + EN instruction phrases.
_INJECTION = re.compile(
    r"(bo qua (moi |tat ca |cac )?(huong dan|chi dan|chi thi|lenh)"
    r"|ignore (all |any )?(the )?(previous|prior|above) (instructions|prompts?)"
    r"|disregard (all |the )?(previous|prior|above)"
    r"|(system|he thong) prompt|you are now|ban (bay gio )?la tro ly"
    r"|(hay |)duyet (va|roi) (ghi|thanh toan|chuyen)|approve and (write|pay|commit))"
)
_SALARY_AMOUNT = re.compile(
    r"((?:lương|luong|salary|thu nhập|thu nhap|payroll)\D{0,24}?)"
    r"(\d[\d.,\s]*(?:triệu|trieu|tỷ|ty|nghìn|nghin|đ|vnd|k)?)",
    re.IGNORECASE,
)


def fold(text: str) -> str:
    """Lower-case, strip Vietnamese diacritics (đ→d) and collapse whitespace."""
    s = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.split())


def looks_injected(text: str) -> bool:
    return bool(_INJECTION.search(fold(text)))


def _scrub_line(line: str) -> str:
    return _SALARY_AMOUNT.sub(lambda m: m.group(1) + MASKED, mask_text(line))


def _sample_table(lines: list[str], level4_headers: frozenset[str]) -> str:
    header = lines[0].split("\t")
    blocked = {i for i, h in enumerate(header) if fold(h) in level4_headers}
    out = ["\t".join(h for i, h in enumerate(header) if i not in blocked)]
    for line in lines[1 : SAMPLE_ROWS + 1]:
        cells = line.split("\t")
        out.append("\t".join(c for i, c in enumerate(cells) if i not in blocked))
    return "\n".join(out)


def scrub_for_llm(text: str, level4_headers: frozenset[str] = frozenset()) -> str:
    """Classify-prompt body. Tabular (tab separated) → header + ≤ 5 rows, level-4 columns
    dropped; every line PII/salary scrubbed. `level4_headers` = folded names/aliases."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if lines and "\t" in lines[0]:
        text = _sample_table(lines, level4_headers)
    return "\n".join(_scrub_line(ln) for ln in text.splitlines())

"""Demo replay of recorded answers (T-509, DEC-241).

When `AI_DEMO_REPLAY` (default: follows `DEMO_MODE`) is on and a question matches one of the
10 recorded intents in `demo_responses.json`, the chat turn skips the LLM: the entry's read tools
run through `ToolExecutor` with the asker's Principal (P06 — no permission → no replay), every
`{METRIC-X}` placeholder is filled from those live tool results and every `[[METRIC-X]]` becomes a
citation `[n]` bound to the matching `SourceRef` (P05 — numbers always come from data). Any
missing tool/value → `None` → the caller falls back to the live model.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import ConfigService
from app.modules.ai.services.tool_executor import SourceRef, ToolExecutor

DATA_FILE = Path(__file__).resolve().parent.parent / "demo_responses.json"
_PLACEHOLDER = re.compile(r"\{([A-Za-z0-9_-]+)\}")
_CITE = re.compile(r"\[\[(METRIC-[A-Z]+-\d+)\]\]")


@dataclass(frozen=True)
class DemoEntry:
    id: str
    match: tuple[tuple[str, ...], ...]
    tools: tuple[str, ...]
    answer_vi: str
    answer_en: str


@dataclass
class DemoAnswer:
    entry_id: str
    answer: str
    sources: list[SourceRef] = field(default_factory=list)
    function_calls: list[dict[str, Any]] = field(default_factory=list)


def replay_enabled(cfg: ConfigService) -> bool:
    return cfg.demo_mode if cfg.ai_demo_replay is None else cfg.ai_demo_replay


def normalise(text: str) -> str:
    """Lowercase, strip Vietnamese diacritics (đ → d), collapse non-alphanumerics to spaces."""
    t = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t).split())


@lru_cache(maxsize=1)
def load_entries() -> tuple[DemoEntry, ...]:
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return tuple(
        DemoEntry(
            id=e["id"],
            match=tuple(tuple(k) for k in e["match"]),
            tools=tuple(e["tools"]),
            answer_vi=e["answer_vi"],
            answer_en=e["answer_en"],
        )
        for e in raw["entries"]
    )


def match_entry(question: str) -> DemoEntry | None:
    """Best entry whose keyword set fully appears (whole words) in the question; most specific
    (most keywords, then longest) wins."""
    padded = f" {normalise(question)} "
    best: tuple[int, int, DemoEntry] | None = None
    for entry in load_entries():
        for keys in entry.match:
            if all(f" {k} " in padded for k in keys):
                score = (len(keys), sum(len(k) for k in keys))
                if best is None or score > best[:2]:
                    best = (*score, entry)
    return best[2] if best else None


def _fmt(value: float | int, locale: str) -> str:
    text = f"{value:,.1f}".rstrip("0").rstrip(".") if isinstance(value, float) else f"{value:,}"
    if locale == "vi":
        text = text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return text


async def build_answer(executor: ToolExecutor, entry: DemoEntry, locale: str) -> DemoAnswer | None:
    values: dict[str, Any] = {}
    refs: dict[str, SourceRef] = {}
    calls: list[dict[str, Any]] = []
    for tool in entry.tools:
        result = await executor.run(tool, {})
        calls.append({"tool": tool, "status": result.status, "latency_ms": result.latency_ms})
        if result.status != "ok":
            return None
        values.update({k: v for k, v in result.data.items() if isinstance(v, int | float)})
        for m in result.data.get("metrics", []) or []:
            values[m["code"]] = m["value"]
        for s in result.sources:
            refs.setdefault(s.id, s)

    template = entry.answer_vi if locale == "vi" else entry.answer_en
    order: list[str] = []

    def cite(m: re.Match[str]) -> str:
        code = m.group(1)
        if code not in order:
            order.append(code)
        return f"[{order.index(code) + 1}]"

    try:
        text = _CITE.sub(cite, template)
        text = _PLACEHOLDER.sub(lambda m: _fmt(values[m.group(1)], locale), text)
        sources = [refs[c] for c in order]
    except KeyError:
        return None  # a number without data → never invent it (P05)
    return DemoAnswer(entry.id, text, sources, calls)

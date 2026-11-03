"""Mask secrets in every log record (CLAUDE.md §6.4, R-DEC-167).

Installed once per process (API, Celery worker/beat, seed): it wraps the stdlib log-record factory,
so it covers every logger and handler uvicorn / Celery configure — a handler filter would miss
handlers added later. The message is rendered, masked and frozen; a traceback is rendered once,
masked, and stored in `exc_text` (the formatter then reuses it instead of formatting the raw one).

Masked: PEM private keys, pydantic `input_value={…}` dumps, `name=value` / `'name': 'value'` pairs
whose name looks secret (KEY / SECRET / PASSWORD / TOKEN / DSN), and credentials inside URLs.
"""

from __future__ import annotations

import logging
import re
import traceback
from typing import Any

MASK = "<redacted>"
_NAME = (
    r"[A-Za-z0-9_]*(?:password|passwd|secret|token(?!s)|api_key|apikey|private_key|_key|dsn)"
    r"[A-Za-z0-9_]*"
)
_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)",
                re.S), f"{MASK} PEM"),
    (re.compile(r"input_value=\{[^\n]*"), f"input_value={MASK}"),
    (re.compile(rf"(['\"]?)({_NAME})\1(\s*[:=]\s*)(['\"])(?:\\.|(?!\4).)*\4", re.I),
     rf"\1\2\1\3\4{MASK}\4"),
    (re.compile(rf"\b({_NAME})=[^\s,;'\"]+", re.I), rf"\1={MASK}"),
    (re.compile(r"(\b[a-z][a-z0-9+.-]*://)[^/\s:@'\"]+:[^@\s'\"]+@"), rf"\1{MASK}@"),
)  # fmt: skip


def redact(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


def install() -> None:
    """Idempotent: wrap the current record factory once."""
    previous = logging.getLogRecordFactory()
    if getattr(previous, "_aureon_redacting", False):
        return

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = previous(*args, **kwargs)
        try:
            message = record.getMessage()
        except Exception:  # a bad %-format must not break logging
            return record
        record.msg, record.args = redact(message), None
        if record.exc_info and not record.exc_text:
            rendered = "".join(traceback.format_exception(*record.exc_info)).rstrip("\n")
            record.exc_text = redact(rendered)
        return record

    factory._aureon_redacting = True  # type: ignore[attr-defined]
    logging.setLogRecordFactory(factory)

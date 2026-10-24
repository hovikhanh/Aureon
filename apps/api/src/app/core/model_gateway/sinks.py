"""Call-log sink registry — lets a module build a `ModelGateway` bound to its session without
importing `ai` (R-DEC-60: `idp → ai` edge removed so `ai → idp` (Action Registry v2) is acyclic).

`ai` registers its `ModelCallLogWriter` factory at import time; `core` holds only the registry
(it imports no module). No factory registered → fail closed (RuntimeError), never a silent
`NullSink` that would drop `ai.model_call_logs` rows.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.model_gateway.gateway import CallLogSink

SinkFactory = Callable[[Any], CallLogSink]

_FACTORY: list[SinkFactory] = []


def register_call_log_sink(factory: SinkFactory) -> None:
    _FACTORY[:] = [factory]


def session_sink(db: Any) -> CallLogSink:
    """The registered `ai.model_call_logs` writer bound to `db` (caller's transaction)."""
    if not _FACTORY:
        raise RuntimeError("no model call-log sink registered (ai module not loaded)")
    return _FACTORY[0](db)

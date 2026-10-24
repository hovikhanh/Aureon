"""Module `ai` (schema `ai`).

Registers the `ai.model_call_logs` writer in `core/model_gateway/sinks.py` so `idp` builds its
pipeline gateway without importing `ai` (R-DEC-60, T-636).
"""

from app.core.model_gateway.sinks import register_call_log_sink
from app.modules.ai.services.ai_service import ModelCallLogWriter

register_call_log_sink(ModelCallLogWriter)

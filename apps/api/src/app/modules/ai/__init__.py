"""Module `ai` (schema `ai`).

Registers the `ai.model_call_logs` writer in `core/model_gateway/sinks.py` so `idp` builds its
pipeline gateway without importing `ai` (R-DEC-60, T-636), and the executive AI-activity feed
in `core/ai_activity.py` so `dashboard` reporting reads recent AI actions without importing `ai`
(M2.1, DEC-125). Importing `action_service` also installs its approval hook.
"""

from app.core.model_gateway.sinks import register_call_log_sink
from app.modules.ai.services import action_service as _action_service  # noqa: F401 (side-effect)
from app.modules.ai.services.ai_service import ModelCallLogWriter

register_call_log_sink(ModelCallLogWriter)

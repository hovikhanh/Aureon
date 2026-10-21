"""ModelGateway (07 §6) — every LLM call goes through here (CLAUDE.md §5.5).

Embedding (`embed`) is not wired: Knowledge RAG is deferred to v2.1 (DEC-150).
"""

from app.core.model_gateway.errors import (
    FixtureMissingError,
    ProviderCallError,
    SecretDataBlockedError,
    TemplateRequired,
)
from app.core.model_gateway.gateway import CallLogSink, CallRecord, ModelGateway, NullSink
from app.core.model_gateway.types import (
    ChatChunk,
    ChatRequest,
    ChatResponse,
    Message,
    ToolCall,
    ToolSpec,
    Usage,
)

__all__ = [
    "CallLogSink", "CallRecord", "ChatChunk", "ChatRequest", "ChatResponse", "FixtureMissingError",
    "Message", "ModelGateway", "NullSink", "ProviderCallError", "SecretDataBlockedError",
    "TemplateRequired", "ToolCall", "ToolSpec", "Usage",
]  # fmt: skip

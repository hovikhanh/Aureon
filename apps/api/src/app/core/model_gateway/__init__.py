"""ModelGateway (07 §6) — every LLM call goes through here (CLAUDE.md §5.5).

Embedding (`embed`) wiring (M3.4, R-DEC-141): fixture mode returns a deterministic hash vector
(`hash_embedding`); the real provider stays deferred (DEC-150). RAG is gated off when
`embedding_model` is empty, in which case Knowledge search falls back to keyword matching.
"""

from app.core.model_gateway.errors import (
    FixtureMissingError,
    ProviderCallError,
    SecretDataBlockedError,
    TemplateRequired,
)
from app.core.model_gateway.gateway import (
    CallLogSink,
    CallRecord,
    ModelGateway,
    NullSink,
    hash_embedding,
)
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
    "TemplateRequired", "ToolCall", "ToolSpec", "Usage", "hash_embedding",
]  # fmt: skip

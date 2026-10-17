"""ModelGateway package — the only module allowed to call an LLM (07 §5.2, T-006).

Usage (T-205 mapping / T-207 classify+extract)::

    from app.core.model_gateway import build_document_messages, get_model_gateway

    gw = get_model_gateway()
    msgs = build_document_messages("Classify this document ...", page_text)
    result = gw.complete_structured("classify", msgs, ClassifyResult, fixture_key=f"{sha}.classify")
"""

from app.core.model_gateway.errors import (
    IDP_E06,
    IDP_E07,
    FixtureNotFoundError,
    ModelGatewayError,
    ModelOutputError,
)
from app.core.model_gateway.fixtures import FixtureRecord, FixtureStore, fixture_hash
from app.core.model_gateway.gateway import (
    DEFAULT_BACKOFF_S,
    DEFAULT_FIXTURE_DIR,
    ModelGateway,
    get_model_gateway,
    parse_json_content,
    reset_model_gateway,
)
from app.core.model_gateway.prompting import (
    DOCUMENT_DATA_POLICY,
    build_document_messages,
    json_schema_instruction,
    wrap_document,
)
from app.core.model_gateway.types import (
    CallRecord,
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    TaskType,
    TokenUsage,
)

__all__ = [
    "DEFAULT_BACKOFF_S",
    "DEFAULT_FIXTURE_DIR",
    "DOCUMENT_DATA_POLICY",
    "IDP_E06",
    "IDP_E07",
    "CallRecord",
    "ChatMessage",
    "CompletionRequest",
    "CompletionResponse",
    "FixtureNotFoundError",
    "FixtureRecord",
    "FixtureStore",
    "ModelGateway",
    "ModelGatewayError",
    "ModelOutputError",
    "TaskType",
    "TokenUsage",
    "build_document_messages",
    "fixture_hash",
    "get_model_gateway",
    "json_schema_instruction",
    "parse_json_content",
    "reset_model_gateway",
    "wrap_document",
]

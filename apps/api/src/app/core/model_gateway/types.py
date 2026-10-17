"""Typed request/response models for ModelGateway (07 §5.2, Pydantic v2)."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# 07 §5.2 "Routing": model chosen by task_type. `stt` is not a chat completion and is not
# served by this client yet (proposed DEC, see module docstring of gateway.py).
TaskType = Literal["classify", "extract", "mapping", "assistant"]
Role = Literal["system", "user", "assistant"]
GatewayMode = Literal["live", "fixture"]


class ChatMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Role
    content: str


class CompletionRequest(BaseModel):
    """One logical LLM call. `fixture_key` lets callers key replays by document SHA-256 (07 §9)."""

    model_config = ConfigDict(frozen=True)

    task_type: TaskType
    messages: tuple[ChatMessage, ...] = Field(min_length=1)
    json_mode: bool = False
    max_tokens: int | None = Field(default=None, gt=0)
    temperature: float | None = Field(default=0.0, ge=0.0, le=2.0)
    timeout_s: float | None = Field(default=None, gt=0)
    fixture_key: str | None = None


class TokenUsage(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class CompletionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_type: TaskType
    content: str
    model: str  # model that actually answered (as reported by OmniRoute, or "fixture")
    route: str  # configured model name we requested
    mode: GatewayMode
    attempts: int  # HTTP attempts used for this logical call (0 in fixture mode)
    used_fallback: bool = False
    usage: TokenUsage = TokenUsage()
    latency_ms: int = 0
    data: Any = None  # parsed JSON when json_mode=True


class CallRecord(BaseModel):
    """Metadata of one HTTP attempt / fixture replay — safe to log (no content, no key)."""

    model_config = ConfigDict(frozen=True)

    task_type: TaskType
    mode: GatewayMode
    model: str
    attempt: int
    outcome: Literal["ok", "retryable_error", "fatal_error", "fixture_hit", "fixture_miss"]
    status_code: int | None = None
    error: str | None = None
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

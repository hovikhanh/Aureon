"""ModelGateway DTOs (07 §6). Provider-neutral; adapters map to/from wire formats."""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

TaskKind = Literal["chat", "classify", "extract", "mapping", "insight", "stt", "embed"]
Classification = Literal["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]
Role = Literal["system", "user", "assistant", "tool"]
CLASSIFICATION_RANK: dict[str, int] = {"PUBLIC": 0, "INTERNAL": 1, "CONFIDENTIAL": 2, "SECRET": 3}


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None  # role == "tool"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


@dataclass(frozen=True)
class ChatRequest:
    task: TaskKind
    messages: tuple[Message, ...]
    caller_module: str
    classification: Classification = "INTERNAL"
    tools: tuple[ToolSpec, ...] = ()
    json_schema: dict[str, Any] | None = None  # extract/classify: structured output
    max_output_tokens: int | None = None
    temperature: float | None = None
    user_id: uuid.UUID | None = None
    message_id: uuid.UUID | None = None
    source_document_id: uuid.UUID | None = None
    schema_version: str = "1"

    def prompt_sha256(self) -> str:
        """Hash of the normalized input (fixture key + `ModelCallLog.prompt_sha256`)."""
        body = {
            "task": self.task,
            "schema_version": self.schema_version,
            "messages": [
                [m.role, " ".join(m.content.split()), m.tool_call_id,
                 [[c.name, c.arguments] for c in m.tool_calls]]
                for m in self.messages
            ],
            "tools": sorted(t.name for t in self.tools),
            "json_schema": self.json_schema,
        }  # fmt: skip
        raw = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class Usage:
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass(frozen=True)
class ChatResponse:
    content: str
    provider: str
    model: str
    usage: Usage = field(default_factory=Usage)
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str = "stop"
    fallback_from: str | None = None
    data: Any = None  # parsed JSON when `json_schema` was requested


@dataclass(frozen=True)
class ChatChunk:
    delta: str = ""
    done: bool = False
    usage: Usage | None = None
    provider: str = ""
    model: str = ""

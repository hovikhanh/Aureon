"""Fixture provider (07 §6.1, §6.4): recorded responses keyed by `prompt_sha256`.

Layout: `<dir>/<task>/<sha256>.json` = `{"content", "tool_calls"?, "data"?, "usage"?, "model"?}`.
Fixture mode never opens a network connection; a missing file is a loud
`FixtureMissingError` (not a silent default). `record` mode writes masked responses.
"""

import json
from pathlib import Path
from typing import Any

from app.core.model_gateway.errors import FixtureMissingError
from app.core.model_gateway.types import ChatRequest, ChatResponse, ToolCall, Usage
from app.core.pii import mask_payload

DEFAULT_DIR = Path(__file__).resolve().parent / "fixtures"


class FixtureStore:
    name = "fixture"

    def __init__(self, root: Path = DEFAULT_DIR) -> None:
        self.root = root

    def path(self, req: ChatRequest) -> Path:
        return self.root / req.task / f"{req.prompt_sha256()}.json"

    def load(self, req: ChatRequest) -> ChatResponse:
        p = self.path(req)
        if not p.is_file():
            raise FixtureMissingError(
                f"no fixture for task={req.task} key={req.prompt_sha256()} "
                f"(expected {p.name} under {req.task}/); record with MODEL_GATEWAY_MODE=record"
            )
        raw: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        usage = raw.get("usage") or {}
        return ChatResponse(
            content=raw.get("content", ""),
            provider="fixture",
            model=raw.get("model", "fixture"),
            usage=Usage(int(usage.get("tokens_in", 0)), int(usage.get("tokens_out", 0))),
            tool_calls=tuple(ToolCall(**c) for c in raw.get("tool_calls") or ()),
            data=raw.get("data"),
        )

    def save(self, req: ChatRequest, resp: ChatResponse) -> Path:
        p = self.path(req)
        p.parent.mkdir(parents=True, exist_ok=True)
        body = {
            "content": resp.content,
            "model": resp.model,
            "usage": {"tokens_in": resp.usage.tokens_in, "tokens_out": resp.usage.tokens_out},
            "tool_calls": [
                {"id": c.id, "name": c.name, "arguments": c.arguments} for c in resp.tool_calls
            ],
            "data": resp.data,
        }
        p.write_text(
            json.dumps(mask_payload(body), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return p

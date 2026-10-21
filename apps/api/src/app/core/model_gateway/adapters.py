"""Provider adapters over `httpx` — no vendor SDK (07 §6.1, A10, DEC-140).

`OpenAICompatAdapter`: omniroute, openrouter, ninerouter, deepseek, openai, ollama
(`POST {base}/chat/completions`). `AnthropicAdapter`: `POST {base}/v1/messages`, mapping
tools ↔ `tool_use` / `tool_result`. Errors become `ProviderCallError` (status only — the
response body is never logged or raised, it may echo the prompt).
"""

import json
from collections.abc import AsyncIterator
from typing import Any, Protocol

import httpx

from app.core.model_gateway.errors import ProviderCallError
from app.core.model_gateway.types import (
    ChatChunk,
    ChatRequest,
    ChatResponse,
    Message,
    ToolCall,
    Usage,
)

CONNECT_TIMEOUT = 5.0


class Adapter(Protocol):
    name: str

    async def chat(self, req: ChatRequest, *, model: str, timeout_s: float) -> ChatResponse: ...

    def stream(
        self, req: ChatRequest, *, model: str, timeout_s: float
    ) -> AsyncIterator[ChatChunk]: ...


def _retryable(status: int) -> bool:
    return status == 429 or status >= 500


async def _post(
    client: httpx.AsyncClient,
    provider: str,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    try:
        r = await client.post(url, json=body, headers=headers)
    except httpx.TimeoutException as exc:
        raise ProviderCallError(provider, retryable=True, status=None, timeout=True) from exc
    except httpx.TransportError as exc:
        raise ProviderCallError(provider, retryable=True, status=None, timeout=False) from exc
    if r.status_code >= 400:
        raise ProviderCallError(
            provider, retryable=_retryable(r.status_code), status=r.status_code, timeout=False
        )
    data: dict[str, Any] = r.json()
    return data


def _timeout(total: float) -> httpx.Timeout:
    return httpx.Timeout(total, connect=CONNECT_TIMEOUT)


class OpenAICompatAdapter:
    def __init__(
        self, name: str, base_url: str, api_key: str | None, *, temperature: float, max_tokens: int
    ) -> None:
        self.name, self.base_url, self._key = name, base_url.rstrip("/"), api_key
        self.temperature, self.max_tokens = temperature, max_tokens

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}"} if self._key else {}

    @staticmethod
    def _message(m: Message) -> dict[str, Any]:
        out: dict[str, Any] = {"role": m.role, "content": m.content}
        if m.tool_calls:
            out["tool_calls"] = [
                {"id": c.id, "type": "function",
                 "function": {"name": c.name, "arguments": json.dumps(c.arguments)}}
                for c in m.tool_calls
            ]  # fmt: skip
        if m.tool_call_id:
            out["tool_call_id"] = m.tool_call_id
        return out

    def _body(self, req: ChatRequest, model: str, *, stream: bool) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": [self._message(m) for m in req.messages],
            "temperature": self.temperature if req.temperature is None else req.temperature,
            "max_tokens": req.max_output_tokens or self.max_tokens,
            "stream": stream,
        }
        if req.tools:
            body["tools"] = [
                {"type": "function",
                 "function": {"name": t.name, "description": t.description,
                              "parameters": t.parameters}}
                for t in req.tools
            ]  # fmt: skip
        if req.json_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": req.task, "schema": req.json_schema, "strict": True},
            }
        return body

    async def chat(self, req: ChatRequest, *, model: str, timeout_s: float) -> ChatResponse:
        async with httpx.AsyncClient(timeout=_timeout(timeout_s)) as client:
            data = await _post(
                client, self.name, f"{self.base_url}/chat/completions",
                self._body(req, model, stream=False), self._headers(),
            )  # fmt: skip
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        calls = tuple(
            ToolCall(
                id=c.get("id", ""),
                name=c["function"]["name"],
                arguments=json.loads(c["function"].get("arguments") or "{}"),
            )
            for c in msg.get("tool_calls") or ()
        )
        usage = data.get("usage") or {}
        return ChatResponse(
            content=msg.get("content") or "",
            provider=self.name,
            model=data.get("model") or model,
            usage=Usage(int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))),
            tool_calls=calls,
            finish_reason=choice.get("finish_reason") or "stop",
        )

    async def stream(
        self, req: ChatRequest, *, model: str, timeout_s: float
    ) -> AsyncIterator[ChatChunk]:
        body = self._body(req, model, stream=True)
        body["stream_options"] = {"include_usage": True}
        async with (
            httpx.AsyncClient(timeout=_timeout(timeout_s)) as client,
            client.stream(
                "POST", f"{self.base_url}/chat/completions", json=body, headers=self._headers()
            ) as r,
        ):
            if r.status_code >= 400:
                raise ProviderCallError(
                    self.name, retryable=_retryable(r.status_code), status=r.status_code,
                    timeout=False,
                )  # fmt: skip
            usage: Usage | None = None
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                event = json.loads(payload)
                if event.get("usage"):
                    u = event["usage"]
                    usage = Usage(
                        int(u.get("prompt_tokens", 0)), int(u.get("completion_tokens", 0))
                    )
                for ch in event.get("choices") or ():
                    delta = (ch.get("delta") or {}).get("content")
                    if delta:
                        yield ChatChunk(delta=delta, provider=self.name, model=model)
            yield ChatChunk(done=True, usage=usage, provider=self.name, model=model)


class AnthropicAdapter:
    VERSION = "2023-06-01"

    def __init__(self, base_url: str, api_key: str | None, *, temperature: float, max_tokens: int):
        self.name, self.base_url, self._key = "anthropic", base_url.rstrip("/"), api_key
        self.temperature, self.max_tokens = temperature, max_tokens

    @staticmethod
    def _messages(req: ChatRequest) -> tuple[str, list[dict[str, Any]]]:
        system = "\n\n".join(m.content for m in req.messages if m.role == "system")
        out: list[dict[str, Any]] = []
        for m in req.messages:
            if m.role == "system":
                continue
            if m.role == "tool":
                block = {"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content}
                out.append({"role": "user", "content": [block]})
            elif m.tool_calls:
                blocks: list[dict[str, Any]] = (
                    [{"type": "text", "text": m.content}] if m.content else []
                )
                blocks += [
                    {"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments}
                    for c in m.tool_calls
                ]
                out.append({"role": "assistant", "content": blocks})
            else:
                out.append({"role": m.role, "content": m.content})
        return system, out

    async def chat(self, req: ChatRequest, *, model: str, timeout_s: float) -> ChatResponse:
        system, messages = self._messages(req)
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": req.max_output_tokens or self.max_tokens,
            "temperature": self.temperature if req.temperature is None else req.temperature,
        }
        if system:
            body["system"] = system
        if req.tools:
            body["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.parameters}
                for t in req.tools
            ]
        headers = {"x-api-key": self._key or "", "anthropic-version": self.VERSION}
        async with httpx.AsyncClient(timeout=_timeout(timeout_s)) as client:
            data = await _post(client, self.name, f"{self.base_url}/v1/messages", body, headers)
        blocks = data.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        calls = tuple(
            ToolCall(id=b["id"], name=b["name"], arguments=b.get("input") or {})
            for b in blocks
            if b.get("type") == "tool_use"
        )
        usage = data.get("usage") or {}
        return ChatResponse(
            content=text,
            provider=self.name,
            model=data.get("model") or model,
            usage=Usage(int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))),
            tool_calls=calls,
            finish_reason=data.get("stop_reason") or "stop",
        )

    async def stream(
        self, req: ChatRequest, *, model: str, timeout_s: float
    ) -> AsyncIterator[ChatChunk]:
        """Non-incremental fallback for Anthropic (SSE event mapping comes with T-3xx chat)."""
        resp = await self.chat(req, model=model, timeout_s=timeout_s)
        if resp.content:
            yield ChatChunk(delta=resp.content, provider=self.name, model=resp.model)
        yield ChatChunk(done=True, usage=resp.usage, provider=self.name, model=resp.model)

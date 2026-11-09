"""Provider adapters over `httpx` — no vendor SDK (07 §6.1, A10, DEC-140).

`OpenAICompatAdapter`: omniroute, openrouter, ninerouter, deepseek, openai, ollama
(`POST {base}/chat/completions`). `AnthropicAdapter`: `POST {base}/v1/messages`, mapping
tools ↔ `tool_use` / `tool_result`. Errors become `ProviderCallError` (status only — the
response body is never logged or raised, it may echo the prompt).
"""

import asyncio
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


def openai_usage(u: dict[str, Any]) -> Usage:
    """OpenAI-compatible usage (OmniRoute, OpenRouter, DeepSeek…): `prompt_tokens` already counts
    cached tokens; the cache split is in `prompt_tokens_details.cached_tokens` (and, when the
    upstream is Anthropic, `cache_creation_input_tokens` passed through).

    OmniRoute's `cc/` (Claude) route instead reports a cache write as
    `prompt_tokens_details.cache_creation_tokens` with `cache_creation_in_prompt: false` — those
    tokens are NOT in `prompt_tokens` (live 2026-11-03: 7 prompt + 10 787 written), so they are
    added back; otherwise the write would vanish from `tokens_in` and the cost."""
    details = u.get("prompt_tokens_details") or {}
    tin = int(u.get("prompt_tokens") or 0)
    write = int(details.get("cache_creation_tokens") or u.get("cache_creation_input_tokens") or 0)
    if details.get("cache_creation_in_prompt") is False:
        tin += write
    return Usage(
        tin, int(u.get("completion_tokens") or 0),
        cached_in=int(details.get("cached_tokens") or 0), cache_write=write,
    )  # fmt: skip


def anthropic_usage(u: dict[str, Any]) -> Usage:
    """Anthropic Messages usage: `input_tokens` EXCLUDES cache reads/writes — add them back so
    `tokens_in` means "all prompt tokens" for every provider."""
    read = int(u.get("cache_read_input_tokens") or 0)
    write = int(u.get("cache_creation_input_tokens") or 0)
    return Usage(
        int(u.get("input_tokens") or 0) + read + write, int(u.get("output_tokens") or 0),
        cached_in=read, cache_write=write,
    )  # fmt: skip


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


def _tool_args(provider: str, raw: Any) -> dict[str, Any]:
    """Tool arguments of an OpenAI-compatible answer. Local models do produce malformed JSON here:
    that is a failed call (retried, logged), not an unhandled 500."""
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw or "{}")
    except (TypeError, ValueError) as exc:
        raise ProviderCallError(provider, retryable=True, status=None, timeout=False) from exc
    if not isinstance(parsed, dict):
        raise ProviderCallError(provider, retryable=True, status=None, timeout=False)
    return parsed


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
                arguments=_tool_args(self.name, c["function"].get("arguments")),
            )
            for c in msg.get("tool_calls") or ()
        )
        usage = data.get("usage") or {}
        return ChatResponse(
            content=msg.get("content") or "",
            provider=self.name,
            model=data.get("model") or model,
            usage=openai_usage(usage),
            tool_calls=calls,
            finish_reason=choice.get("finish_reason") or "stop",
        )

    async def embed(
        self, texts: list[str], *, model: str, timeout_s: float
    ) -> tuple[list[list[float]], Usage]:
        """`POST {base}/embeddings` (OpenAI-compatible; Ollama serves `bge-m3` here)."""
        async with httpx.AsyncClient(timeout=_timeout(timeout_s)) as client:
            data = await _post(
                client, self.name, f"{self.base_url}/embeddings",
                {"model": model, "input": texts}, self._headers(),
            )  # fmt: skip
        rows = sorted(data.get("data") or [], key=lambda r: int(r.get("index", 0)))
        vectors = [r.get("embedding") or [] for r in rows]
        if len(vectors) != len(texts):
            raise ProviderCallError(self.name, retryable=False, status=None, timeout=False)
        return vectors, openai_usage(data.get("usage") or {})

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
            parts: dict[int, dict[str, str]] = {}  # streamed tool calls arrive in fragments
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                event = json.loads(payload)
                if event.get("usage"):
                    u = event["usage"]
                    usage = openai_usage(u)
                for ch in event.get("choices") or ():
                    d = ch.get("delta") or {}
                    for tc in d.get("tool_calls") or ():
                        acc = parts.setdefault(
                            int(tc.get("index", 0)), {"id": "", "name": "", "args": ""}
                        )
                        fn = tc.get("function") or {}
                        acc["id"] = tc.get("id") or acc["id"]
                        acc["name"] += fn.get("name") or ""
                        acc["args"] += fn.get("arguments") or ""
                    if d.get("content"):
                        yield ChatChunk(delta=d["content"], provider=self.name, model=model)
            calls = tuple(
                ToolCall(id=p["id"], name=p["name"], arguments=_tool_args(self.name, p["args"]))
                for _, p in sorted(parts.items())
            )
            yield ChatChunk(done=True, usage=usage, provider=self.name, model=model,
                            tool_calls=calls)  # fmt: skip


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
            usage=anthropic_usage(usage),
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
        yield ChatChunk(done=True, usage=resp.usage, provider=self.name, model=resp.model,
                        tool_calls=resp.tool_calls)  # fmt: skip


def _ollama_timings(event: dict[str, Any]) -> dict[str, int]:
    """Ollama reports durations in ns; keep ms + the token counts behind them (D-19 evidence)."""
    ms = {k: int((event.get(f"{k}_duration") or 0) / 1e6) for k in ("prompt_eval", "eval", "load")}
    return {**{f"{k}_ms": v for k, v in ms.items()},
            "prompt_tokens": int(event.get("prompt_eval_count") or 0),
            "gen_tokens": int(event.get("eval_count") or 0)}  # fmt: skip


def _ollama_calls(msg: dict[str, Any], offset: int = 0) -> tuple[ToolCall, ...]:
    """Native tool calls carry no id: number them so `tool` replies can be paired."""
    return tuple(
        ToolCall(
            id=str(c.get("id") or f"call_{offset + i + 1}"),
            name=str((c.get("function") or {}).get("name") or ""),
            arguments=_tool_args("ollama", (c.get("function") or {}).get("arguments")),
        )
        for i, c in enumerate(msg.get("tool_calls") or ())
    )


class OllamaAdapter(OpenAICompatAdapter):
    """Ollama native `POST {root}/api/chat` (D-19). The OpenAI-compatible route ignores
    `keep_alive` and `num_ctx`: on a CPU host the model then unloads after 5 minutes idle and the
    next demo turn pays the reload. The native route also reports prompt-eval / generation time.
    Embeddings stay on the OpenAI-compatible `/v1/embeddings` (inherited)."""

    def __init__(
        self, root_url: str, *, temperature: float, max_tokens: int, keep_alive: str,
        num_ctx: int,
    ) -> None:  # fmt: skip
        self.root = root_url.rstrip("/")
        super().__init__("ollama", self.root + "/v1", None, temperature=temperature,
                         max_tokens=max_tokens)  # fmt: skip
        self.keep_alive, self.num_ctx = keep_alive, num_ctx

    @staticmethod
    def _native_message(m: Message) -> dict[str, Any]:
        out: dict[str, Any] = {"role": m.role, "content": m.content}
        if m.tool_calls:
            out["tool_calls"] = [
                {"function": {"name": c.name, "arguments": c.arguments}} for c in m.tool_calls
            ]
        return out

    def native_body(self, req: ChatRequest, model: str, *, stream: bool) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": [self._native_message(m) for m in req.messages],
            "stream": stream,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": self.temperature if req.temperature is None else req.temperature,
                "num_predict": req.max_output_tokens or self.max_tokens,
                "num_ctx": self.num_ctx,
            },
        }
        if req.tools:
            body["tools"] = self._body(req, model, stream=False)["tools"]
        if req.json_schema is not None:
            body["format"] = req.json_schema
        return body

    async def chat(self, req: ChatRequest, *, model: str, timeout_s: float) -> ChatResponse:
        try:
            async with (
                asyncio.timeout(timeout_s),
                httpx.AsyncClient(timeout=_timeout(timeout_s)) as client,
            ):
                data = await _post(client, self.name, f"{self.root}/api/chat",
                                   self.native_body(req, model, stream=False), {})  # fmt: skip
        except TimeoutError as exc:
            raise ProviderCallError(self.name, retryable=True, status=None, timeout=True) from exc
        msg = data.get("message") or {}
        timings = _ollama_timings(data)
        return ChatResponse(
            content=msg.get("content") or "",
            provider=self.name,
            model=data.get("model") or model,
            usage=Usage(timings["prompt_tokens"], timings["gen_tokens"]),
            tool_calls=_ollama_calls(msg),
            finish_reason=data.get("done_reason") or "stop",
            timings=timings,
        )

    async def stream(
        self, req: ChatRequest, *, model: str, timeout_s: float
    ) -> AsyncIterator[ChatChunk]:
        """NDJSON token stream. `timeout_s` bounds the whole call: the socket idle timeout covers
        the prompt evaluation, the deadline is re-checked on every line."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_s
        calls: tuple[ToolCall, ...] = ()
        try:
            async with (
                httpx.AsyncClient(timeout=_timeout(timeout_s)) as client,
                client.stream("POST", f"{self.root}/api/chat",
                              json=self.native_body(req, model, stream=True)) as r,
            ):  # fmt: skip
                if r.status_code >= 400:
                    raise ProviderCallError(
                        self.name, retryable=_retryable(r.status_code), status=r.status_code,
                        timeout=False,
                    )  # fmt: skip
                async for line in r.aiter_lines():
                    if loop.time() > deadline:
                        raise ProviderCallError(self.name, retryable=True, status=None,
                                                timeout=True)  # fmt: skip
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    msg = event.get("message") or {}
                    calls += _ollama_calls(msg, len(calls))
                    if msg.get("content"):
                        yield ChatChunk(delta=msg["content"], provider=self.name, model=model)
                    if event.get("done"):
                        t = _ollama_timings(event)
                        yield ChatChunk(
                            done=True, usage=Usage(t["prompt_tokens"], t["gen_tokens"]),
                            provider=self.name, model=model, tool_calls=calls, timings=t,
                        )  # fmt: skip
                        return
        except httpx.TimeoutException as exc:
            raise ProviderCallError(self.name, retryable=True, status=None, timeout=True) from exc
        except httpx.TransportError as exc:
            raise ProviderCallError(self.name, retryable=True, status=None, timeout=False) from exc
        yield ChatChunk(done=True, provider=self.name, model=model, tool_calls=calls)

    async def warm(self, model: str, *, timeout_s: float = 120.0) -> None:
        """Load `model` into RAM with this adapter's `keep_alive` (no prompt, no generation)."""
        async with httpx.AsyncClient(timeout=_timeout(timeout_s)) as client:
            await _post(client, self.name, f"{self.root}/api/generate",
                        {"model": model, "keep_alive": self.keep_alive}, {})  # fmt: skip

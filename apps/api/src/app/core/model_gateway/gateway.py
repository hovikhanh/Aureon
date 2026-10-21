"""ModelGateway — the only path to an LLM (07 §6, DEC-131, CLAUDE.md §5.5).

Flow per request: classification route (§6.5) → budget guard (§6.3) → mode:
  fixture: recorded response by `prompt_sha256` (no network; missing → FixtureMissingError)
  live:    provider chain; each provider retried ≤ 2× on 5xx/429/timeout (backoff 1 s, 3 s),
           a 4xx content error stops the chain (no fallback); open circuit → provider skipped
  record:  live, then the masked response is written as a fixture (dev only)
Every attempt (ok, error, fallback, template/blocked decision) goes to the `CallLogSink`
(`ai` module writes `ENT-ModelCallLog`; `core/` cannot import modules — DEC-125).
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, replace
from typing import Literal, Protocol

from app.core.config import ConfigService, get_config
from app.core.errors import ai_error
from app.core.model_gateway.adapters import Adapter, AnthropicAdapter, OpenAICompatAdapter
from app.core.model_gateway.cost import estimate_cost_micro_usd
from app.core.model_gateway.errors import (
    ProviderCallError,
    SecretDataBlockedError,
    TemplateRequired,
    provider_error,
)
from app.core.model_gateway.fixtures import FixtureStore
from app.core.model_gateway.routing import TEMPLATE, Route, model_for, route
from app.core.model_gateway.types import ChatChunk, ChatRequest, ChatResponse, Usage

log = logging.getLogger("app.model_gateway")

CallStatus = Literal["ok", "error", "forbidden", "timeout"]
RETRY_BACKOFF_S: tuple[float, ...] = (1.0, 3.0)  # 07 §6.2: ≤ 2 retries per provider
BREAKER_FAILURES, BREAKER_WINDOW_S, BREAKER_OPEN_S = 5, 60.0, 120.0


@dataclass(frozen=True)
class CallRecord:
    """One row of `ENT-ModelCallLog` (05 §4.8) + the routing reason (logged, not stored raw)."""

    caller_module: str
    task_kind: str
    provider: str
    model: str
    status: CallStatus
    tokens_in: int
    tokens_out: int
    estimated_cost_micro_usd: int
    latency_ms: int
    prompt_sha256: str
    classification: str
    route_reason: str
    fallback_from: str | None = None
    error_code: str | None = None
    user_id: object = None
    message_id: object = None
    source_document_id: object = None


class CallLogSink(Protocol):
    async def record(self, rec: CallRecord) -> None: ...

    async def month_spend_micro_usd(self) -> int: ...


class NullSink:
    """No persistence (unit tests / scripts). Production wires `ai.ModelCallLogWriter`."""

    def __init__(self) -> None:
        self.records: list[CallRecord] = []

    async def record(self, rec: CallRecord) -> None:
        self.records.append(rec)

    async def month_spend_micro_usd(self) -> int:
        return sum(r.estimated_cost_micro_usd for r in self.records)


class CircuitBreaker:
    """≥ 5 failures in 60 s → provider skipped for 120 s (07 §6.2). Process-local."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._fails: dict[str, deque[float]] = defaultdict(deque)
        self._open_until: dict[str, float] = {}

    def is_open(self, provider: str) -> bool:
        return self._clock() < self._open_until.get(provider, 0.0)

    def failure(self, provider: str) -> None:
        now, q = self._clock(), self._fails[provider]
        q.append(now)
        while q and now - q[0] > BREAKER_WINDOW_S:
            q.popleft()
        if len(q) >= BREAKER_FAILURES:
            self._open_until[provider] = now + BREAKER_OPEN_S
            q.clear()

    def success(self, provider: str) -> None:
        self._fails.pop(provider, None)


BREAKER = CircuitBreaker()


def build_adapter(cfg: ConfigService, provider: str) -> Adapter:
    temp, max_tok = cfg.model_temperature, cfg.model_max_output_tokens
    if provider == "anthropic":
        key = cfg.anthropic_api_key.get_secret_value() if cfg.anthropic_api_key else None
        return AnthropicAdapter(cfg.anthropic_base_url, key, temperature=temp, max_tokens=max_tok)
    if provider == "ollama":
        base = cfg.ollama_base_url.rstrip("/") + "/v1"
        return OpenAICompatAdapter("ollama", base, None, temperature=temp, max_tokens=max_tok)
    secret = getattr(cfg, f"{provider}_api_key")
    base_url: str = getattr(cfg, f"{provider}_base_url")
    key = secret.get_secret_value() if secret else None
    return OpenAICompatAdapter(provider, base_url, key, temperature=temp, max_tokens=max_tok)


class ModelGateway:
    def __init__(
        self,
        sink: CallLogSink | None = None,
        *,
        cfg: ConfigService | None = None,
        fixtures: FixtureStore | None = None,
        adapter_factory: Callable[[ConfigService, str], Adapter] = build_adapter,
        breaker: CircuitBreaker = BREAKER,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.cfg = cfg or get_config()
        self.sink: CallLogSink = sink or NullSink()
        self.fixtures = fixtures or FixtureStore()
        self._adapter = adapter_factory
        self.breaker = breaker
        self._sleep = sleep

    # --- helpers -------------------------------------------------------------------------

    def _rec(
        self, req: ChatRequest, rt: Route, provider: str, model: str, status: CallStatus,
        started: float, *, usage: Usage | None = None, fallback_from: str | None = None,
        error_code: str | None = None,
    ) -> CallRecord:  # fmt: skip
        u = usage or Usage()
        cost = estimate_cost_micro_usd(
            self.cfg.model_pricing_json, provider, model, u.tokens_in, u.tokens_out
        )
        return CallRecord(
            caller_module=req.caller_module, task_kind=req.task, provider=provider, model=model,
            status=status, tokens_in=u.tokens_in, tokens_out=u.tokens_out,
            estimated_cost_micro_usd=cost, latency_ms=int((time.monotonic() - started) * 1000),
            prompt_sha256=req.prompt_sha256(), classification=rt.classification,
            route_reason=rt.reason, fallback_from=fallback_from, error_code=error_code,
            user_id=req.user_id, message_id=req.message_id,
            source_document_id=req.source_document_id,
        )  # fmt: skip

    async def _route(self, req: ChatRequest) -> Route:
        started = time.monotonic()
        try:
            return route(self.cfg, req.classification)
        except SecretDataBlockedError:
            rt = Route("SECRET", (), "secret: never sent to an LLM")
            await self.sink.record(
                self._rec(req, rt, "none", "none", "forbidden", started,
                          error_code="CLASSIFICATION_SECRET")
            )  # fmt: skip
            raise

    async def _check_budget(self) -> None:
        budget = int(self.cfg.ai_monthly_budget_usd * 1_000_000)
        if budget and await self.sink.month_spend_micro_usd() >= budget:
            raise ai_error("AI_QUOTA_EXCEEDED", "monthly AI budget exhausted")

    async def _template(self, req: ChatRequest, rt: Route, last: str | None) -> TemplateRequired:
        await self.sink.record(
            self._rec(req, rt, TEMPLATE, TEMPLATE, "forbidden", time.monotonic(),
                      fallback_from=last, error_code=f"CLASSIFICATION_{rt.classification}")
        )  # fmt: skip
        return TemplateRequired(rt.classification, "no local LLM available — use template")

    # --- public API ----------------------------------------------------------------------

    async def chat(self, req: ChatRequest) -> ChatResponse:
        rt = await self._route(req)
        await self._check_budget()
        if self.cfg.model_gateway_mode == "fixture":
            return await self._fixture(req, rt)
        resp = await self._live(req, rt)
        if self.cfg.model_gateway_mode == "record":
            self.fixtures.save(req, resp)
        return resp

    async def extract(self, req: ChatRequest) -> ChatResponse:
        """Structured output: `json_schema` required; `data` = parsed JSON (07 §6)."""
        if req.json_schema is None:
            raise ValueError("extract() needs ChatRequest.json_schema")
        resp = await self.chat(req)
        if resp.data is not None:
            return resp
        try:
            return replace(resp, data=json.loads(resp.content))
        except json.JSONDecodeError as exc:
            raise ai_error("AI_FUNCTION_CALL_FAILED", "model output is not valid JSON") from exc

    async def _fixture(self, req: ChatRequest, rt: Route) -> ChatResponse:
        started = time.monotonic()
        resp = self.fixtures.load(req)  # FixtureMissingError propagates (loud)
        await self.sink.record(self._rec(req, rt, "fixture", resp.model, "ok", started,
                                         usage=resp.usage))  # fmt: skip
        return resp

    async def _live(self, req: ChatRequest, rt: Route) -> ChatResponse:
        last_err: ProviderCallError | None = None
        failed_from: str | None = None
        for provider in rt.providers:
            if provider == TEMPLATE:
                raise await self._template(req, rt, failed_from)
            if self.breaker.is_open(provider):
                log.warning("model_gateway: circuit open, skip %s", provider)
                continue
            model = model_for(self.cfg, req.task, provider)
            adapter = self._adapter(self.cfg, provider)
            for attempt in range(len(RETRY_BACKOFF_S) + 1):
                started = time.monotonic()
                try:
                    resp = await adapter.chat(
                        req, model=model, timeout_s=self.cfg.ai_turn_timeout_sec
                    )
                except ProviderCallError as err:
                    last_err = err
                    self.breaker.failure(provider)
                    status: CallStatus = "timeout" if err.timeout else "error"
                    code = "AI_PROVIDER_TIMEOUT" if err.timeout else "AI_PROVIDER_ERROR"
                    await self.sink.record(
                        self._rec(
                            req,
                            rt,
                            provider,
                            model,
                            status,
                            started,
                            fallback_from=failed_from,
                            error_code=code,
                        )
                    )
                    if not err.retryable:
                        raise provider_error(err) from err  # 4xx content: no fallback
                    if attempt < len(RETRY_BACKOFF_S):
                        await self._sleep(RETRY_BACKOFF_S[attempt])
                    continue
                self.breaker.success(provider)
                resp = replace(resp, fallback_from=failed_from)
                await self.sink.record(
                    self._rec(
                        req,
                        rt,
                        provider,
                        resp.model,
                        "ok",
                        started,
                        usage=resp.usage,
                        fallback_from=failed_from,
                    )
                )
                return resp
            failed_from = provider
        raise provider_error(last_err)

    async def stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Token stream. Fallback only before the first token (a half answer is not retried)."""
        rt = await self._route(req)
        await self._check_budget()
        if self.cfg.model_gateway_mode == "fixture":
            resp = await self._fixture(req, rt)
            for word in resp.content.split(" "):
                yield ChatChunk(delta=word + " ", provider="fixture", model=resp.model)
            yield ChatChunk(done=True, usage=resp.usage, provider="fixture", model=resp.model)
            return
        last_err: ProviderCallError | None = None
        failed_from: str | None = None
        for provider in rt.providers:
            if provider == TEMPLATE:
                raise await self._template(req, rt, failed_from)
            if self.breaker.is_open(provider):
                continue
            model = model_for(self.cfg, req.task, provider)
            started, emitted = time.monotonic(), False
            try:
                adapter = self._adapter(self.cfg, provider)
                async for chunk in adapter.stream(
                    req, model=model, timeout_s=self.cfg.ai_turn_timeout_sec
                ):
                    emitted = True
                    if chunk.done:
                        await self.sink.record(
                            self._rec(
                                req,
                                rt,
                                provider,
                                model,
                                "ok",
                                started,
                                usage=chunk.usage,
                                fallback_from=failed_from,
                            )
                        )
                    yield chunk
                self.breaker.success(provider)
                return
            except ProviderCallError as err:
                last_err = err
                self.breaker.failure(provider)
                await self.sink.record(self._rec(
                    req, rt, provider, model, "timeout" if err.timeout else "error", started,
                    fallback_from=failed_from,
                    error_code="AI_PROVIDER_TIMEOUT" if err.timeout else "AI_PROVIDER_ERROR",
                ))  # fmt: skip
                if emitted or not err.retryable:
                    raise provider_error(err) from err
                failed_from = provider
        raise provider_error(last_err)

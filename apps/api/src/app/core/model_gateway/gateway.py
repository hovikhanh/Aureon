"""ModelGateway — the ONLY place allowed to call an LLM (CLAUDE.md "IDP Worker", 07 §5.2, T-006).

Live mode posts to OmniRoute's OpenAI-compatible `/chat/completions` with httpx (no provider
SDK). Fixture mode replays recorded outputs (07 §9). Failure policy (04 §14 IDP-E06, 07 §5.1):

* each route gets 1 attempt + 3 retries with backoff 2 s → 8 s → 30 s on timeout, transport
  error, HTTP 5xx and 429; other 4xx are fatal and raise immediately (retrying cannot help);
* when the primary model is exhausted, each fallback model is tried (default: a single
  attempt, `fallback_backoff=()`), then `ModelGatewayError(code="IDP-E06")` is raised so the
  pipeline moves the document to `FAILED` (FR-DC-22, TC-IDP-030);
* JSON / schema-invalid output is retried once with a schema reminder, then
  `ModelOutputError(code="IDP-E07")` (04 §13.1 PI-02).

Credentials: the API key lives in a `SecretStr`, is only materialised into the per-request
Authorization header, and never appears in logs, exception messages, `CallRecord`s or repr.
Logged metadata = task_type, model, attempt, status, latency, tokens (no document content).
"""

import json
import logging
import re
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any, TypeVar, cast

import httpx
from pydantic import BaseModel, SecretStr, ValidationError

from app.core.config import REPO_ROOT, ConfigService, get_config
from app.core.model_gateway.errors import IDP_E06, ModelGatewayError, ModelOutputError
from app.core.model_gateway.fixtures import FixtureStore, fixture_hash
from app.core.model_gateway.prompting import json_schema_instruction
from app.core.model_gateway.types import (
    CallRecord,
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    GatewayMode,
    TaskType,
    TokenUsage,
)

logger = logging.getLogger("app.model_gateway")

T = TypeVar("T", bound=BaseModel)
CallHook = Callable[[CallRecord], None]
SleepFn = Callable[[float], None]
MessagesIn = Sequence[ChatMessage] | Sequence[Mapping[str, str]]

DEFAULT_BACKOFF_S: tuple[float, ...] = (2.0, 8.0, 30.0)  # IDP-E06 (04 §14)
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_FIXTURE_DIR = REPO_ROOT / "apps" / "api" / "tests" / "fixtures" / "model_gateway"
SCHEMA_RETRIES = 1  # PI-02 / IDP-E07: one retry with schema reminder
_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


class _AttemptError(Exception):
    """Internal: one HTTP attempt failed. Message is pre-sanitised (no key, no body)."""

    def __init__(self, reason: str, *, retryable: bool, status_code: int | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.retryable = retryable
        self.status_code = status_code


def default_routes(config: ConfigService) -> dict[TaskType, str]:
    # 07 §5.2 Routing: model per task_type via env (MODEL_CLASSIFY / MODEL_EXTRACT).
    return {
        "classify": config.model_classify,
        "extract": config.model_extract,
        "mapping": config.model_extract,
        "assistant": config.model_classify,
    }


def default_fallbacks(config: ConfigService) -> dict[TaskType, list[str]]:
    # No MODEL_FALLBACK env var exists yet (proposed DEC): fall back to the other configured
    # OmniRoute route so a failing/rate-limited combo does not fail the document outright.
    routes = default_routes(config)
    other = {
        config.model_classify: config.model_extract,
        config.model_extract: config.model_classify,
    }
    return {
        task: [other[model]] if other.get(model, model) != model else []
        for task, model in routes.items()
    }


def parse_json_content(content: str) -> Any:
    """Parse model text as JSON, tolerating a single ```json fenced block."""
    text = content.strip()
    fenced = _JSON_FENCE.match(text)
    if fenced:
        text = fenced.group(1)
    return json.loads(text)


def _to_messages(messages: MessagesIn) -> tuple[ChatMessage, ...]:
    return tuple(
        m if isinstance(m, ChatMessage) else ChatMessage.model_validate(dict(m)) for m in messages
    )


class ModelGateway:
    """Single LLM entry point. Thread-safe enough for Celery prefork (one instance per process)."""

    def __init__(
        self,
        config: ConfigService | None = None,
        *,
        mode: GatewayMode | str | None = None,
        routes: Mapping[TaskType, str] | None = None,
        fallbacks: Mapping[TaskType, Sequence[str]] | None = None,
        backoff_s: Sequence[float] = DEFAULT_BACKOFF_S,
        fallback_backoff_s: Sequence[float] = (),
        timeout_s: float = DEFAULT_TIMEOUT_S,
        fixture_dir: Path | str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: SleepFn = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        hooks: Iterable[CallHook] = (),
        use_response_format: bool = True,
    ) -> None:
        cfg = config or get_config()
        resolved_mode = (mode or cfg.model_gateway_mode).strip().lower()
        if resolved_mode not in ("live", "fixture"):
            raise ValueError(
                f"MODEL_GATEWAY_MODE must be 'live' or 'fixture', got {resolved_mode!r}"
            )
        self.mode: GatewayMode = cast(GatewayMode, resolved_mode)
        self.base_url = cfg.omniroute_base_url.rstrip("/")
        self._api_key: SecretStr = cfg.omniroute_api_key
        self.routes: dict[TaskType, str] = dict(
            routes if routes is not None else default_routes(cfg)
        )
        self.fallbacks: dict[TaskType, list[str]] = {
            k: list(v)
            for k, v in (fallbacks if fallbacks is not None else default_fallbacks(cfg)).items()
        }
        self.backoff_s = tuple(backoff_s)
        self.fallback_backoff_s = tuple(fallback_backoff_s)
        self.timeout_s = timeout_s
        self.fixtures = FixtureStore(Path(fixture_dir) if fixture_dir else DEFAULT_FIXTURE_DIR)
        self.use_response_format = use_response_format
        self._sleep = sleep
        self._clock = clock
        self._hooks: list[CallHook] = list(hooks)
        self._client = httpx.Client(transport=transport) if self.mode == "live" else None
        # TC-IDP-036 call counters.
        self.call_count = 0  # logical complete() calls
        self.attempt_count = 0  # HTTP attempts + fixture replays
        self.records: list[CallRecord] = []

    def __repr__(self) -> str:
        return (
            f"ModelGateway(mode={self.mode!r}, base_url={self.base_url!r}, routes={self.routes!r})"
        )

    # -- hooks / counters ---------------------------------------------------------------------

    def add_hook(self, hook: CallHook) -> None:
        """Register a callback receiving every `CallRecord` (call counting, model_call_log)."""
        self._hooks.append(hook)

    def reset_counters(self) -> None:
        self.call_count = 0
        self.attempt_count = 0
        self.records.clear()

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    def _record(self, record: CallRecord) -> None:
        self.attempt_count += 1
        self.records.append(record)
        log = (
            logger.warning
            if record.outcome != "ok" and record.outcome != "fixture_hit"
            else logger.info
        )
        log(
            "model_call task_type=%s mode=%s model=%s attempt=%d outcome=%s status=%s "
            "latency_ms=%d tokens_in=%d tokens_out=%d error=%s",
            record.task_type,
            record.mode,
            record.model,
            record.attempt,
            record.outcome,
            record.status_code,
            record.latency_ms,
            record.prompt_tokens,
            record.completion_tokens,
            record.error,
        )
        for hook in self._hooks:
            hook(record)

    # -- public API ---------------------------------------------------------------------------

    def complete(
        self,
        task_type: TaskType,
        messages: MessagesIn,
        response_schema: type[BaseModel] | None = None,
        *,
        json_mode: bool = False,
        max_tokens: int | None = None,
        temperature: float | None = 0.0,
        timeout_s: float | None = None,
        fixture_key: str | None = None,
    ) -> CompletionResponse:
        """07 §5.2 interface. With `response_schema`, `data` is a validated model instance;
        with `json_mode`, `data` is the parsed JSON; otherwise `data` is None."""
        msgs = _to_messages(messages)
        structured = response_schema is not None or json_mode
        if response_schema is not None:
            msgs = (
                *msgs,
                ChatMessage(
                    role="system",
                    content=json_schema_instruction(response_schema.model_json_schema()),
                ),
            )
        request = CompletionRequest(
            task_type=task_type,
            messages=msgs,
            json_mode=structured,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_s=timeout_s,
            fixture_key=fixture_key,
        )
        self.call_count += 1
        response = self._dispatch(request)
        if not structured:
            return response

        last_error = ""
        for schema_try in range(SCHEMA_RETRIES + 1):
            try:
                data: Any = parse_json_content(response.content)
                if response_schema is not None:
                    data = response_schema.model_validate(data)
                return response.model_copy(update={"data": data})
            except (ValueError, ValidationError) as exc:
                # ValidationError subclasses ValueError; json.JSONDecodeError too.
                last_error = type(exc).__name__
                if schema_try >= SCHEMA_RETRIES or self.mode == "fixture":
                    break
                reminder = ChatMessage(
                    role="system",
                    content="Your previous answer was not valid JSON for the required schema. "
                    "Answer again with ONLY the JSON object.",
                )
                response = self._dispatch(
                    request.model_copy(update={"messages": (*request.messages, reminder)})
                )
        raise ModelOutputError(
            f"model output for task_type={task_type} is not valid JSON/schema ({last_error})",
            task_type=task_type,
            attempts=response.attempts,
        )

    def complete_json(self, task_type: TaskType, messages: MessagesIn, **kwargs: Any) -> Any:
        """JSON-mode completion returning the parsed JSON value."""
        return self.complete(task_type, messages, json_mode=True, **kwargs).data

    def complete_structured(
        self, task_type: TaskType, messages: MessagesIn, schema: type[T], **kwargs: Any
    ) -> T:
        """JSON-mode completion validated against a Pydantic model (PI-02)."""
        return cast(T, self.complete(task_type, messages, schema, **kwargs).data)

    # -- dispatch -----------------------------------------------------------------------------

    def _dispatch(self, request: CompletionRequest) -> CompletionResponse:
        if self.mode == "fixture":
            return self._replay(request)
        return self._live(request)

    def _replay(self, request: CompletionRequest) -> CompletionResponse:
        key = request.fixture_key or fixture_hash(
            request.task_type, request.messages, request.json_mode
        )
        try:
            record = self.fixtures.load(request.task_type, key)
        except ModelGatewayError as exc:
            self._record(
                CallRecord(
                    task_type=request.task_type,
                    mode="fixture",
                    model="fixture",
                    attempt=1,
                    outcome="fixture_miss",
                    error=type(exc).__name__,
                )
            )
            raise
        self._record(
            CallRecord(
                task_type=request.task_type,
                mode="fixture",
                model=record.model,
                attempt=1,
                outcome="fixture_hit",
            )
        )
        return CompletionResponse(
            task_type=request.task_type,
            content=record.text(),
            model=record.model,
            route="fixture",
            mode="fixture",
            attempts=0,
        )

    def _live(self, request: CompletionRequest) -> CompletionResponse:
        primary = self.routes.get(request.task_type)
        if not primary:
            raise ModelGatewayError(
                f"no model route configured for task_type={request.task_type}",
                task_type=request.task_type,
                retryable=False,
            )
        plan: list[tuple[str, tuple[float, ...], bool]] = [(primary, self.backoff_s, False)]
        plan += [
            (m, self.fallback_backoff_s, True)
            for m in self.fallbacks.get(request.task_type, [])
            if m != primary
        ]
        total_attempts = 0
        failures: list[str] = []
        for model, backoff, is_fallback in plan:
            for attempt in range(len(backoff) + 1):
                if attempt > 0:
                    self._sleep(backoff[attempt - 1])
                total_attempts += 1
                try:
                    return self._attempt(request, model, attempt + 1, total_attempts, is_fallback)
                except _AttemptError as err:
                    failures.append(f"{model}#{attempt + 1}:{err.reason}")
                    if not err.retryable:
                        raise ModelGatewayError(
                            f"model gateway non-retryable error for task_type="
                            f"{request.task_type} model={model}: {err.reason}",
                            code=IDP_E06,
                            task_type=request.task_type,
                            attempts=total_attempts,
                            retryable=False,
                        ) from None
        raise ModelGatewayError(
            f"model gateway exhausted retries and fallbacks for task_type={request.task_type} "
            f"after {total_attempts} attempts ({'; '.join(failures)})",
            code=IDP_E06,
            task_type=request.task_type,
            attempts=total_attempts,
        )

    def _payload(self, request: CompletionRequest, model: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [m.model_dump() for m in request.messages],
            "stream": False,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.json_mode and self.use_response_format:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _attempt(
        self,
        request: CompletionRequest,
        model: str,
        attempt: int,
        total_attempts: int,
        is_fallback: bool,
    ) -> CompletionResponse:
        client = self._client
        if client is None:  # only reachable if called in fixture mode
            raise ModelGatewayError("live HTTP call attempted in fixture mode", retryable=False)
        started = self._clock()
        status: int | None = None

        def fail(reason: str, *, retryable: bool) -> _AttemptError:
            self._record(
                CallRecord(
                    task_type=request.task_type,
                    mode="live",
                    model=model,
                    attempt=attempt,
                    outcome="retryable_error" if retryable else "fatal_error",
                    status_code=status,
                    error=reason,
                    latency_ms=int((self._clock() - started) * 1000),
                )
            )
            return _AttemptError(reason, retryable=retryable, status_code=status)

        try:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                json=self._payload(request, model),
                headers={"Authorization": f"Bearer {self._api_key.get_secret_value()}"},
                timeout=request.timeout_s or self.timeout_s,
            )
        except httpx.TimeoutException as exc:
            raise fail(f"timeout:{type(exc).__name__}", retryable=True) from None
        except httpx.TransportError as exc:
            raise fail(f"transport:{type(exc).__name__}", retryable=True) from None

        status = resp.status_code
        if status == 429 or status >= 500:
            raise fail(f"http_{status}", retryable=True)
        if status >= 400:
            raise fail(f"http_{status}", retryable=False)
        try:
            body = resp.json()
            choice = body["choices"][0]["message"]
            content = choice.get("content")
            if not isinstance(content, str):
                raise TypeError("content is not a string")
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            # Malformed 2xx body from the gateway: treat like a gateway error (retryable).
            raise fail("malformed_response", retryable=True) from None

        usage_raw = body.get("usage") or {}
        usage = TokenUsage(
            prompt_tokens=int(usage_raw.get("prompt_tokens") or 0),
            completion_tokens=int(usage_raw.get("completion_tokens") or 0),
            total_tokens=int(usage_raw.get("total_tokens") or 0),
        )
        latency_ms = int((self._clock() - started) * 1000)
        self._record(
            CallRecord(
                task_type=request.task_type,
                mode="live",
                model=model,
                attempt=attempt,
                outcome="ok",
                status_code=status,
                latency_ms=latency_ms,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )
        )
        return CompletionResponse(
            task_type=request.task_type,
            content=content,
            model=str(body.get("model") or model),
            route=model,
            mode="live",
            attempts=total_attempts,
            used_fallback=is_fallback,
            usage=usage,
            latency_ms=latency_ms,
        )

    def ping(self) -> bool:
        """Single-attempt liveness probe for EP-01 health; fixture mode is always available.

        Lets core/health.py stop posting to OmniRoute itself (TC-IDP-036)."""
        if self.mode == "fixture":
            return True
        probe = CompletionRequest(
            task_type="classify",
            messages=(ChatMessage(role="user", content="ping"),),
            max_tokens=1,
            timeout_s=min(self.timeout_s, 5.0),
        )
        try:
            self._attempt(probe, self.routes["classify"], 1, 1, False)
        except _AttemptError:
            return False
        return True


@lru_cache
def get_model_gateway() -> ModelGateway:
    """Process-wide gateway built from ConfigService. Tests override via `reset_model_gateway`
    + dependency injection rather than patching HTTP."""
    return ModelGateway(get_config())


def reset_model_gateway() -> None:
    get_model_gateway.cache_clear()

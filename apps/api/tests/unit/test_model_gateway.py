"""TC-AI-001/002/003/021/022 (T-013) — ModelGateway routing, fallback, fixtures, cost.

Live paths use `respx` (DEC-139) — no real network. Fixture mode asserts no HTTP at all.
"""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from pydantic import SecretStr, ValidationError

from app.core.config import ConfigService
from app.core.errors import AIError
from app.core.model_gateway import (
    ChatRequest,
    FixtureMissingError,
    Message,
    ModelGateway,
    NullSink,
    SecretDataBlockedError,
    TemplateRequired,
    ToolSpec,
)
from app.core.model_gateway.cost import estimate_cost_micro_usd
from app.core.model_gateway.fixtures import FixtureStore
from app.core.model_gateway.gateway import CircuitBreaker
from app.core.model_gateway.routing import model_for, route
from app.core.model_gateway.types import ChatResponse, Usage

KEYS = ("omniroute", "openrouter", "ninerouter", "deepseek", "openai", "anthropic")


def cfg(**kw: Any) -> ConfigService:
    base: dict[str, Any] = {
        "model_gateway_mode": "live",
        "model_provider_primary": "omniroute",
        "model_provider_fallbacks": "openrouter,deepseek",
        "model_provider_confidential": "ollama",
        "model_pricing_json": json.dumps({"openrouter:auto/coding": {"in": 3, "out": 15}}),
        "ai_monthly_budget_usd": 50,
        "chat_model_primary": "",  # dev .env may set the T-509 chain; tests opt in explicitly
        "chat_model_fallback": "",
        **{f"{p}_api_key": SecretStr(f"k-{p}") for p in KEYS},
        **{f"{p}_base_url": f"https://{p}.test/v1" for p in KEYS if p != "anthropic"},
        "anthropic_base_url": "https://anthropic.test",
        "ollama_base_url": "http://ollama.test:11434",
    }
    base.update(kw)
    return ConfigService(**base)


def req(classification: str = "INTERNAL", **kw: Any) -> ChatRequest:
    return ChatRequest(
        task=kw.pop("task", "chat"),
        messages=(Message("system", "Bạn là trợ lý."), Message("user", "Doanh thu Q3?")),
        caller_module="ai_core",
        classification=classification,  # type: ignore[arg-type]
        **kw,
    )


def ok_body(content: str = "Doanh thu 27,5 tỷ", model: str = "auto/coding") -> dict[str, Any]:
    return {
        "model": model,
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 200},
    }


async def _no_sleep(_: float) -> None:
    return None


def gw(c: ConfigService, sink: NullSink | None = None, **kw: Any) -> ModelGateway:
    return ModelGateway(sink or NullSink(), cfg=c, breaker=CircuitBreaker(), sleep=_no_sleep, **kw)


# --- routing by classification (TC-AI-021) ------------------------------------------------


def test_route_internal_is_cloud_chain() -> None:
    assert route(cfg(), "INTERNAL").providers == ("omniroute", "openrouter", "deepseek")
    assert route(cfg(), "PUBLIC").providers == ("omniroute", "openrouter", "deepseek")


def test_route_confidential_is_local_then_template() -> None:
    r = route(cfg(), "CONFIDENTIAL")
    assert r.providers == ("ollama", "template")
    assert r.reason == "confidential: local"


def test_route_confidential_admin_override_is_explicit() -> None:
    r = route(cfg(model_provider_confidential="openrouter"), "CONFIDENTIAL")
    assert r.providers == ("openrouter", "template")
    assert "override" in r.reason


def test_route_secret_never_llm() -> None:
    with pytest.raises(SecretDataBlockedError):
        route(cfg(), "SECRET")


def test_provider_without_key_is_skipped() -> None:
    c = cfg(openrouter_api_key=None, deepseek_api_key=SecretStr("<change-me>"))
    assert route(c, "INTERNAL").providers == ("omniroute",)


def test_model_per_task_and_override(monkeypatch: pytest.MonkeyPatch) -> None:
    c = cfg()
    assert model_for(c, "chat", "omniroute") == "auto/coding"
    assert model_for(c, "insight", "omniroute") == "auto/cheap"
    assert model_for(c, "chat", "ollama") == "qwen2.5:7b-instruct"  # never bge-m3
    monkeypatch.setenv("MODEL_CHAT__ANTHROPIC", "claude-x")
    assert model_for(c, "chat", "anthropic") == "claude-x"


# --- config fail-fast (TC-AI-022) ---------------------------------------------------------


@pytest.mark.parametrize(
    "kw",
    [
        {"model_provider_secret": "openai"},
        {"model_provider_primary": "gemini"},
        {"model_provider_fallbacks": "openrouter,bogus"},
        {"model_provider_confidential": "nope"},
    ],
)
def test_bad_routing_config_fails_fast(kw: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        cfg(**kw)


def test_9router_alias_accepted() -> None:
    assert route(cfg(model_provider_fallbacks="9router"), "INTERNAL").providers == (
        "omniroute",
        "ninerouter",
    )


# --- live: fallback, retry, no-fallback on 4xx (TC-AI-001) --------------------------------


@respx.mock
async def test_primary_5xx_falls_back_with_retries() -> None:
    primary = respx.post("https://omniroute.test/v1/chat/completions").mock(
        return_value=httpx.Response(503)
    )
    fb = respx.post("https://openrouter.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=ok_body())
    )
    sink = NullSink()
    resp = await gw(cfg(), sink).chat(req())
    assert primary.call_count == 3  # 1 + 2 retries (07 §6.2)
    assert fb.call_count == 1
    assert (resp.provider, resp.fallback_from, resp.content) == (
        "openrouter",
        "omniroute",
        "Doanh thu 27,5 tỷ",
    )
    assert [(r.provider, r.status) for r in sink.records] == [("omniroute", "error")] * 3 + [
        ("openrouter", "ok")
    ]
    last = sink.records[-1]
    assert (last.fallback_from, last.tokens_in, last.tokens_out) == ("omniroute", 1000, 200)
    assert last.estimated_cost_micro_usd == 1000 * 3 + 200 * 15
    assert last.prompt_sha256 == req().prompt_sha256()
    assert last.route_reason == "internal: cloud chain"


@respx.mock
async def test_429_and_timeout_are_retryable() -> None:
    respx.post("https://omniroute.test/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(429),
            httpx.ReadTimeout("t"),
            httpx.Response(200, json=ok_body()),
        ]
    )
    sink = NullSink()
    resp = await gw(cfg(), sink).chat(req())
    assert resp.provider == "omniroute"
    assert [r.status for r in sink.records] == ["error", "timeout", "ok"]


@respx.mock
async def test_4xx_content_error_does_not_fall_back() -> None:
    respx.post("https://omniroute.test/v1/chat/completions").mock(
        return_value=httpx.Response(400, json={"error": "context too long: <prompt echo>"})
    )
    fb = respx.post("https://openrouter.test/v1/chat/completions")
    with pytest.raises(AIError) as exc:
        await gw(cfg()).chat(req())
    assert exc.value.code == "AI_PROVIDER_ERROR"
    assert "prompt echo" not in str(exc.value)
    assert fb.call_count == 0


@respx.mock
async def test_chain_exhausted_timeout_maps_to_ai_provider_timeout() -> None:
    for p in ("omniroute", "openrouter", "deepseek"):
        respx.post(f"https://{p}.test/v1/chat/completions").mock(
            side_effect=httpx.ConnectTimeout("t")
        )
    with pytest.raises(AIError) as exc:
        await gw(cfg()).chat(req())
    assert (exc.value.code, exc.value.status_code) == ("AI_PROVIDER_TIMEOUT", 504)


@respx.mock
async def test_circuit_breaker_skips_provider() -> None:
    primary = respx.post("https://omniroute.test/v1/chat/completions").mock(
        return_value=httpx.Response(500)
    )
    respx.post("https://openrouter.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=ok_body())
    )
    now = [0.0]
    breaker = CircuitBreaker(clock=lambda: now[0])
    g = ModelGateway(NullSink(), cfg=cfg(), breaker=breaker, sleep=_no_sleep)
    await g.chat(req())  # 3 failures
    await g.chat(req())  # 3 more → open (≥ 5 / 60 s)
    calls = primary.call_count
    await g.chat(req())
    assert primary.call_count == calls  # skipped while open
    now[0] = 121.0
    await g.chat(req())
    assert primary.call_count > calls  # retried after the 120 s open window


# --- classification at the gateway (TC-AI-021) --------------------------------------------


@respx.mock
async def test_confidential_uses_ollama_never_cloud() -> None:
    cloud = respx.post(url__regex=r"https://.*\.test/v1/chat/completions")
    local = respx.post("http://ollama.test:11434/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=ok_body(model="qwen2.5:7b-instruct"))
    )
    sink = NullSink()
    resp = await gw(cfg(), sink).chat(req("CONFIDENTIAL"))
    assert resp.provider == "ollama"
    assert local.calls.last.request.headers.get("authorization") is None  # no key to local
    sent = json.loads(local.calls.last.request.content)
    assert sent["model"] == "qwen2.5:7b-instruct"
    assert cloud.call_count == 0
    assert sink.records[-1].route_reason == "confidential: local"


@respx.mock
async def test_confidential_local_down_goes_template_not_cloud() -> None:
    cloud = respx.post(url__regex=r"https://.*\.test/v1/chat/completions")
    respx.post("http://ollama.test:11434/v1/chat/completions").mock(
        side_effect=httpx.ConnectError("down")
    )
    sink = NullSink()
    with pytest.raises(TemplateRequired) as exc:
        await gw(cfg(), sink).chat(req("CONFIDENTIAL"))
    assert exc.value.classification == "CONFIDENTIAL"
    assert cloud.call_count == 0
    assert sink.records[-1].provider == "template"
    assert sink.records[-1].fallback_from == "ollama"


@respx.mock
async def test_secret_blocked_and_logged_without_any_http() -> None:
    any_http = respx.route()
    sink = NullSink()
    with pytest.raises(SecretDataBlockedError):
        await gw(cfg(), sink).chat(req("SECRET"))
    assert any_http.call_count == 0
    assert [(r.provider, r.status, r.error_code) for r in sink.records] == [
        ("none", "forbidden", "CLASSIFICATION_SECRET")
    ]


# --- fixture mode (TC-AI-003) -------------------------------------------------------------


@respx.mock
async def test_fixture_mode_no_network_and_logs(tmp_path: Path) -> None:
    any_http = respx.route()
    store = FixtureStore(tmp_path)
    r = req()
    store.save(r, ChatResponse("Từ fixture", "omniroute", "auto/coding", Usage(10, 5)))
    sink = NullSink()
    resp = await gw(cfg(model_gateway_mode="fixture"), sink, fixtures=store).chat(r)
    assert (resp.content, resp.provider) == ("Từ fixture", "fixture")
    assert any_http.call_count == 0
    assert (sink.records[0].provider, sink.records[0].tokens_in) == ("fixture", 10)


async def test_fixture_missing_is_loud(tmp_path: Path) -> None:
    with pytest.raises(FixtureMissingError, match="no fixture for task=chat"):
        await gw(cfg(model_gateway_mode="fixture"), fixtures=FixtureStore(tmp_path)).chat(req())


async def test_fixture_mode_still_routes_secret(tmp_path: Path) -> None:
    with pytest.raises(SecretDataBlockedError):
        await gw(cfg(model_gateway_mode="fixture"), fixtures=FixtureStore(tmp_path)).chat(
            req("SECRET")
        )


@respx.mock
async def test_record_mode_writes_masked_fixture(tmp_path: Path) -> None:
    respx.post("https://omniroute.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=ok_body("Gọi 0901234567 để xác nhận"))
    )
    store = FixtureStore(tmp_path)
    await gw(cfg(model_gateway_mode="record"), fixtures=store).chat(req())
    saved = store.path(req()).read_text(encoding="utf-8")
    assert "0901234567" not in saved
    assert "••••4567" in saved
    replay = await gw(cfg(model_gateway_mode="fixture"), fixtures=store).chat(req())
    assert replay.content == "Gọi ••••4567 để xác nhận"


def test_prompt_hash_normalizes_whitespace_and_tracks_schema() -> None:
    a = req()
    b = ChatRequest(
        task="chat",
        messages=(Message("system", "Bạn  là\ntrợ lý."), Message("user", "Doanh thu Q3?")),
        caller_module="idp",
    )
    assert a.prompt_sha256() == b.prompt_sha256()  # caller_module not part of the key
    assert req(schema_version="2").prompt_sha256() != a.prompt_sha256()
    assert len(a.prompt_sha256()) == 64


# --- budget & cost ------------------------------------------------------------------------


async def test_budget_exhausted_is_429() -> None:
    class Spent(NullSink):
        async def month_spend_micro_usd(self) -> int:
            return 50_000_000

    with pytest.raises(AIError) as exc:
        await gw(cfg(), Spent()).chat(req())
    assert (exc.value.code, exc.value.status_code) == ("AI_QUOTA_EXCEEDED", 429)


def test_cost_estimate_integer_micro_usd() -> None:
    pricing = json.dumps({"openai:gpt-x": {"in": 0.15, "out": 0.6}})
    assert estimate_cost_micro_usd(pricing, "openai", "gpt-x", 1_000_000, 1000) == 150_600
    assert estimate_cost_micro_usd(pricing, "ollama", "qwen", 10, 10) == 0
    with pytest.raises(ValueError):
        estimate_cost_micro_usd("[]", "a", "b", 1, 1)


# --- adapters (TC-AI-002) -----------------------------------------------------------------


@respx.mock
@pytest.mark.parametrize(
    "provider", ["omniroute", "openrouter", "ninerouter", "deepseek", "openai"]
)
async def test_openai_compat_adapter_uses_own_url_and_key(provider: str) -> None:
    route_ = respx.post(f"https://{provider}.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=ok_body())
    )
    c = cfg(model_provider_primary=provider, model_provider_fallbacks="")
    tool = ToolSpec("get_metric", "Lấy metric", {"type": "object", "properties": {}})
    await gw(c).chat(req(tools=(tool,), temperature=0.1))
    sent = route_.calls.last.request
    assert sent.headers["authorization"] == f"Bearer k-{provider}"
    body = json.loads(sent.content)
    assert body["tools"][0]["function"]["name"] == "get_metric"
    assert (body["temperature"], body["max_tokens"]) == (0.1, 2048)


@respx.mock
async def test_openai_compat_parses_tool_calls() -> None:
    body = ok_body("")
    body["choices"][0]["message"]["tool_calls"] = [
        {"id": "c1", "type": "function",
         "function": {"name": "get_metric", "arguments": '{"code": "METRIC-FIN-01"}'}}
    ]  # fmt: skip
    respx.post("https://omniroute.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=body)
    )
    resp = await gw(cfg()).chat(req())
    assert resp.tool_calls[0].arguments == {"code": "METRIC-FIN-01"}


@respx.mock
async def test_anthropic_adapter_maps_messages_and_tools() -> None:
    from app.core.model_gateway.types import ToolCall

    route_ = respx.post("https://anthropic.test/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "claude-x",
                "content": [
                    {"type": "text", "text": "Đang tra"},
                    {"type": "tool_use", "id": "t1", "name": "get_metric", "input": {"a": 1}},
                ],
                "usage": {"input_tokens": 50, "output_tokens": 7},
                "stop_reason": "tool_use",
            },
        )
    )
    c = cfg(model_provider_primary="anthropic", model_provider_fallbacks="")
    r = ChatRequest(
        task="chat",
        caller_module="ai_core",
        messages=(
            Message("system", "SYS"),
            Message("user", "Q"),
            Message("assistant", "", tool_calls=(ToolCall("t0", "get_metric", {}),)),
            Message("tool", '{"v": 1}', tool_call_id="t0"),
        ),
        tools=(ToolSpec("get_metric", "d", {"type": "object"}),),
    )
    resp = await gw(c).chat(r)
    sent = json.loads(route_.calls.last.request.content)
    assert route_.calls.last.request.headers["x-api-key"] == "k-anthropic"
    assert sent["system"] == "SYS"
    assert sent["messages"][1]["content"][0]["type"] == "tool_use"
    assert sent["messages"][2]["content"][0] == {
        "type": "tool_result", "tool_use_id": "t0", "content": '{"v": 1}'
    }  # fmt: skip
    assert sent["tools"][0]["input_schema"] == {"type": "object"}
    assert (resp.content, resp.tool_calls[0].name, resp.usage.tokens_in) == (
        "Đang tra",
        "get_metric",
        50,
    )


@respx.mock
async def test_extract_parses_json_and_rejects_garbage() -> None:
    schema = {"type": "object", "properties": {"total": {"type": "integer"}}}
    route_ = respx.post("https://omniroute.test/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(200, json=ok_body('{"total": 27500000}')),
            httpx.Response(200, json=ok_body("không phải JSON")),
        ]
    )
    g = gw(cfg())
    resp = await g.extract(req(task="extract", json_schema=schema))
    assert resp.data == {"total": 27500000}
    sent = json.loads(route_.calls[0].request.content)
    assert sent["response_format"]["json_schema"]["schema"] == schema
    with pytest.raises(AIError) as exc:
        await g.extract(req(task="extract", json_schema=schema))
    assert exc.value.code == "AI_FUNCTION_CALL_FAILED"
    with pytest.raises(ValueError):
        await g.extract(req(task="extract"))


@respx.mock
async def test_stream_openai_compat_and_fallback_before_first_token() -> None:
    respx.post("https://omniroute.test/v1/chat/completions").mock(return_value=httpx.Response(502))
    sse = (
        'data: {"choices":[{"delta":{"content":"Doanh "}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"thu"}}]}\n\n'
        'data: {"choices":[],"usage":{"prompt_tokens":9,"completion_tokens":2}}\n\n'
        "data: [DONE]\n\n"
    )
    respx.post("https://openrouter.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})
    )
    sink = NullSink()
    chunks = [c async for c in gw(cfg(), sink).stream(req())]
    assert "".join(c.delta for c in chunks) == "Doanh thu"
    assert chunks[-1].done and chunks[-1].usage == Usage(9, 2)
    assert [(r.provider, r.status) for r in sink.records] == [
        ("omniroute", "error"),
        ("openrouter", "ok"),
    ]


async def test_stream_fixture_mode(tmp_path: Path) -> None:
    store = FixtureStore(tmp_path)
    store.save(req(), ChatResponse("a b c", "x", "m", Usage(1, 3)))
    chunks = [c async for c in gw(cfg(model_gateway_mode="fixture"), fixtures=store).stream(req())]
    assert "".join(c.delta for c in chunks).strip() == "a b c"
    assert chunks[-1].done


@respx.mock
async def test_stream_secret_and_confidential_template() -> None:
    respx.post("http://ollama.test:11434/v1/chat/completions").mock(
        return_value=httpx.Response(503)
    )
    with pytest.raises(SecretDataBlockedError):
        [c async for c in gw(cfg()).stream(req("SECRET"))]
    with pytest.raises(TemplateRequired):
        [c async for c in gw(cfg()).stream(req("CONFIDENTIAL"))]


@respx.mock
async def test_anthropic_stream_is_single_chunk() -> None:
    respx.post("https://anthropic.test/v1/messages").mock(
        return_value=httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})
    )
    c = cfg(model_provider_primary="anthropic", model_provider_fallbacks="")
    chunks = [x async for x in gw(c).stream(req())]
    assert [x.delta for x in chunks] == ["ok", ""]


def test_no_api_key_in_logs_or_errors(caplog: pytest.LogCaptureFixture) -> None:
    """TC-SEC-001: config repr and gateway errors never carry the key."""
    c = cfg()
    assert "k-openai" not in repr(c)
    from app.core.model_gateway.errors import ProviderCallError

    assert "k-openai" not in str(
        ProviderCallError("openai", retryable=True, status=503, timeout=False)
    )


# --- T-509 / DEC-241: chat model chain + chat timeout -----------------------------------


def test_chat_model_chain_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.model_gateway.routing import models_for, timeout_for

    c = cfg(chat_model_primary="cc/claude-sonnet-5", chat_model_fallback="cl/ds-flash")
    assert models_for(c, "chat", "omniroute") == ["cc/claude-sonnet-5", "cl/ds-flash"]
    assert models_for(c, "insight", "omniroute") == ["auto/cheap"]  # chat only
    assert models_for(c, "chat", "ollama") == ["qwen2.5:7b-instruct"]  # local unaffected
    assert models_for(cfg(), "chat", "omniroute") == ["auto/coding"]  # unset → MODEL_CHAT
    monkeypatch.setenv("MODEL_CHAT__OMNIROUTE", "pinned")
    assert models_for(c, "chat", "omniroute") == ["pinned"]  # explicit override wins
    assert timeout_for(cfg(chat_timeout_seconds=90), "chat") == 90
    assert timeout_for(cfg(ai_turn_timeout_sec=30), "extract") == 30


@respx.mock
async def test_chat_primary_timeout_falls_back_to_second_model_once() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        model = json.loads(request.content)["model"]
        seen.append(model)
        if model == "slow-primary":
            raise httpx.ReadTimeout("t")
        return httpx.Response(200, json=ok_body(model=model))

    respx.post("https://omniroute.test/v1/chat/completions").mock(side_effect=handler)
    sink = NullSink()
    c = cfg(chat_model_primary="slow-primary", chat_model_fallback="fast-fallback")
    resp = await gw(c, sink).chat(req())
    assert seen == ["slow-primary", "fast-fallback"]  # one attempt each, no 3× retry
    assert resp.model == "fast-fallback"
    assert resp.fallback_from == "omniroute:slow-primary"
    assert [r.status for r in sink.records] == ["timeout", "ok"]


async def test_call_record_carries_request_id_and_agent_m16() -> None:
    """T-647 (05 §2.8): `CallRecord.request_id` from `X-Request-Id`, agent from the request."""
    from app.core import request_context

    sink = NullSink()
    token = request_context._request_id.set("6f1c1d8e-0000-4000-8000-000000000001")
    try:
        with pytest.raises(SecretDataBlockedError):
            await gw(cfg(), sink).chat(req("SECRET", agent_profile_code="ceo"))
    finally:
        request_context._request_id.reset(token)
    rec = sink.records[-1]
    assert rec.request_id == "6f1c1d8e-0000-4000-8000-000000000001"
    assert rec.agent_profile_code == "ceo"

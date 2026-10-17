"""TC-IDP-030 (gateway part, T-006): timeout → retry 2/8/30 s → fallback → IDP-E06.

04 §14 IDP-E06, 07 §5.1/§5.2. Uses httpx.MockTransport; sleep is injected (no real waits).
"""

from collections.abc import Callable

import httpx
import pytest
from pydantic import BaseModel

from app.core.model_gateway import (
    IDP_E06,
    IDP_E07,
    CallRecord,
    ModelGateway,
    ModelGatewayError,
    ModelOutputError,
)

from .conftest import BASE_URL, Recorder, ok_body

GatewayFactory = Callable[..., ModelGateway]
MSG = [{"role": "user", "content": "hello"}]


def test_timeouts_retry_with_backoff_then_fallback_then_idp_e06(
    make_gateway: GatewayFactory, sleeps: list[float]
) -> None:
    rec = Recorder(httpx.ReadTimeout("slow"))
    gw = make_gateway(rec, fallbacks={"classify": ["fallback-model"]})

    with pytest.raises(ModelGatewayError) as info:
        gw.complete("classify", MSG)

    err = info.value
    assert err.code == IDP_E06 == "IDP-E06"
    assert err.task_type == "classify"
    assert err.retryable is True
    # 1 + 3 retries on primary, then 1 attempt on fallback.
    assert rec.models() == ["primary-model"] * 4 + ["fallback-model"]
    assert err.attempts == 5
    assert sleeps == [2.0, 8.0, 30.0]
    assert "timeout:ReadTimeout" in str(err)
    assert str(err).startswith("[IDP-E06]")
    assert gw.call_count == 1
    assert gw.attempt_count == 5


def test_fallback_succeeds_after_primary_exhausted(
    make_gateway: GatewayFactory, sleeps: list[float]
) -> None:
    rec = Recorder(
        httpx.Response(503),
        httpx.Response(500),
        httpx.Response(429),
        httpx.ConnectError("down"),
        httpx.Response(200, json=ok_body("from fallback", model="real-fb")),
    )
    gw = make_gateway(rec, fallbacks={"classify": ["fallback-model"]})

    resp = gw.complete("classify", MSG)

    assert resp.content == "from fallback"
    assert resp.used_fallback is True
    assert resp.route == "fallback-model"
    assert resp.model == "real-fb"
    assert resp.attempts == 5
    assert sleeps == [2.0, 8.0, 30.0]


def test_fallback_backoff_is_configurable(
    make_gateway: GatewayFactory, sleeps: list[float]
) -> None:
    rec = Recorder(httpx.Response(502))
    gw = make_gateway(
        rec,
        backoff_s=(0.5,),
        fallback_backoff_s=(1.0,),
        fallbacks={"classify": ["fb-1", "fb-2", "primary-model"]},  # primary deduplicated
    )

    with pytest.raises(ModelGatewayError):
        gw.complete("classify", MSG)

    assert rec.models() == ["primary-model"] * 2 + ["fb-1"] * 2 + ["fb-2"] * 2
    assert sleeps == [0.5, 1.0, 1.0]


def test_success_on_second_attempt(make_gateway: GatewayFactory, sleeps: list[float]) -> None:
    rec = Recorder(httpx.ReadTimeout("slow"), httpx.Response(200, json=ok_body("ok")))
    records: list[CallRecord] = []
    gw = make_gateway(rec, hooks=[records.append])

    resp = gw.complete("classify", MSG, max_tokens=7, timeout_s=3.5)

    assert resp.content == "ok"
    assert resp.attempts == 2
    assert resp.used_fallback is False
    assert resp.usage.total_tokens == 16
    assert sleeps == [2.0]
    assert [r.outcome for r in records] == ["retryable_error", "ok"]
    req = rec.requests[-1]
    assert str(req.url) == f"{BASE_URL}/chat/completions"
    assert rec.bodies()[-1]["max_tokens"] == 7
    assert req.extensions["timeout"]["read"] == 3.5


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_non_retryable_4xx_raises_immediately(
    make_gateway: GatewayFactory, sleeps: list[float], status: int
) -> None:
    rec = Recorder(httpx.Response(status, json={"error": "nope"}))
    gw = make_gateway(rec, fallbacks={"classify": ["fallback-model"]})

    with pytest.raises(ModelGatewayError) as info:
        gw.complete("classify", MSG)

    assert info.value.code == IDP_E06
    assert info.value.retryable is False
    assert info.value.attempts == 1
    assert f"http_{status}" in str(info.value)
    assert len(rec.requests) == 1
    assert sleeps == []


def test_malformed_2xx_body_is_retried(make_gateway: GatewayFactory, sleeps: list[float]) -> None:
    rec = Recorder(
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"choices": [{"message": {"content": None}}]}),
        httpx.Response(200, json=ok_body("finally")),
    )
    gw = make_gateway(rec)

    assert gw.complete("classify", MSG).content == "finally"
    assert sleeps == [2.0, 8.0, 30.0]


def test_default_routes_and_fallbacks_come_from_config(
    make_gateway: GatewayFactory, sleeps: list[float]
) -> None:
    rec = Recorder(httpx.Response(500))
    gw = make_gateway(rec, backoff_s=())

    with pytest.raises(ModelGatewayError):
        gw.complete("extract", MSG)

    # MODEL_EXTRACT primary, MODEL_CLASSIFY as cross-route fallback.
    assert rec.models() == ["extract-model", "primary-model"]


def test_missing_route_raises(make_gateway: GatewayFactory) -> None:
    gw = make_gateway(Recorder(httpx.Response(200, json=ok_body("x"))), routes={})
    with pytest.raises(ModelGatewayError, match="no model route"):
        gw.complete("classify", MSG)


class Classified(BaseModel):
    doc_type: str
    confidence: float


def test_json_mode_and_schema_validation(make_gateway: GatewayFactory) -> None:
    rec = Recorder(
        httpx.Response(
            200, json=ok_body('```json\n{"doc_type": "INVOICE", "confidence": 0.9}\n```')
        )
    )
    gw = make_gateway(rec)

    result = gw.complete_structured("classify", MSG, Classified)

    assert result == Classified(doc_type="INVOICE", confidence=0.9)
    body = rec.bodies()[0]
    assert body["response_format"] == {"type": "json_object"}
    assert body["temperature"] == 0.0
    assert "JSON Schema" in body["messages"][-1]["content"]
    assert gw.complete_json("classify", MSG) == {"doc_type": "INVOICE", "confidence": 0.9}


def test_schema_violation_retries_once_then_idp_e07(make_gateway: GatewayFactory) -> None:
    rec = Recorder(httpx.Response(200, json=ok_body('{"doc_type": "INVOICE"}')))
    gw = make_gateway(rec, use_response_format=False)

    with pytest.raises(ModelOutputError) as info:
        gw.complete("classify", MSG, Classified)

    assert info.value.code == IDP_E07
    assert len(rec.requests) == 2  # PI-02: one retry with schema reminder
    assert "response_format" not in rec.bodies()[0]
    assert "not valid JSON" in rec.bodies()[1]["messages"][-1]["content"]


def test_schema_retry_can_recover(make_gateway: GatewayFactory) -> None:
    rec = Recorder(
        httpx.Response(200, json=ok_body("sorry, here you go")),
        httpx.Response(200, json=ok_body('{"doc_type": "CONTRACT", "confidence": 0.8}')),
    )
    gw = make_gateway(rec)
    assert gw.complete_json("classify", MSG) == {"doc_type": "CONTRACT", "confidence": 0.8}
    assert gw.call_count == 2 - 1  # one logical call, two HTTP attempts
    assert gw.attempt_count == 2


def test_invalid_mode_rejected(make_gateway: GatewayFactory) -> None:
    with pytest.raises(ValueError, match="MODEL_GATEWAY_MODE"):
        make_gateway(mode="offline")


def test_ping(make_gateway: GatewayFactory) -> None:
    assert make_gateway(Recorder(httpx.Response(200, json=ok_body("")))).ping() is True
    assert make_gateway(Recorder(httpx.Response(500))).ping() is False
    assert make_gateway(mode="fixture").ping() is True


def test_reset_counters_and_close(make_gateway: GatewayFactory) -> None:
    gw = make_gateway(Recorder(httpx.Response(200, json=ok_body("x"))))
    seen: list[CallRecord] = []
    gw.add_hook(seen.append)
    gw.complete("assistant", MSG)
    assert (gw.call_count, gw.attempt_count, len(seen)) == (1, 1, 1)
    gw.reset_counters()
    assert (gw.call_count, gw.attempt_count, gw.records) == (0, 0, [])
    gw.close()

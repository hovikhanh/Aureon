"""TC-IDP-036 (b): MODEL_GATEWAY_MODE=fixture replays deterministically and counts calls.

07 §5.2 "Fixture mode", §9 offline demo (missing fixture → clear error → FAILED).
"""

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from pydantic import BaseModel

from app.core.config import ConfigService
from app.core.model_gateway import (
    DEFAULT_FIXTURE_DIR,
    IDP_E06,
    CallRecord,
    ChatMessage,
    FixtureNotFoundError,
    FixtureStore,
    ModelGateway,
    ModelGatewayError,
    ModelOutputError,
    build_document_messages,
    fixture_hash,
    get_model_gateway,
    reset_model_gateway,
)

GatewayFactory = Callable[..., ModelGateway]


class Classified(BaseModel):
    doc_type: str
    confidence: float


def _fail_transport(request: httpx.Request) -> httpx.Response:
    raise AssertionError("fixture mode must never hit the network")


def test_replay_by_explicit_key_is_deterministic_and_counted(
    make_gateway: GatewayFactory, tmp_path: Path
) -> None:
    store = FixtureStore(tmp_path / "fixtures")
    sha = "a" * 64
    store.save(
        "classify",
        f"{sha}.classify",
        data={"doc_type": "INVOICE", "confidence": 0.97},
        note="DOC-01",
    )
    records: list[CallRecord] = []
    gw = make_gateway(
        mode="fixture", hooks=[records.append], transport=httpx.MockTransport(_fail_transport)
    )
    msgs = build_document_messages("Classify the document.", "HÓA ĐƠN GTGT ...")

    first = gw.complete_structured("classify", msgs, Classified, fixture_key=f"{sha}.classify")
    second = gw.complete_structured("classify", msgs, Classified, fixture_key=f"{sha}.classify")

    assert first == second == Classified(doc_type="INVOICE", confidence=0.97)
    assert gw.call_count == 2
    assert gw.attempt_count == 2
    assert [r.outcome for r in records] == ["fixture_hit", "fixture_hit"]
    assert all(r.mode == "fixture" for r in records)


def test_replay_by_input_hash(make_gateway: GatewayFactory, tmp_path: Path) -> None:
    msgs = [ChatMessage(role="user", content="extract please")]
    key = fixture_hash("extract", msgs, json_mode=False)
    assert key == fixture_hash("extract", list(msgs), json_mode=False)  # stable
    assert key != fixture_hash("classify", msgs, json_mode=False)
    FixtureStore(tmp_path / "fixtures").save("extract", key, content="raw text", model="rec-m")
    gw = make_gateway(mode="fixture")

    resp = gw.complete("extract", msgs)

    assert (resp.content, resp.model, resp.mode, resp.attempts) == (
        "raw text",
        "rec-m",
        "fixture",
        0,
    )


def test_missing_fixture_raises_clear_error(make_gateway: GatewayFactory, tmp_path: Path) -> None:
    records: list[CallRecord] = []
    gw = make_gateway(mode="fixture", hooks=[records.append])

    with pytest.raises(FixtureNotFoundError) as info:
        gw.complete(
            "classify", [{"role": "user", "content": "unknown doc"}], fixture_key="deadbeef"
        )

    err = info.value
    assert err.code == IDP_E06
    assert err.retryable is False
    assert err.key == "deadbeef"
    assert err.path == str(tmp_path / "fixtures" / "classify" / "deadbeef.json")
    assert "no model fixture" in str(err) and "deadbeef.json" in str(err)
    assert records[0].outcome == "fixture_miss"
    assert gw.call_count == 1


def test_malformed_or_mismatched_fixture(make_gateway: GatewayFactory, tmp_path: Path) -> None:
    root = tmp_path / "fixtures" / "classify"
    root.mkdir(parents=True)
    (root / "bad.json").write_text('{"task_type": "classify", "key": "bad"}')  # no payload
    (root / "both.json").write_text(
        json.dumps({"task_type": "classify", "key": "both", "content": "x", "data": None})
    )
    (root / "other.json").write_text(
        json.dumps({"task_type": "classify", "key": "not-other", "content": "x"})
    )
    gw = make_gateway(mode="fixture")
    for key, msg in [("bad", "malformed"), ("both", "malformed"), ("other", "declares")]:
        with pytest.raises(ModelGatewayError, match=msg):
            gw.complete("classify", [{"role": "user", "content": "x"}], fixture_key=key)
    with pytest.raises(ModelGatewayError, match="invalid fixture key"):
        gw.complete("classify", [{"role": "user", "content": "x"}], fixture_key="../etc/passwd")


def test_fixture_data_null_and_invalid_schema_is_not_retried(
    make_gateway: GatewayFactory, tmp_path: Path
) -> None:
    store = FixtureStore(tmp_path / "fixtures")
    store.save("extract", "k-null", data=None)
    store.save("extract", "k-bad", content="not json")
    gw = make_gateway(mode="fixture")
    msgs = [{"role": "user", "content": "x"}]

    assert gw.complete_json("extract", msgs, fixture_key="k-null") is None
    with pytest.raises(ModelOutputError):
        gw.complete("extract", msgs, Classified, fixture_key="k-bad")
    assert gw.attempt_count == 2  # no schema re-ask in fixture mode (replay is deterministic)


def test_default_fixture_dir_and_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.core.model_gateway.gateway.get_config",
        lambda: ConfigService(model_gateway_mode="fixture"),
    )
    reset_model_gateway()
    try:
        gw = get_model_gateway()
        assert gw is get_model_gateway()
        assert gw.mode == "fixture"
        assert gw.fixtures.root == DEFAULT_FIXTURE_DIR
        assert DEFAULT_FIXTURE_DIR.as_posix().endswith("apps/api/tests/fixtures/model_gateway")
        assert "FixtureStore" in repr(gw.fixtures)
    finally:
        reset_model_gateway()

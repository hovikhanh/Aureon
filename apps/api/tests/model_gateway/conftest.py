"""Shared helpers for ModelGateway tests (T-006). Never sleeps: `sleep` is injected."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.core.config import ConfigService
from app.core.model_gateway import ModelGateway

FAKE_KEY = "sk-test-NEVER-LEAK-0123456789"
BASE_URL = "http://omniroute.test/v1"

Handler = Callable[[httpx.Request], httpx.Response]


def ok_body(content: str, model: str = "served-model") -> dict[str, Any]:
    return {
        "id": "chatcmpl-test",
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 5, "total_tokens": 16},
    }


class Recorder:
    """httpx.MockTransport handler that replays scripted outcomes and records requests."""

    def __init__(self, *outcomes: httpx.Response | Exception | Handler) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, httpx.Response):
            return outcome
        return outcome(request)

    def models(self) -> list[str]:
        return [json.loads(r.content)["model"] for r in self.requests]

    def bodies(self) -> list[dict[str, Any]]:
        return [json.loads(r.content) for r in self.requests]


@pytest.fixture
def config() -> ConfigService:
    return ConfigService(
        omniroute_base_url=BASE_URL,
        omniroute_api_key=FAKE_KEY,
        model_classify="primary-model",
        model_extract="extract-model",
        model_gateway_mode="live",
    )


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def make_gateway(
    config: ConfigService, sleeps: list[float], tmp_path: Path
) -> Callable[..., ModelGateway]:
    def build(recorder: Recorder | None = None, **kwargs: Any) -> ModelGateway:
        kwargs.setdefault("sleep", sleeps.append)
        kwargs.setdefault("fixture_dir", tmp_path / "fixtures")
        if recorder is not None:
            kwargs.setdefault("transport", httpx.MockTransport(recorder))
        return ModelGateway(config, **kwargs)

    return build

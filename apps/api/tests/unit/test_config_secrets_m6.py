"""TC-M6-05 — R-DEC-167: a settings validation error does not print the settings input.

Found in M6: a mis-quoted `MODEL_PRICING_JSON` made `ConfigService()` fail and pydantic printed the
whole input dict — a demo password included — into an E2E log. What a traceback shows is
`str()` / `repr()` of the error; that is what must stay free of input. The test runs on an EMPTY
environment with made-up values, so even a failing assertion cannot echo a real secret.
"""

import os

import pytest
from pydantic import ValidationError

from app.core.config import ConfigService

SAMPLE = "Sample-Pa55word-not-real"


@pytest.fixture
def bare_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for k in list(os.environ):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", SAMPLE)
    monkeypatch.setenv("DATABASE_URL", f"postgresql+psycopg://aureon:{SAMPLE}@localhost:5432/x")
    return monkeypatch


def _shown(err: ValidationError) -> str:
    return f"{err}\n{err!r}\n{err.errors(include_input=False)}"


def test_validation_error_hides_secret_input(bare_env: pytest.MonkeyPatch) -> None:
    bare_env.setenv("MODEL_PRICING_JSON", '\'{"p:m": {"in": 1, "out": 1}}\'')  # quotes kept
    with pytest.raises(ValidationError) as err:
        ConfigService(_env_file=None)
    shown = _shown(err.value)
    assert "input_value" not in shown
    assert SAMPLE not in shown, "settings input leaked into the error text"


def test_bad_field_type_hides_its_value(bare_env: pytest.MonkeyPatch) -> None:
    bare_env.setenv("OUTBOX_RELAY_INTERVAL_SECONDS", SAMPLE)  # not a number
    with pytest.raises(ValidationError) as err:
        ConfigService(_env_file=None)
    assert SAMPLE not in _shown(err.value), "field value leaked into the error text"

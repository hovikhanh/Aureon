"""AI-eval reuses the IDP integration fixtures (temp object store, hidden review queue)."""

import pytest

from tests.integration.idp.conftest import idp_store

__all__ = ["idp_store"]


@pytest.fixture(autouse=True)
def full_catalog_chat(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """D-19 intent routing narrows the tools and runs obvious READ tools before the first model
    round. These tests script the model's own tool choice over the full permitted catalog (P06
    filtering, budgets, classification), so they pin `CHAT_INTENT_ROUTING=false`; routing has its
    own tests (modules that set `INTENT_ROUTING = True`, e.g. `test_chat_intent_d19.py`)."""
    if getattr(request.module, "INTENT_ROUTING", False):
        return
    from app.core.config import get_config

    monkeypatch.setenv("CHAT_INTENT_ROUTING", "false")
    get_config.cache_clear()

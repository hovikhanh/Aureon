"""T-002 — `.env.example` declares every v2.1 variable (07 §7) and ConfigService knows them."""

import re

from app.core.config import REPO_ROOT, ConfigService

DOMAINS = ("EXECUTION", "SALES", "FINANCE", "RISK", "HR", "PRODUCT")
V21_VARS = {
    "APPROVAL_FINANCE_THRESHOLD_VND",
    "BRIEFING_TIME",
    "DQ_WEIGHT_COMPLETENESS",
    "DQ_WEIGHT_ACCURACY",
    "DQ_WEIGHT_FRESHNESS",
    "MODEL_PROVIDER_CONFIDENTIAL",
    "MODEL_PROVIDER_SECRET",
    "OLLAMA_BASE_URL",
    "LOCAL_CHAT_MODEL",
    "EMBEDDING_MODEL",
    "CLAMAV_HOST",
    "CLAMAV_PORT",
    *(f"SLA_OPERATIONAL_{d}_HOURS" for d in DOMAINS),
    *(f"SLA_FRESHNESS_{d}_HOURS" for d in DOMAINS),
}


def _example_vars() -> dict[str, str]:
    text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    return dict(re.findall(r"^([A-Z0-9_]+)=(.*)$", text, flags=re.MULTILINE))


def test_env_example_has_v21_vars() -> None:
    missing = V21_VARS - _example_vars().keys()
    assert not missing, f"missing in .env.example: {sorted(missing)}"


def test_config_service_declares_v21_vars() -> None:
    fields = {name.upper() for name in ConfigService.model_fields}
    assert V21_VARS <= fields


def test_local_chat_model_is_not_embedding_model() -> None:
    env = _example_vars()
    assert env["LOCAL_CHAT_MODEL"] != env["EMBEDDING_MODEL"] == "bge-m3"

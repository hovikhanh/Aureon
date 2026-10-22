"""Provider chain selection (07 §6.2, §6.5 — DEC-131, DEC-149, DEC-157).

| classification      | chain                                                         |
|---------------------|---------------------------------------------------------------|
| PUBLIC / INTERNAL   | MODEL_PROVIDER_PRIMARY → MODEL_PROVIDER_FALLBACKS (cloud OK)   |
| CONFIDENTIAL        | MODEL_PROVIDER_CONFIDENTIAL (default `ollama`) → `template`    |
| SECRET              | none — `SecretDataBlockedError` (template, never an LLM)       |

Invariant: a CONFIDENTIAL chain never falls back from local/template to cloud. A configured
cloud id in MODEL_PROVIDER_CONFIDENTIAL is the explicit, audited ADMIN override path only
(EP-129, T-3xx) — the env default is local.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.model_gateway.errors import SecretDataBlockedError
from app.core.model_gateway.types import Classification, TaskKind

if TYPE_CHECKING:
    from app.core.config import ConfigService

CLOUD_PROVIDERS: tuple[str, ...] = (
    "omniroute", "openrouter", "ninerouter", "deepseek", "openai", "anthropic",
)  # fmt: skip
LOCAL_PROVIDERS: tuple[str, ...] = ("ollama",)
TEMPLATE = "template"
ALIASES = {"9router": "ninerouter"}


def _csv(value: str) -> list[str]:
    return [ALIASES.get(p, p) for p in (x.strip().lower() for x in value.split(",")) if p]


@dataclass(frozen=True)
class Route:
    classification: Classification
    providers: tuple[str, ...]  # in order; may end with TEMPLATE
    reason: str


def validate_routing_config(cfg: "ConfigService") -> None:
    """Fail fast at startup (TC-AI-022)."""
    known = {*CLOUD_PROVIDERS, *LOCAL_PROVIDERS}
    for p in [cfg.model_provider_primary, *_csv(cfg.model_provider_fallbacks)]:
        if ALIASES.get(p, p) not in known:
            raise ValueError(f"unknown provider {p!r} in MODEL_PROVIDER_PRIMARY/FALLBACKS")
    for p in _csv(cfg.model_provider_confidential):
        if p not in known and p != TEMPLATE:
            raise ValueError(f"unknown provider {p!r} in MODEL_PROVIDER_CONFIDENTIAL")


def has_credentials(cfg: "ConfigService", provider: str) -> bool:
    if provider in LOCAL_PROVIDERS or provider == TEMPLATE:
        return True
    key = getattr(cfg, f"{provider}_api_key", None)
    return key is not None and bool(key.get_secret_value()) and "<" not in key.get_secret_value()


def route(cfg: "ConfigService", classification: Classification) -> Route:
    if classification == "SECRET":
        raise SecretDataBlockedError
    if classification == "CONFIDENTIAL":
        chain = [p for p in _csv(cfg.model_provider_confidential) if p != TEMPLATE]
        chain = [p for p in chain if has_credentials(cfg, p)]
        overridden = any(p in CLOUD_PROVIDERS for p in chain)
        reason = "confidential: admin override to cloud" if overridden else "confidential: local"
        return Route(classification, (*chain, TEMPLATE), reason)
    chain = [ALIASES.get(cfg.model_provider_primary, cfg.model_provider_primary)]
    chain += [p for p in _csv(cfg.model_provider_fallbacks) if p not in chain]
    usable = tuple(p for p in chain if has_credentials(cfg, p))
    return Route(classification, usable, f"{classification.lower()}: cloud chain")


def model_for(cfg: "ConfigService", task: TaskKind, provider: str) -> str:
    """`MODEL_<TASK>__<PROVIDER>` → (ollama: LOCAL_CHAT_MODEL) → `MODEL_<TASK>`."""
    override = cfg.model_overrides().get((task, provider))
    if override:
        return override
    if provider in LOCAL_PROVIDERS:
        return cfg.local_chat_model
    if task == "embed":
        return cfg.embedding_model
    value: str = getattr(cfg, f"model_{task}")
    return value


def models_for(cfg: "ConfigService", task: TaskKind, provider: str) -> list[str]:
    """Ordered model chain for one provider (T-509, DEC-241).

    Chat on a cloud provider without a per-provider override uses
    `CHAT_MODEL_PRIMARY` → `CHAT_MODEL_FALLBACK` when set; every other case is the single
    `model_for` value.
    """
    base = model_for(cfg, task, provider)
    if task != "chat" or provider not in CLOUD_PROVIDERS:
        return [base]
    if cfg.model_overrides().get((task, provider)):
        return [base]
    chain = [m for m in (cfg.chat_model_primary.strip(), cfg.chat_model_fallback.strip()) if m]
    return list(dict.fromkeys(chain)) or [base]


def timeout_for(cfg: "ConfigService", task: TaskKind) -> float:
    """Per-call timeout: chat uses `CHAT_TIMEOUT_SECONDS` (T-509), others `AI_TURN_TIMEOUT_SEC`."""
    return cfg.chat_timeout_seconds if task == "chat" else cfg.ai_turn_timeout_sec

"""Gateway errors. Public failures are `AI_*` (10 §1.4); the rest are routing signals."""

from app.core.errors import AIError, ai_error


class ProviderCallError(Exception):
    """One adapter call failed. `retryable` = 5xx / 429 / timeout / connect (07 §6.2)."""

    def __init__(self, provider: str, *, retryable: bool, status: int | None, timeout: bool):
        self.provider, self.retryable, self.status, self.timeout = (
            provider,
            retryable,
            status,
            timeout,
        )
        kind = "timeout" if timeout else f"HTTP {status}" if status else "connection error"
        super().__init__(f"{provider}: {kind}")  # never the body — may echo the prompt


class TemplateRequired(Exception):
    """No LLM may answer this request — the caller renders the rule/number template (07 §6.5)."""

    def __init__(self, classification: str, reason: str) -> None:
        self.classification, self.reason = classification, reason
        super().__init__(f"{classification}: {reason}")


class SecretDataBlockedError(TemplateRequired):
    """`SECRET` data never reaches any LLM, under any configuration (DEC-157)."""

    def __init__(self) -> None:
        super().__init__("SECRET", "secret data is never sent to an LLM")


class FixtureMissingError(LookupError):
    """`MODEL_GATEWAY_MODE=fixture` and no recorded response — fail loudly (CLAUDE.md §6.5)."""


def provider_error(last: ProviderCallError | None) -> AIError:
    if last is not None and last.timeout:
        return ai_error("AI_PROVIDER_TIMEOUT", "all providers timed out")
    return ai_error("AI_PROVIDER_ERROR", "no provider could answer")

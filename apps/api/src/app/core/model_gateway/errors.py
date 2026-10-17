"""ModelGateway error types (04 §14 IDP-E06 / IDP-E07, 07 §5.2).

Error messages are built by the gateway itself and never contain the API key, the
Authorization header, request bodies or document content (CLAUDE.md credential rules).
"""

from typing import Final

IDP_E06: Final = "IDP-E06"  # Model timeout / gateway error -> pipeline FAILED (04 §14)
IDP_E07: Final = "IDP-E07"  # Model output violates schema after 1 retry -> FAILED (04 §14, PI-02)


class ModelGatewayError(Exception):
    """Raised when no route produced a usable completion.

    `code` is the IDP error code the pipeline stores on the job (`error_code`), so the
    document can transition to `FAILED` (04 §6, FR-DC-22, TC-IDP-030).
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = IDP_E06,
        task_type: str | None = None,
        attempts: int = 0,
        retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.task_type = task_type
        self.attempts = attempts
        self.retryable = retryable

    def __str__(self) -> str:
        return f"[{self.code}] {self.args[0]}"


class FixtureNotFoundError(ModelGatewayError):
    """Fixture mode has no recorded output for this input (07 §9: outside DOC-01→07 -> FAILED)."""

    def __init__(self, message: str, *, task_type: str, key: str, path: str) -> None:
        super().__init__(message, code=IDP_E06, task_type=task_type, retryable=False)
        self.key = key
        self.path = path


class ModelOutputError(ModelGatewayError):
    """Model output is not valid JSON / does not match the response schema (IDP-E07, PI-02)."""

    def __init__(self, message: str, *, task_type: str, attempts: int) -> None:
        super().__init__(
            message, code=IDP_E07, task_type=task_type, attempts=attempts, retryable=False
        )

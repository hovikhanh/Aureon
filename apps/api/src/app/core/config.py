"""ConfigService — single source of env config (CLAUDE.md §6.4, 07 §7).

No `os.environ` reads anywhere else. Secrets are `SecretStr` so they never print in logs/reprs.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/src/app/core/config.py -> repo root is 5 levels up.
REPO_ROOT = Path(__file__).resolve().parents[5]


class ConfigService(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # --- Database / queue ---
    database_url: SecretStr = SecretStr("postgresql+psycopg://localhost:5432/aureon")
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    celery_broker_url: SecretStr = SecretStr("redis://localhost:6379/1")
    celery_result_backend: SecretStr = SecretStr("redis://localhost:6379/2")
    # Outbox relay tick (07 §3 `beat`: every 2 s). Beat runs exactly one instance.
    outbox_relay_interval_seconds: float = Field(default=2.0, gt=0)

    # --- Auth / JWT RS256 (DEC-129) ---
    jwt_algorithm: Literal["RS256"] = "RS256"
    jwt_private_key_path: Path = REPO_ROOT / "secrets" / "jwt_private.pem"
    jwt_public_key_path: Path = REPO_ROOT / "secrets" / "jwt_public.pem"
    jwt_private_key: SecretStr | None = None
    jwt_public_key: SecretStr | None = None
    jwt_key_id: str = "aureon-2026-10"
    jwt_issuer: str = "aureon"
    jwt_audience: str = "aureon-api"
    jwt_access_ttl_seconds: int = 900
    jwt_refresh_ttl_seconds: int = 604800
    # 02 §4: temporary lock after N consecutive failures (configurable value).
    auth_max_failed_logins: int = 5
    auth_lockout_minutes: int = 15

    # --- ModelGateway / AI routing (DEC-131, DEC-157) ---
    model_gateway_mode: Literal["fixture", "live", "record"] = "fixture"
    model_provider_confidential: str = "ollama"
    model_provider_secret: Literal["none"] = Field(default="none")
    ollama_base_url: str = "http://localhost:11434"
    local_chat_model: str = "qwen2.5:7b-instruct"
    embedding_model: str = "bge-m3"

    # --- IDP / ClamAV (DEC-138) ---
    clamav_host: str = "localhost"
    clamav_port: int = 3310
    clamav_required: bool = False

    # --- Dashboard / DQ / SLA (DEC-148, DEC-158) ---
    dq_weight_completeness: float = 0.3
    dq_weight_accuracy: float = 0.4
    dq_weight_freshness: float = 0.3
    # Operational Freshness SLA (dashboard "stale" badge) vs DQ Freshness SLA — DEC-158.
    sla_operational_execution_hours: int = 1
    sla_operational_sales_hours: int = 1
    sla_operational_finance_hours: int = 4
    sla_operational_risk_hours: int = 4
    sla_operational_hr_hours: int = 24
    sla_operational_product_hours: int = 24
    sla_freshness_finance_hours: int = 24
    sla_freshness_sales_hours: int = 24
    sla_freshness_hr_hours: int = 72
    sla_freshness_product_hours: int = 72
    sla_freshness_risk_hours: int = 48
    sla_freshness_execution_hours: int = 24
    briefing_time: str = "06:00"
    approval_finance_threshold_vnd: int = 500_000_000

    # --- Demo ---
    demo_mode: bool = False
    demo_reference_date: str = "2026-10-20"
    demo_password: SecretStr | None = None  # fallback for every role below (dev convenience)
    # 08 §2 — one password per demo account; v1 names accepted as aliases.
    demo_ceo_password: SecretStr | None = None
    demo_cfo_password: SecretStr | None = None
    demo_vp_sales_password: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("DEMO_VP_SALES_PASSWORD", "DEMO_SALES_PASSWORD")
    )
    demo_hr_manager_password: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("DEMO_HR_MANAGER_PASSWORD", "DEMO_HR_PASSWORD")
    )
    demo_reviewer_password: SecretStr | None = None
    demo_cpo_password: SecretStr | None = None
    demo_risk_manager_password: SecretStr | None = None
    demo_manager_password: SecretStr | None = None
    demo_employee_password: SecretStr | None = None
    demo_admin_password: SecretStr | None = None

    def demo_password_for(self, role: str) -> SecretStr | None:
        value: SecretStr | None = getattr(self, f"demo_{role.lower()}_password", None)
        return value or self.demo_password

    @model_validator(mode="after")
    def _resolve_key_paths(self) -> "ConfigService":
        # Relative paths in .env (`./secrets/...`) are relative to the repo root, not the cwd.
        if not self.jwt_private_key_path.is_absolute():
            self.jwt_private_key_path = REPO_ROOT / self.jwt_private_key_path
        if not self.jwt_public_key_path.is_absolute():
            self.jwt_public_key_path = REPO_ROOT / self.jwt_public_key_path
        return self

    @model_validator(mode="after")
    def _dq_weights_sum_to_one(self) -> "ConfigService":
        total = self.dq_weight_completeness + self.dq_weight_accuracy + self.dq_weight_freshness
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"DQ_WEIGHT_* must sum to 1.0 (got {total})")
        return self


@lru_cache
def get_config() -> ConfigService:
    return ConfigService()

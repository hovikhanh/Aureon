"""ConfigService: single place secrets/config are read from env (CLAUDE.md, 07 §7)."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/src/app/core/config.py -> repo root is 5 levels up.
REPO_ROOT = Path(__file__).resolve().parents[5]


class ConfigService(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_version: str = "0.1.0"

    # Database / queue / storage
    database_url: SecretStr = SecretStr("postgresql+psycopg://localhost:5432/aureon")
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    celery_broker_url: SecretStr = SecretStr("redis://localhost:6379/1")
    celery_result_backend: SecretStr = SecretStr("redis://localhost:6379/2")
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: SecretStr = SecretStr("")
    s3_secret_key: SecretStr = SecretStr("")
    s3_bucket: str = "source-documents"

    # Auth (07 §8.1.2)
    jwt_secret: SecretStr = SecretStr("")
    jwt_issuer: str = "aureon-demo"
    jwt_audience: str = "aureon-api"
    jwt_expires_in: int = 28800

    # Model gateway (07 §5.2)
    omniroute_base_url: str = "http://localhost:20128/v1"
    omniroute_api_key: SecretStr = SecretStr("")
    model_classify: str = "agent-free-cheap"
    model_extract: str = "agent-coding"
    model_gateway_mode: str = "fixture"

    # Limits / demo
    max_file_size_mb: int = 20
    max_pages: int = 50
    ai_kill_switch: bool = False
    ai_kill_switch_mode: str = "L0"
    invoice_autonomy_level: str = "L2"
    demo_mode: bool = False
    demo_reference_date: str = "2026-10-20"
    # Demo account passwords (08 §2) — read only by `app.seed`, hashed with argon2id, never logged.
    demo_ceo_password: SecretStr | None = None
    demo_cfo_password: SecretStr | None = None
    demo_sales_password: SecretStr | None = None
    demo_hr_password: SecretStr | None = None
    demo_reviewer_password: SecretStr | None = None


@lru_cache
def get_config() -> ConfigService:
    return ConfigService()

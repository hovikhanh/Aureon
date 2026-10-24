"""ConfigService — single source of env config (CLAUDE.md §6.4, 07 §7).

No `os.environ` reads anywhere else. Secrets are `SecretStr` so they never print in logs/reprs.
"""

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
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
    # Clock skew tolerated on `iat`/`exp` (whole-second `iat` vs float `now`; multi-host skew).
    jwt_leeway_seconds: int = Field(default=30, ge=0, le=300)
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
    # 07 §6.1–6.3. Chain = primary → fallbacks (CSV); a cloud provider with no key is skipped.
    model_provider_primary: str = "omniroute"
    model_provider_fallbacks: str = ""
    omniroute_base_url: str = "http://localhost:20128/v1"
    omniroute_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: SecretStr | None = None
    ninerouter_base_url: str = "http://localhost:20129/v1"
    ninerouter_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: SecretStr | None = None
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_api_key: SecretStr | None = None
    model_chat: str = "auto/coding"
    model_classify: str = "auto/cheap"
    model_extract: str = "auto/coding"
    model_mapping: str = "auto/cheap"
    model_insight: str = "auto/cheap"
    model_stt: str = "fixture/stt"
    model_temperature: float = Field(default=0.2, ge=0, le=2)
    model_max_output_tokens: int = Field(default=2048, gt=0)
    model_pricing_json: str = "{}"  # {"provider:model": {"in": usd_per_1m, "out": usd_per_1m}}
    ai_turn_timeout_sec: float = Field(default=30, gt=0)
    # T-509 / DEC-241: chat-only model chain inside each cloud provider (primary → fallback,
    # each tried once on timeout) and a longer per-call chat timeout. Empty → MODEL_CHAT.
    chat_model_primary: str = ""
    chat_model_fallback: str = ""
    chat_timeout_seconds: float = Field(default=90, gt=0)
    # Demo replay of recorded answers (DEC-241). Unset → follows DEMO_MODE.
    ai_demo_replay: bool | None = None
    ai_demo_token_delay_sec: float = Field(default=0.03, ge=0, le=1)
    ai_monthly_budget_usd: float = Field(default=50, ge=0)
    ai_budget_alert_pct: int = Field(default=80, ge=1, le=100)

    # --- IDP / ClamAV (DEC-138) ---
    clamav_host: str = "localhost"
    clamav_port: int = 3310
    clamav_required: bool = False
    # --- IDP storage & pipeline limits (04 §15.1, 07 §448) ---
    # Demo object store: local filesystem under this dir (prod swaps for MinIO/S3 behind the
    # same ObjectStore interface). `quarantine` bucket for INFECTED files (DEC-138).
    idp_storage_dir: Path = REPO_ROOT / "var" / "idp-storage"
    idp_max_file_size_mb: int = Field(default=50, gt=0)  # 04 §15.1
    idp_max_pages: int = Field(default=300, gt=0)
    idp_max_files_per_upload: int = Field(default=100, gt=0)
    # OCR backend: `stub` (deterministic, demo/CI default) | `paddle` (in-process, 07 §47).
    # `paddle` is only used when the optional package is importable (DEC-049 fixture/replay demo).
    ocr_provider: Literal["stub", "paddle"] = "stub"
    # --- IDP review SLA (04 §8.3, FR-DC-21) ---
    # Default review SLA: documents in NEEDS_REVIEW beyond this → escalate to manager; a
    # second SLA span (2×) → escalate to the department head (hourly `check_review_sla` beat).
    review_sla_hours: int = Field(default=24, gt=0)

    # --- Goals M1.4 (05 §2.6, R-DEC-54/55): on-time KPI/KR (METRIC-STR-01) + KR at-risk ---
    goals_kpi_grace_days: int = Field(default=5, ge=0, le=31)
    goals_kr_checkin_max_age_days: int = Field(default=7, gt=0, le=92)
    goals_kr_behind_ratio: float = Field(default=0.7, gt=0, le=1)

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

    # --- E-mail notifications (T-616b, R-DEC-20/33) — Mailpit in dev ---
    smtp_host: str = ""  # empty = e-mail not configured → PENDING rows wait, send task fails
    smtp_port: int = Field(default=1025, gt=0, le=65535)
    smtp_username: str = ""
    smtp_password: SecretStr | None = None
    smtp_from: str = "Aureon <no-reply@aureon.local>"
    smtp_starttls: bool = False
    smtp_timeout_seconds: float = Field(default=10, gt=0, le=60)
    web_base_url: str = "http://localhost:3000"  # absolute links in e-mails
    notification_email_interval_seconds: float = Field(default=60, gt=0)

    # --- Demo ---
    demo_mode: bool = False
    demo_reference_date: str = "2026-10-20"
    # pgcrypto key for level-4 PII columns (T-234, DEC-207); 05 OQ-08 name accepted as alias
    db_encryption_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("DB_ENCRYPTION_KEY", "PII_ENCRYPTION_KEY")
    )
    # METRIC-HR-01 plan, VND / person / year (08 §6 HR_REVENUE_PER_HEAD_PLAN = 2,0 tỷ)
    hr_revenue_per_head_plan: int = 2_000_000_000
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
    # T-237: `SEED_PASSWORD_CPO` / `SEED_PASSWORD_RISK_MANAGER` accepted as aliases (brief naming).
    demo_cpo_password: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("DEMO_CPO_PASSWORD", "SEED_PASSWORD_CPO")
    )
    demo_risk_manager_password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DEMO_RISK_MANAGER_PASSWORD", "SEED_PASSWORD_RISK_MANAGER"),
    )
    demo_manager_password: SecretStr | None = None
    # T-603b: MGR Hành chính — falls back to the MGR password so existing dev .env keep working.
    demo_office_manager_password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DEMO_OFFICE_MANAGER_PASSWORD", "DEMO_MANAGER_PASSWORD"),
    )
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
    def _model_routing_valid(self) -> "ConfigService":
        from app.core.model_gateway.routing import validate_routing_config

        validate_routing_config(self)
        return self

    def model_overrides(self) -> dict[tuple[str, str], str]:
        """`MODEL_<TASK>__<PROVIDER>` (07 §6.2) from the process env and `.env` (env wins)."""
        return _model_overrides(self.model_config.get("env_file"))

    @model_validator(mode="after")
    def _dq_weights_sum_to_one(self) -> "ConfigService":
        total = self.dq_weight_completeness + self.dq_weight_accuracy + self.dq_weight_freshness
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"DQ_WEIGHT_* must sum to 1.0 (got {total})")
        return self


_OVERRIDE = re.compile(r"^MODEL_([A-Z]+)__([A-Z0-9]+)$")


def _model_overrides(env_file: object) -> dict[tuple[str, str], str]:
    raw: dict[str, str | None] = {}
    if isinstance(env_file, Path) and env_file.is_file():
        raw.update(dotenv_values(env_file))
    raw.update(os.environ)
    out: dict[tuple[str, str], str] = {}
    for key, value in raw.items():
        m = _OVERRIDE.match(key.upper())
        if m and value:
            out[(m.group(1).lower(), m.group(2).lower())] = value
    return out


@lru_cache
def get_config() -> ConfigService:
    return ConfigService()

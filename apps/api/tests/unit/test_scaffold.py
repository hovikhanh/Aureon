"""T-001 — scaffold smoke tests: app factory, 11 modules, base classes, config."""

import importlib

import pytest
from pydantic import ValidationError

from app.core.base_model import (
    BusinessModel,
    DataClassification,
    RecordSource,
)
from app.core.config import ConfigService
from app.main import API_PREFIX, MODULE_ROUTERS, create_app

MODULES = (
    "auth", "finance", "sales", "hr", "product", "risk",
    "execution", "ai", "idp", "platform", "dashboard",
)  # fmt: skip


def test_app_factory_builds() -> None:
    app = create_app()
    assert app.title == "Aureon API"
    assert len(MODULE_ROUTERS) == 11
    assert API_PREFIX == "/api/v1"


@pytest.mark.parametrize("module", MODULES)
def test_module_layout(module: str) -> None:
    importlib.import_module(f"app.modules.{module}.routes.router")
    importlib.import_module(f"app.modules.{module}.services.{module}_service")
    if module != "dashboard":
        for layer in ("models", "repositories", "schemas", "events"):
            importlib.import_module(f"app.modules.{module}.{layer}")


def test_dashboard_has_no_models() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("app.modules.dashboard.models")


def test_business_model_has_standard_columns() -> None:
    names = set(BusinessModel.__annotations__) | {
        n for c in BusinessModel.__mro__ for n in getattr(c, "__annotations__", {})
    }
    expected = {"id", "created_at", "updated_at", "deleted_at", "created_by", "updated_by"}
    assert expected | {"source", "data_classification", "version"} <= names


def test_enums_match_spec() -> None:
    assert [m.value for m in DataClassification] == ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]
    assert {m.value for m in RecordSource} == {"MANUAL", "IDP", "IMPORT", "AI", "EVENT", "SEED"}


def test_config_rejects_bad_dq_weights() -> None:
    with pytest.raises(ValidationError):
        ConfigService(dq_weight_completeness=0.5, dq_weight_accuracy=0.5, dq_weight_freshness=0.5)


def test_config_secret_provider_is_none_only() -> None:
    with pytest.raises(ValidationError):
        ConfigService(model_provider_secret="ollama")  # type: ignore[arg-type]
